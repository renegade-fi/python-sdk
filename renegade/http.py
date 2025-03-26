from typing import Any, TypeVar 
from datetime import timedelta
import json
import hmac
import hashlib
import time
import base64
from httpx import AsyncClient, Client, Headers, Response

REQUEST_SIGNATURE_DURATION = timedelta(seconds=10)
RENEGADE_HEADER_NAMESPACE = "x-renegade"
RENEGADE_AUTH_HEADER_NAME = "x-renegade-auth"
RENEGADE_SIG_EXPIRATION_HEADER_NAME = "x-renegade-auth-expiration"

T = TypeVar('T')
Req = TypeVar('Req')
Resp = TypeVar('Resp')

class RelayerHttpClient:
    """HTTP client for making authenticated requests to the Renegade relayer API.
    
    This client handles request signing and authentication using HMAC-SHA256.
    """
    
    def __init__(self, base_url: str, auth_key: str):
        """Initialize a new RelayerHttpClient.
        
        Args:
            base_url: The base URL of the relayer API
            auth_key: The base64-encoded authentication key for request signing
        """
        self.async_client = AsyncClient()
        self.sync_client = Client()
        self.base_url = base_url
        # Decode base64 auth key
        self.auth_key = base64.b64decode(auth_key)

    async def post(self, path: str, body: Any) -> Response:
        """Make a POST request without custom headers.
        
        Args:
            path: The API endpoint path
            body: The request body to send
            
        Returns:
            The API response
        """
        return await self.post_with_headers(path, body, Headers())

    def post_sync(self, path: str, body: Any) -> Response:
        """Make a synchronous POST request without custom headers.
        
        Args:
            path: The API endpoint path
            body: The request body to send
            
        Returns:
            The API response
        """
        return self.post_with_headers_sync(path, body, Headers())

    async def get(self, path: str) -> Response:
        """Make a GET request without custom headers.
        
        Args:
            path: The API endpoint path
            
        Returns:
            The API response
        """
        return await self.get_with_headers(path, Headers())

    def get_sync(self, path: str) -> Response:
        """Make a synchronous GET request without custom headers.
        
        Args:
            path: The API endpoint path
            
        Returns:
            The API response
        """
        return self.get_with_headers_sync(path, Headers())

    async def post_with_headers(self, path: str, body: Any, custom_headers: Headers) -> Response:
        """Make a POST request with custom headers.
        
        Args:
            path: The API endpoint path
            body: The request body to send
            custom_headers: Additional headers to include
            
        Returns:
            The API response
        """
        url = f"{self.base_url}{path}"
        body_bytes = json.dumps(body).encode()
        headers = self._add_auth(path, custom_headers, body_bytes)
        response = await self.async_client.post(url, headers=headers, content=body_bytes)
        return response

    def post_with_headers_sync(self, path: str, body: Any, custom_headers: Headers) -> Response:
        """Make a synchronous POST request with custom headers.
        
        Args:
            path: The API endpoint path
            body: The request body to send
            custom_headers: Additional headers to include
            
        Returns:
            The API response
        """
        url = f"{self.base_url}{path}"
        body_bytes = json.dumps(body).encode()
        headers = self._add_auth(path, custom_headers, body_bytes)
        response = self.sync_client.post(url, headers=headers, content=body_bytes)
        return response

    async def get_with_headers(self, path: str, custom_headers: Headers) -> Response:
        """Make a GET request with custom headers.
        
        Args:
            path: The API endpoint path
            custom_headers: Additional headers to include
            
        Returns:
            The API response
        """
        url = f"{self.base_url}{path}"
        headers = self._add_auth(path, custom_headers, b"")
        response = await self.async_client.get(url, headers=headers)
        return response

    def get_with_headers_sync(self, path: str, custom_headers: Headers) -> Response:
        """Make a synchronous GET request with custom headers.
        
        Args:
            path: The API endpoint path
            custom_headers: Additional headers to include
            
        Returns:
            The API response
        """
        url = f"{self.base_url}{path}"
        headers = self._add_auth(path, custom_headers, b"")
        response = self.sync_client.get(url, headers=headers)
        return response

    def _get_header_bytes(self, headers: Headers) -> bytes:
        """Get sorted Renegade headers bytes for signature calculation.
        
        This method extracts all headers with the x-renegade prefix (except auth),
        sorts them by key, and concatenates them into a single byte string.
        
        Args:
            headers: The headers to process
            
        Returns:
            A byte string containing the concatenated header data
        """
        renegade_headers = []
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower.startswith(RENEGADE_HEADER_NAMESPACE) and key_lower != RENEGADE_AUTH_HEADER_NAME:
                renegade_headers.append((key_lower, value))
        
        # Sort headers by key
        renegade_headers.sort(key=lambda x: x[0])
        
        # Concatenate headers
        header_bytes = b""
        for key, value in renegade_headers:
            current = key.encode() + str(value).encode()
            header_bytes += current
        
        return header_bytes

    def _add_auth(self, path: str, headers: Headers, body: bytes) -> Headers:
        """Add authentication headers to a request.
        
        This method adds the expiration timestamp and HMAC signature headers
        required for request authentication.
        
        Args:
            path: The request path
            headers: The existing headers
            body: The request body bytes
            
        Returns:
            Headers with authentication information added
        """
        # Add timestamp and expiry
        timestamp = int(time.time() * 1000)
        expiry = timestamp + int(REQUEST_SIGNATURE_DURATION.total_seconds() * 1000)
        headers[RENEGADE_SIG_EXPIRATION_HEADER_NAME] = str(expiry)
        
        # Calculate signature
        path_bytes = path.encode()
        header_bytes = self._get_header_bytes(headers)
        message = path_bytes + header_bytes + body

        signature = hmac.new(self.auth_key, message, hashlib.sha256).digest()
        b64_signature = base64.b64encode(signature).decode().rstrip("=")
        
        headers[RENEGADE_AUTH_HEADER_NAME] = b64_signature
        return headers 