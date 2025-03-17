from dataclasses import dataclass
from typing import Optional
from httpx import Headers, Response
from deprecated import deprecated
from .http import RelayerHttpClient
from .types import (
    ExternalOrder, ExternalMatchResponse,
    ExternalQuoteRequest, ExternalQuoteResponse,
    AssembleExternalMatchRequest, SignedExternalQuote,
    AtomicMatchApiBundle, ApiSignedExternalQuote
)

SEPOLIA_BASE_URL = "https://testnet.auth-server.renegade.fi"
MAINNET_BASE_URL = "https://mainnet.auth-server.renegade.fi"

RENEGADE_API_KEY_HEADER = "x-renegade-api-key"

REQUEST_EXTERNAL_QUOTE_ROUTE = "/v0/matching-engine/quote"
ASSEMBLE_EXTERNAL_MATCH_ROUTE = "/v0/matching-engine/assemble-external-match"
REQUEST_EXTERNAL_MATCH_ROUTE = "/v0/matching-engine/request-external-match"

DISABLE_GAS_SPONSORSHIP_QUERY_PARAM = "disable_gas_sponsorship"
GAS_REFUND_ADDRESS_QUERY_PARAM = "refund_address"
REFUND_NATIVE_ETH_QUERY_PARAM = "refund_native_eth"

class ExternalMatchClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

@dataclass
class ExternalMatchOptions:
    do_gas_estimation: bool = False
    receiver_address: Optional[str] = None
    request_gas_sponsorship: bool = False
    gas_refund_address: Optional[str] = None

    @classmethod
    def new(cls) -> "ExternalMatchOptions":
        return cls()

    def with_gas_estimation(self, do_gas_estimation: bool) -> "ExternalMatchOptions":
        self.do_gas_estimation = do_gas_estimation
        return self

    def with_receiver_address(self, receiver_address: str) -> "ExternalMatchOptions":
        self.receiver_address = receiver_address
        return self

    def with_gas_sponsorship(self, request_gas_sponsorship: bool, gas_refund_address: Optional[str] = None) -> "ExternalMatchOptions":
        self.request_gas_sponsorship = request_gas_sponsorship
        self.gas_refund_address = gas_refund_address
        return self 

    def with_updated_order(self, updated_order: ExternalOrder) -> "ExternalMatchOptions":
        self.updated_order = updated_order
        return self

    def build_request_path(self) -> str:
        """
        Builds the path at which the request will be sent, with query params 
        """
        disable_sponsorship_str = str(not self.request_gas_sponsorship).lower()
        path = f"{REQUEST_EXTERNAL_MATCH_ROUTE}?{DISABLE_GAS_SPONSORSHIP_QUERY_PARAM}={disable_sponsorship_str}"
        if self.gas_refund_address:
            path += f"&{GAS_REFUND_ADDRESS_QUERY_PARAM}={self.gas_refund_address}"

        return path

@dataclass
class RequestQuoteOptions:
    disable_gas_sponsorship: bool = False
    gas_refund_address: Optional[str] = None
    refund_native_eth: bool = False

    @classmethod
    def new(cls) -> "RequestQuoteOptions":
        return cls()

    def with_gas_sponsorship_disabled(self, disable_gas_sponsorship: bool) -> "RequestQuoteOptions":
        self.disable_gas_sponsorship = disable_gas_sponsorship
        return self

    def with_gas_refund_address(self, gas_refund_address: str) -> "RequestQuoteOptions":
        self.gas_refund_address = gas_refund_address
        return self

    def with_refund_native_eth(self, refund_native_eth: bool) -> "RequestQuoteOptions":
        self.refund_native_eth = refund_native_eth
        return self

    def build_request_path(self) -> str:
        """
        Builds the path at which the request will be sent, with query params
        """
        disable_sponsorship_str = str(self.disable_gas_sponsorship).lower()
        path = f"{REQUEST_EXTERNAL_QUOTE_ROUTE}?{DISABLE_GAS_SPONSORSHIP_QUERY_PARAM}={disable_sponsorship_str}"
        if self.gas_refund_address:
            path += f"&{GAS_REFUND_ADDRESS_QUERY_PARAM}={self.gas_refund_address}"
        if self.refund_native_eth:
            refund_native_eth_str = str(self.refund_native_eth).lower()
            path += f"&{REFUND_NATIVE_ETH_QUERY_PARAM}={refund_native_eth_str}"

        return path

