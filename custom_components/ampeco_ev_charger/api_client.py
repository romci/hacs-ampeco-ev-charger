"""API Client for EV Charger."""

from __future__ import annotations

import logging
import aiohttp
import async_timeout
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .base_api_client import BaseApiClient
from .exceptions import ConnectionError

_LOGGER = logging.getLogger(__name__)
# Uncomment this line to enable debug logging for this integration
logging.getLogger(__name__).setLevel(logging.DEBUG)


class EVChargerApiClient(BaseApiClient):
    """AMPECO EV Charger API client."""

    def __init__(
        self,
        host: str,
        chargepoint_id: str,
        auth_token: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        super().__init__(host, session)
        self._chargepoint_id = chargepoint_id
        self._auth_token = auth_token
        self._headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        self._active_session_id: str | None = None

    async def get_charger_status(self) -> dict[str, Any]:
        """Get charger status."""
        return await self._make_request(
            "GET",
            f"app/personal/charge-points/{self._chargepoint_id}",
            headers=self._headers,
        )

    async def get_active_session(self) -> dict[str, Any]:
        """Get active charging session."""
        try:
            response = await self._make_request(
                "GET",
                "app/session/active",
                headers=self._headers,
            )
            session_data = response.get("session", {})
            self._active_session_id = session_data.get("id") if session_data else None
            return session_data
        except ConnectionError:
            self._active_session_id = None
            return {}

    async def start_charging(self, evse_id: str) -> dict[str, Any]:
        """Start charging session."""
        response = await self._make_request(
            "POST", "app/session/start", {"evseId": evse_id}
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
            "POST", f"app/session/{self._active_session_id}/end"
        )
        session_data = response.get("session", {})
        self._active_session_id = None
        return session_data
