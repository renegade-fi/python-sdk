from typing import Any, TypeVar 
from datetime import timedelta
import json
import hmac
import hashlib
import time
import base64
from httpx import AsyncClient, Headers, Response

REQUEST_SIGNATURE_DURATION = timedelta(seconds=10)
RENEGADE_HEADER_NAMESPACE = "x-renegade"
RENEGADE_AUTH_HEADER_NAME = "x-renegade-auth"
RENEGADE_SIG_EXPIRATION_HEADER_NAME = "x-renegade-auth-expiration"

T = TypeVar('T')
Req = TypeVar('Req')
Resp = TypeVar('Resp')

class RelayerHttpClient:
    def __init__(self, base_url: str, auth_key: str):
        self.client = AsyncClient()
        self.base_url = base_url
        # Decode base64 auth key
        self.auth_key = base64.b64decode(auth_key)

    async def post(self, path: str, body: Any) -> Response:
        return await self.post_with_headers(path, body, Headers())

    async def get(self, path: str) -> Response:
        return await self.get_with_headers(path, Headers())

    async def post_with_headers(self, path: str, body: Any, custom_headers: Headers) -> Response:
        url = f"{self.base_url}{path}"
        body_bytes = json.dumps(body).encode()
        headers = self._add_auth(path, custom_headers, body_bytes)
        response = await self.client.post(url, headers=headers, content=body_bytes)
        return response

    async def get_with_headers(self, path: str, custom_headers: Headers) -> Response:
        url = f"{self.base_url}{path}"
        headers = self._add_auth(path, custom_headers, b"")
        
        response = await self.client.get(url, headers=headers)
        return response

    def _get_header_bytes(self, headers: Headers) -> bytes:
        """Get sorted Renegade headers bytes for signature calculation"""
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