@dataclass
class AssembleExternalMatchOptions:
    do_gas_estimation: bool = False
    receiver_address: Optional[str] = None
    updated_order: Optional[ExternalOrder] = None
    request_gas_sponsorship: bool = False
    gas_refund_address: Optional[str] = None

    @classmethod
    def new(cls) -> "AssembleExternalMatchOptions":
        return cls()

    def with_gas_estimation(self, do_gas_estimation: bool) -> "AssembleExternalMatchOptions":
        self.do_gas_estimation = do_gas_estimation
        return self

    def with_receiver_address(self, receiver_address: str) -> "AssembleExternalMatchOptions":
        self.receiver_address = receiver_address
        return self

    def with_updated_order(self, updated_order: ExternalOrder) -> "AssembleExternalMatchOptions":
        self.updated_order = updated_order
        return self

    @deprecated(version="0.1.2", reason="Request gas sponsorship when requesting a quote instead")
    def with_gas_sponsorship(self, request_gas_sponsorship: bool) -> "AssembleExternalMatchOptions":
        self.request_gas_sponsorship = request_gas_sponsorship
        return self

    @deprecated(version="0.1.2", reason="Request gas sponsorship when requesting a quote instead")
    def with_gas_refund_address(self, gas_refund_address: str) -> "AssembleExternalMatchOptions":
        self.gas_refund_address = gas_refund_address
        return self

    def build_request_path(self) -> str:
        """
        Builds the path at which the request will be sent, with query params 
        """
        path = ASSEMBLE_EXTERNAL_MATCH_ROUTE
        if self.request_gas_sponsorship:
            # We only write this query parameter if it was explicitly set. The
            # expectation of the auth server is that when gas sponsorship is
            # requested at the quote stage, there should be no query parameters
            # at all in the assemble request.
            disable_sponsorship_str = str(not self.request_gas_sponsorship).lower()
            path += f"?{DISABLE_GAS_SPONSORSHIP_QUERY_PARAM}={disable_sponsorship_str}"
        if self.gas_refund_address:
            path += f"&{GAS_REFUND_ADDRESS_QUERY_PARAM}={self.gas_refund_address}"

        return path

