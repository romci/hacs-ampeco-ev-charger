"""API Client for EV Charger."""
from __future__ import annotations

import logging
import aiohttp
import async_timeout
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

class EVChargerApiClient:
    """API Client for EV Charger."""

    def __init__(
        self,
        host: str,
        chargepoint_id: str,
        auth_token: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._host = host.rstrip("/")
        self._chargepoint_id = chargepoint_id
        self._auth_token = auth_token
        self._session = session
        self._active_session_id: str | None = None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        """Make request to the API."""
        headers = {
            "Authorization": f"Bearer {self._auth_token}",
            "Content-Type": "application/json",
        }

        url = f"{self._host}/api/v1/{endpoint}"

        async with async_timeout.timeout(10):
            response = await self._session.request(
                method,
                url,
                headers=headers,
                json=json_data,
            )
            
            if response.status == 404:
                return {}
                
            response.raise_for_status()
            return await response.json()

    async def get_charger_status(self) -> dict[str, Any]:
        """Get charger status."""
        response = await self._make_request(
            "GET",
            f"app/personal/charge-points/{self._chargepoint_id}"
        )
        return response.get("data", {})

    async def get_active_session(self) -> dict[str, Any]:
        """Get active charging session."""
        try:
            response = await self._make_request("GET", "app/session/active")
            session_data = response.get("session", {})
            if session_data:
                self._active_session_id = session_data.get("id")
            return session_data
        except aiohttp.ClientResponseError as err:
            if err.status == 404:
                self._active_session_id = None
                return {}
            raise

    async def start_charging(self, evse_id: str) -> dict[str, Any]:
        """Start charging session."""
        response = await self._make_request(
            "POST",
            "app/session/start",
            {"evseId": evse_id}
        )
        session_data = response.get("session", {})
        if session_data:
            self._active_session_id = session_data.get("id")
        return session_data

    async def stop_charging(self) -> dict[str, Any]:
        """Stop charging session."""
        if not self._active_session_id:
            raise HomeAssistantError("No active charging session to stop")
            
        response = await self._make_request(
            "POST",
            f"app/session/{self._active_session_id}/end"
        )
        session_data = response.get("session", {})
        self._active_session_id = None
        return session_data 