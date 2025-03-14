"""API Client for EV Charger."""

from __future__ import annotations

import logging
import aiohttp
import async_timeout
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .base_api_client import BaseApiClient
from .exceptions import ConnectionError, AlreadyChargingError

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
        """Get active charging session from charge point info.

        The app/session/active endpoint is no longer available, so we retrieve
        session data directly from the charge point info.
        """
        try:
            charger_status = await self.get_charger_status()
            evse = charger_status.get("data", {}).get("evses", [{}])[0]
            session_data = evse.get("session", {})

            if session_data and "id" in session_data:
                _LOGGER.debug(
                    "Found session in charge point info: %s, power: %s, energy: %s, duration: %s seconds",
                    session_data["id"],
                    session_data.get("power"),
                    session_data.get("energy"),
                    session_data.get("duration"),
                )
                self._active_session_id = session_data["id"]
                return {"session": session_data}
            else:
                _LOGGER.debug("No session found in charge point info")
                self._active_session_id = None
                return {}
        except Exception as err:
            _LOGGER.error("Failed to get session from charge point info: %s", str(err))
            self._active_session_id = None
            return {}

    async def start_charging(
        self, evse_id: str, max_current: Optional[int] = None
    ) -> dict[str, Any]:
        """Start charging session.

        Args:
            evse_id: The ID of the EVSE to start charging
            max_current: Optional maximum charging current in amperes (6-32A)
        """
        # First check if there's already an active session
        active_session = await self.get_active_session()
        if active_session and active_session.get("session"):
            session_data = active_session.get("session", {})
            session_id = session_data.get("id")
            _LOGGER.info(
                "Session already active with ID: %s, returning existing session data",
                session_id,
            )
            self._active_session_id = session_id
            return session_data

        payload = {"evseId": evse_id}

        # Add max_current to the payload if provided
        if max_current is not None:
            payload["maxCurrent"] = max_current

        try:
            response = await self._make_request(
                "POST", "app/session/start", headers=self._headers, json_data=payload
            )
            session_data = response.get("session", {})
            if session_data:
                self._active_session_id = session_data.get("id")
            return session_data
        except AlreadyChargingError:
            # If we get here, our initial check missed an active session
            # Try to get the session data again
            _LOGGER.info("Got AlreadyChargingError, fetching current session data")
            active_session = await self.get_active_session()
            if active_session and active_session.get("session"):
                session_data = active_session.get("session", {})
                self._active_session_id = session_data.get("id")
                return session_data
            # If we still can't find a session, re-raise the error
            raise

    async def stop_charging(self) -> dict[str, Any]:
        """Stop charging session."""
        if not self._active_session_id:
            # Get the latest session info directly
            await self.get_active_session()

            if not self._active_session_id:
                raise HomeAssistantError("No active charging session to stop")

        try:
            response = await self._make_request(
                "POST",
                f"app/session/{self._active_session_id}/end",
                headers=self._headers,
            )
            session_data = response.get("session", {})
            self._active_session_id = None
            return session_data
        except Exception as err:
            _LOGGER.error("Failed to stop charging session: %s", str(err))
            # Always clear the session ID to avoid getting stuck
            self._active_session_id = None
            raise
