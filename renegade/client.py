from dataclasses import dataclass
from typing import Optional
from httpx import Headers, Response

from .http import RelayerHttpClient
from .types import (
    ExternalOrder, ExternalMatchRequest, ExternalMatchResponse,
    ExternalQuoteRequest, ExternalQuoteResponse,
    AssembleExternalMatchRequest, SignedExternalQuote,
    AtomicMatchApiBundle
)

SEPOLIA_BASE_URL = "https://testnet.auth-server.renegade.fi"
MAINNET_BASE_URL = "https://mainnet.auth-server.renegade.fi"

RENEGADE_API_KEY_HEADER = "x-renegade-api-key"

REQUEST_EXTERNAL_QUOTE_ROUTE = "/v0/matching-engine/quote"
ASSEMBLE_EXTERNAL_MATCH_ROUTE = "/v0/matching-engine/assemble-external-match"
REQUEST_EXTERNAL_MATCH_ROUTE = "/v0/matching-engine/request-external-match"

class ExternalMatchClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

@dataclass
class ExternalMatchOptions:
    do_gas_estimation: bool = False
    receiver_address: Optional[str] = None

    @classmethod
    def new(cls) -> "ExternalMatchOptions":
        return cls()

    def with_gas_estimation(self, do_gas_estimation: bool) -> "ExternalMatchOptions":
        self.do_gas_estimation = do_gas_estimation
        return self

    def with_receiver_address(self, receiver_address: str) -> "ExternalMatchOptions":
        self.receiver_address = receiver_address
        return self

class ExternalMatchClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.http_client = RelayerHttpClient(base_url, api_secret)

    @classmethod
    def new_sepolia_client(cls, api_key: str, api_secret: str) -> "ExternalMatchClient":
        return cls(api_key, api_secret, SEPOLIA_BASE_URL)

    @classmethod
    def new_mainnet_client(cls, api_key: str, api_secret: str) -> "ExternalMatchClient":
        return cls(api_key, api_secret, MAINNET_BASE_URL)

    async def request_quote(self, order: ExternalOrder) -> Optional[SignedExternalQuote]:
        request = ExternalQuoteRequest(external_order=order)

        headers = self._get_headers()
        response = await self.http_client.post_with_headers(REQUEST_EXTERNAL_QUOTE_ROUTE, request.model_dump(), headers)
        quote_resp = await self._handle_optional_response(response)
        if quote_resp:
            return ExternalQuoteResponse(**quote_resp).signed_quote

        return None

    async def assemble_quote(self, quote: SignedExternalQuote) -> Optional[AtomicMatchApiBundle]:
        return await self.assemble_quote_with_options(quote, ExternalMatchOptions())

    async def assemble_quote_with_options(
        self, 
        quote: SignedExternalQuote, 
        options: ExternalMatchOptions
    ) -> Optional[AtomicMatchApiBundle]:
        request = AssembleExternalMatchRequest(
            do_gas_estimation=options.do_gas_estimation,
            receiver_address=options.receiver_address,
            signed_quote=quote
        )

        headers = self._get_headers()
        response = await self.http_client.post_with_headers(ASSEMBLE_EXTERNAL_MATCH_ROUTE, request.model_dump(), headers)
        match_resp = await self._handle_optional_response(response)
        if match_resp:
            return ExternalMatchResponse(**match_resp).match_bundle

        return None

    async def request_external_match(self, order: ExternalOrder) -> Optional[AtomicMatchApiBundle]:
        return await self.request_external_match_with_options(order, ExternalMatchOptions())

    async def request_external_match_with_options(
        self, 
        order: ExternalOrder, 
        options: ExternalMatchOptions
    ) -> Optional[AtomicMatchApiBundle]:
        request = ExternalMatchRequest(
            do_gas_estimation=options.do_gas_estimation,
            receiver_address=options.receiver_address,
            external_order=order
        )
        headers = self._get_headers()
        response = await self.http_client.post_with_headers(REQUEST_EXTERNAL_MATCH_ROUTE, request.model_dump(), headers)
        match_resp = await self._handle_optional_response(response)
        if match_resp:
            return ExternalMatchResponse(**match_resp).match_bundle

        return None

    def _get_headers(self) -> Headers:
        headers = Headers()
        headers[RENEGADE_API_KEY_HEADER] = self.api_key
        return headers

    async def _handle_optional_response(self, response: Response) -> Optional[dict]:
        if response.status_code == 204:  # NO_CONTENT
            return None
        elif response.status_code == 200:  # OK
            return response.json()
        else:
            raise ExternalMatchClientError(
                response.text,
                status_code=response.status_code
            ) 