class ExternalMatchClient:
    """Client for interacting with the Renegade external matching API.
    
    This client handles authentication and provides methods for requesting quotes,
    assembling matches, and executing trades.
    """
    
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        """Initialize a new ExternalMatchClient.
        
        Args:
            api_key: The API key for authentication
            api_secret: The API secret for request signing
            base_url: The base URL of the Renegade API
        """
        self.api_key = api_key
        self.http_client = RelayerHttpClient(base_url, api_secret)

    @classmethod
    def new_sepolia_client(cls, api_key: str, api_secret: str) -> "ExternalMatchClient":
        """Create a new client configured for the Sepolia testnet.
        
        Args:
            api_key: The API key for authentication
            api_secret: The API secret for request signing
            
        Returns:
            A new ExternalMatchClient configured for Sepolia
        """
        return cls(api_key, api_secret, SEPOLIA_BASE_URL)

    @classmethod
    def new_mainnet_client(cls, api_key: str, api_secret: str) -> "ExternalMatchClient":
        """Create a new client configured for mainnet.
        
        Args:
            api_key: The API key for authentication
            api_secret: The API secret for request signing
            
        Returns:
            A new ExternalMatchClient configured for mainnet
        """
        return cls(api_key, api_secret, MAINNET_BASE_URL)

    async def request_quote(self, order: ExternalOrder) -> Optional[SignedExternalQuote]:
        """Request a quote for the given order.
        
        Args:
            order: The order to request a quote for
            
        Returns:
            A signed quote if one is available, None otherwise
            
        Raises:
            ExternalMatchClientError: If the request fails
        """
        return await self.request_quote_with_options(order, RequestQuoteOptions())

    async def request_quote_with_options(
        self,
        order: ExternalOrder,
        options: RequestQuoteOptions
    ) -> Optional[SignedExternalQuote]:
        """Request a quote for the given order with custom options.

        Args:
            order: The order to request a quote for
            options: Custom options for the quote request

        Returns:
            A signed quote if one is available, None otherwise

        Raises:
            ExternalMatchClientError: If the request fails
        """
        request = ExternalQuoteRequest(external_order=order)

        path = options.build_request_path()
        headers = self._get_headers()
        response = await self.http_client.post_with_headers(path, request.model_dump(), headers)
        quote_resp = await self._handle_optional_response(response)

        if quote_resp == None:
            return None

        quote_resp = ExternalQuoteResponse(**quote_resp)
        signed_quote = SignedExternalQuote(
            quote=quote_resp.signed_quote.quote,
            signature=quote_resp.signed_quote.signature,
            gas_sponsorship_info=quote_resp.gas_sponsorship_info
        )

        return signed_quote

    async def assemble_quote(self, quote: SignedExternalQuote) -> Optional[AtomicMatchApiBundle]:
        """Assemble a quote into a match bundle with default options.
        
        Args:
            quote: The signed quote to assemble
            
        Returns:
            A match bundle if assembly succeeds, None otherwise
            
        Raises:
            ExternalMatchClientError: If the request fails
        """
        return await self.assemble_quote_with_options(quote, AssembleExternalMatchOptions())

    async def assemble_quote_with_options(
        self, 
        quote: SignedExternalQuote, 
        options: AssembleExternalMatchOptions
    ) -> Optional[ExternalMatchResponse]:
        """Assemble a quote into a match bundle with custom options.
        
        Args:
            quote: The signed quote to assemble
            options: Custom options for quote assembly
            
        Returns:
            A match bundle if assembly succeeds, None otherwise
            
        Raises:
            ExternalMatchClientError: If the request fails
        """
        signed_quote = ApiSignedExternalQuote(
            quote=quote.quote,
            signature=quote.signature,
        )
        request = AssembleExternalMatchRequest(
            do_gas_estimation=options.do_gas_estimation,
            receiver_address=options.receiver_address,
            signed_quote=signed_quote,
            updated_order=options.updated_order,
            gas_sponsorship_info=quote.gas_sponsorship_info,
        )

        path = options.build_request_path()
        headers = self._get_headers()
        response = await self.http_client.post_with_headers(path, request.model_dump(), headers)
        match_resp = await self._handle_optional_response(response)
        if match_resp:
            return ExternalMatchResponse(**match_resp)

        return None

    def _get_headers(self) -> Headers:
        """Get the headers required for API requests.
        
        Returns:
            Headers containing the API key
        """
        headers = Headers()
        headers[RENEGADE_API_KEY_HEADER] = self.api_key
        return headers

    async def _handle_optional_response(self, response: Response) -> Optional[dict]:
        """Handle an API response that may be empty.
        
        Args:
            response: The API response to handle
            
        Returns:
            The response data if present, None for 204 responses
            
        Raises:
            ExternalMatchClientError: If the response indicates an error
        """
        if response.status_code == 204:  # NO_CONTENT
            return None
        elif response.status_code == 200:  # OK
            return response.json()
        else:
            raise ExternalMatchClientError(
                response.text,
                status_code=response.status_code
            ) 