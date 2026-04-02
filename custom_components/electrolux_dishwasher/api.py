"""Electrolux OCP API client."""

import asyncio
import hashlib
import hmac
import logging
import time
from urllib.parse import quote

import aiohttp

from .const import (
    GIGYA_API_KEY,
    GIGYA_DOMAIN,
    OCP_API_KEY,
    OCP_BASE_URL,
    OCP_CLIENT_ID,
    OCP_CLIENT_SECRET,
    OCP_WS_URL,
)

_LOGGER = logging.getLogger(__name__)


class ElectroluxApi:
    """Electrolux OCP API client with Gigya OTP authentication."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires: float = 0
        self._gigya_session: str | None = None

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "x-api-key": OCP_API_KEY,
            "Content-Type": "application/json",
        }

    async def _get_client_token(self) -> str:
        """Step 1: Get client credentials token."""
        async with self._session.post(
            f"{OCP_BASE_URL}/one-account-authorization/api/v1/token",
            headers={"x-api-key": OCP_API_KEY, "Content-Type": "application/json"},
            json={
                "grantType": "client_credentials",
                "clientId": OCP_CLIENT_ID,
                "clientSecret": OCP_CLIENT_SECRET,
                "scope": "",
            },
        ) as resp:
            data = await resp.json()
            return data["accessToken"]

    async def send_otp(self, email: str) -> str:
        """Send OTP code to email. Returns vToken for verification."""
        async with self._session.post(
            f"https://accounts.{GIGYA_DOMAIN}/accounts.otp.sendCode",
            data={
                "apiKey": GIGYA_API_KEY,
                "format": "json",
                "email": email,
                "lang": "de",
            },
        ) as resp:
            data = await resp.json(content_type=None)
            if data.get("errorCode", 0) != 0:
                raise Exception(f"OTP send failed: {data.get('errorMessage')}")
            return data["vToken"]

    async def verify_otp(self, vtoken: str, code: str) -> str:
        """Verify OTP code. Returns Gigya session token."""
        async with self._session.post(
            f"https://accounts.{GIGYA_DOMAIN}/accounts.otp.login",
            data={
                "apiKey": GIGYA_API_KEY,
                "format": "json",
                "vToken": vtoken,
                "code": code,
            },
        ) as resp:
            data = await resp.json(content_type=None)
            if data.get("errorCode", 0) != 0:
                raise Exception(f"OTP verify failed: {data.get('errorMessage')}")
            cookie_value = data["sessionInfo"]["cookieValue"]
            self._gigya_session = cookie_value
            return cookie_value

    async def _get_jwt(self, session_token: str) -> str:
        """Step 3c: Get JWT from Gigya session."""
        async with self._session.post(
            f"https://accounts.{GIGYA_DOMAIN}/accounts.getJWT",
            data={
                "apiKey": GIGYA_API_KEY,
                "format": "json",
                "login_token": session_token,
                "fields": "country",
            },
        ) as resp:
            data = await resp.json(content_type=None)
            if data.get("errorCode", 0) != 0:
                raise Exception(f"JWT failed: {data.get('errorMessage')}")
            return data["id_token"]

    async def _exchange_token(self, jwt: str) -> None:
        """Step 4: Exchange JWT for OCP access token."""
        async with self._session.post(
            f"{OCP_BASE_URL}/one-account-authorization/api/v1/token",
            headers={"x-api-key": OCP_API_KEY, "Content-Type": "application/json", "Origin-Country-Code": "DE"},
            json={
                "grantType": "urn:ietf:params:oauth:grant-type:token-exchange",
                "clientId": OCP_CLIENT_ID,
                "idToken": jwt,
                "scope": "",
            },
        ) as resp:
            data = await resp.json()
            self._access_token = data["accessToken"]
            self._refresh_token = data.get("refreshToken")
            self._token_expires = time.time() + data.get("expiresIn", 43200) - 300

    async def authenticate(self, session_token: str) -> None:
        """Full authentication from Gigya session token."""
        jwt = await self._get_jwt(session_token)
        await self._exchange_token(jwt)
        _LOGGER.info("Authenticated with OCP API")

    async def refresh_access_token(self) -> None:
        """Refresh the access token."""
        if not self._refresh_token:
            raise Exception("No refresh token available")
        async with self._session.post(
            f"{OCP_BASE_URL}/one-account-authorization/api/v1/token",
            headers={"x-api-key": OCP_API_KEY, "Content-Type": "application/json"},
            json={
                "grantType": "refresh_token",
                "clientId": OCP_CLIENT_ID,
                "refreshToken": self._refresh_token,
                "scope": "",
            },
        ) as resp:
            data = await resp.json()
            self._access_token = data["accessToken"]
            self._refresh_token = data.get("refreshToken", self._refresh_token)
            self._token_expires = time.time() + data.get("expiresIn", 43200) - 300
            _LOGGER.debug("Token refreshed")

    async def ensure_token(self) -> None:
        """Ensure we have a valid token."""
        if time.time() >= self._token_expires:
            if self._refresh_token:
                await self.refresh_access_token()
            elif self._gigya_session:
                await self.authenticate(self._gigya_session)
            else:
                raise Exception("No valid credentials for token refresh")

    async def get_appliances(self) -> list:
        """Get all registered appliances."""
        await self.ensure_token()
        async with self._session.get(
            f"{OCP_BASE_URL}/appliance/api/v2/appliances",
            headers=self.headers,
        ) as resp:
            return await resp.json()

    async def get_appliance(self, appliance_id: str) -> dict:
        """Get single appliance state."""
        await self.ensure_token()
        async with self._session.get(
            f"{OCP_BASE_URL}/appliance/api/v2/appliances/{appliance_id}",
            headers=self.headers,
        ) as resp:
            return await resp.json()

    async def get_capabilities(self, appliance_id: str) -> dict:
        """Get appliance capabilities."""
        await self.ensure_token()
        async with self._session.get(
            f"{OCP_BASE_URL}/appliance/api/v2/appliances/{appliance_id}/capabilities",
            headers=self.headers,
        ) as resp:
            return await resp.json()

    async def send_command(self, appliance_id: str, command: str) -> None:
        """Send command to appliance (ON, OFF, START, PAUSE, RESUME, STOPRESET)."""
        await self.ensure_token()
        async with self._session.put(
            f"{OCP_BASE_URL}/appliance/api/v2/appliances/{appliance_id}/command",
            headers=self.headers,
            json={"executeCommand": command},
        ) as resp:
            if resp.status not in (200, 204):
                text = await resp.text()
                raise Exception(f"Command {command} failed ({resp.status}): {text}")
            _LOGGER.info("Sent command %s to %s", command, appliance_id)

    async def set_property(self, appliance_id: str, properties: dict) -> None:
        """Set appliance properties."""
        await self.ensure_token()
        async with self._session.put(
            f"{OCP_BASE_URL}/appliance/api/v2/appliances/{appliance_id}/command",
            headers=self.headers,
            json=properties,
        ) as resp:
            if resp.status not in (200, 204):
                text = await resp.text()
                raise Exception(f"Set property failed ({resp.status}): {text}")
