"""API Client for EV Charger."""

from __future__ import annotations

import logging
import aiohttp
import async_timeout
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)
# Uncomment this line to enable debug logging for this integration
logging.getLogger(__name__).setLevel(logging.DEBUG)


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
        _LOGGER.debug("Making %s request to %s", method, url)
        if json_data:
            _LOGGER.debug("Request data: %s", json_data)

        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method,
                    url,
                    headers=headers,
                    json=json_data,
                )

                _LOGGER.debug(
                    "Response status: %s, Headers: %s",
                    response.status,
                    response.headers,
                )

                if response.status == 404:
                    _LOGGER.warning("Endpoint not found: %s", url)
                    return {}

                response.raise_for_status()
                data = await response.json()
                _LOGGER.debug("Response data: %s", data)
                return data

        except aiohttp.ClientResponseError as err:
            _LOGGER.error(
                "HTTP error %s during %s request to %s: %s",
                err.status,
                method,
                url,
                err.message,
            )
            raise
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout during %s request to %s", method, url)
            raise
        except Exception as err:
            _LOGGER.error(
                "Unexpected error during %s request to %s: %s", method, url, str(err)
            )
            raise

    async def get_charger_status(self) -> dict[str, Any]:
        """Get charger status."""
        response = await self._make_request(
            "GET", f"app/personal/charge-points/{self._chargepoint_id}"
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
