"""DataUpdateCoordinator for EV Charger."""

from datetime import timedelta, datetime
import logging
import asyncio
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, SCAN_INTERVAL, DEFAULT_TIMEOUT, IDLE_SCAN_INTERVAL
from .api_client import EVChargerApiClient
from .retry import AdaptivePollingStrategy
from .exceptions import AuthenticationError, NoActiveSessionError

_LOGGER = logging.getLogger(__name__)


class EVChargerDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        config_entry,
    ) -> None:
        """Initialize coordinator."""
        self.polling_strategy = AdaptivePollingStrategy(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self.polling_strategy.update_interval,
        )

        self.config_entry = config_entry
        self.api_client = self._create_client(hass, config_entry)

        # Initialize variables for active session polling
        self._active_session_task: asyncio.Task | None = None
        self._active_session_interval = timedelta(seconds=30)
        self._active_session_running = False

    def _create_client(self, hass: HomeAssistant, config_entry) -> EVChargerApiClient:
        """Create API client instance."""
        return EVChargerApiClient(
            host=config_entry.data["api_host"],
            chargepoint_id=config_entry.data["chargepoint_id"],
            auth_token=config_entry.data["auth_token"],
            session=async_get_clientsession(hass),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            _LOGGER.debug("Fetching charger status")
            charger_status = await self.api_client.get_charger_status()

            # Extract EVSE status
            evse = charger_status.get("data", {}).get("evses", [{}])[0]
            evse_status = evse.get("status", "unknown")

            active_session = {}
            session_from_chargepoint = evse.get("session", {})

            # Check if there's a session in the charge_point info
            if session_from_chargepoint and "id" in session_from_chargepoint:
                _LOGGER.debug(
                    "Found session in charge_point info: %s",
                    session_from_chargepoint["id"],
                )
                # Store this session ID in the client for potential stop_charging operations
                self.api_client._active_session_id = session_from_chargepoint["id"]

                # For "charging" state, still try to get the full session data from the active endpoint
                if evse_status == "charging":
                    _LOGGER.debug("Charger is charging, fetching active session")
                    try:
                        active_session = await self.api_client.get_active_session()
                        self._start_active_session_polling()
                    except Exception as err:
                        _LOGGER.debug(
                            "Failed to get active session despite charging status: %s. Using session from charge_point.",
                            str(err),
                        )
                        # Use the session from charge_point info as fallback
                        active_session = {"session": session_from_chargepoint}
                        self._start_active_session_polling()
                # For "preparing" state, use the session from charge_point info
                elif evse_status == "preparing":
                    _LOGGER.debug(
                        "Charger is preparing, using session from charge_point info"
                    )
                    active_session = {"session": session_from_chargepoint}
                    self._start_active_session_polling()
                else:
                    _LOGGER.debug(
                        "Charger not charging or preparing, using session from charge_point for tracking"
                    )
                    active_session = {"session": session_from_chargepoint}
                    self._stop_active_session_polling()
            else:
                _LOGGER.debug("No session found in charge_point info")
                self._stop_active_session_polling()

            # Update polling strategy based on charging status
            is_charging = evse_status in ["charging", "preparing"]
            self.polling_strategy.update_charging_state(is_charging)

            # Update the coordinator's update interval
            old_interval = self.update_interval
            self.update_interval = self.polling_strategy.update_interval
            _LOGGER.debug(
                "Updated coordinator interval: %s -> %s",
                old_interval,
                self.update_interval,
            )

            return {
                "status": charger_status.get("data", {}),
                "session": active_session.get("session", {}),
            }

        except AuthenticationError as err:
            _LOGGER.error("Authentication failed: %s", str(err))
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            _LOGGER.error("Update failed: %s", str(err))
            await self.polling_strategy.handle_error(err)
            raise UpdateFailed(f"Update failed: {err}") from err

    async def start_charging(
        self, evse_id: str, max_current: Optional[int] = None
    ) -> dict[str, Any]:
        """Start charging session.

        Args:
            evse_id: The ID of the EVSE to start charging
            max_current: Optional maximum charging current in amperes (6-32A)
        """
        _LOGGER.debug(
            f"Starting charging with EVSE ID: {evse_id}, max current: {max_current or 'default'}"
        )
        result = await self.api_client.start_charging(evse_id, max_current)
        self.polling_strategy.update_charging_state(True)
        await self.async_refresh()
        self._start_active_session_polling()
        return result

    async def stop_charging(self) -> dict[str, Any]:
        """Stop charging session."""
        try:
            result = await self.api_client.stop_charging()
            self.polling_strategy.update_charging_state(False)
            await self.async_refresh()
            self._stop_active_session_polling()
            return result
        except Exception as err:
            _LOGGER.error("Error stopping charging session: %s", str(err))
            # Force update data to get latest state
            await self.async_refresh()
            # Still stop polling since we attempted to stop
            self.polling_strategy.update_charging_state(False)
            self._stop_active_session_polling()
            # Re-raise the error for the service call handler
            raise

    def _start_active_session_polling(self) -> None:
        """Start the active session polling loop."""
        if not self._active_session_running:
            _LOGGER.debug("Starting active session polling loop")
            self._active_session_running = True
            self._active_session_task = asyncio.create_task(self._active_session_loop())

    def _stop_active_session_polling(self) -> None:
        """Stop the active session polling loop."""
        if self._active_session_running and self._active_session_task:
            _LOGGER.debug("Stopping active session polling loop")
            self._active_session_task.cancel()
            self._active_session_running = False

    async def _active_session_loop(self) -> None:
        """Loop to poll active session data every 30 seconds."""
        while self._active_session_running:
            try:
                _LOGGER.debug("Fetching active session data")
                try:
                    active_session = await self.api_client.get_active_session()
                    if active_session and active_session.get("session"):
                        self.data["session"] = active_session.get("session", {})
                        self.async_set_updated_data(self.data)
                    else:
                        # If active_session endpoint doesn't return data, check charge_point info
                        _LOGGER.debug(
                            "No data from active session endpoint, checking charge_point info"
                        )
                        charger_status = await self.api_client.get_charger_status()
                        evse = charger_status.get("data", {}).get("evses", [{}])[0]
                        evse_status = evse.get("status", "unknown")
                        session_from_chargepoint = evse.get("session", {})

                        if (
                            session_from_chargepoint
                            and "id" in session_from_chargepoint
                        ):
                            _LOGGER.debug(
                                "Using session from charge_point info: %s",
                                session_from_chargepoint["id"],
                            )
                            self.api_client._active_session_id = (
                                session_from_chargepoint["id"]
                            )
                            self.data["session"] = session_from_chargepoint
                            self.async_set_updated_data(self.data)

                            # If not in a charging or preparing state but we have a session, the session might have ended
                            if evse_status not in ["charging", "preparing"]:
                                _LOGGER.debug(
                                    "EVSE not in charging/preparing state - session might have ended"
                                )
                                self._stop_active_session_polling()
                                await self.async_refresh()
                                break
                        else:
                            _LOGGER.debug(
                                "No session found in charge_point info, stopping polling"
                            )
                            self._stop_active_session_polling()
                            await self.async_refresh()
                            break
                except NoActiveSessionError:
                    # Check charge_point info as a fallback
                    _LOGGER.debug("No active session found, checking charge_point info")
                    charger_status = await self.api_client.get_charger_status()
                    evse = charger_status.get("data", {}).get("evses", [{}])[0]
                    evse_status = evse.get("status", "unknown")
                    session_from_chargepoint = evse.get("session", {})

                    if (
                        session_from_chargepoint
                        and "id" in session_from_chargepoint
                        and evse_status in ["charging", "preparing"]
                    ):
                        _LOGGER.debug(
                            "Found active session in charge_point info, status: %s",
                            evse_status,
                        )
                        self.api_client._active_session_id = session_from_chargepoint[
                            "id"
                        ]
                        self.data["session"] = session_from_chargepoint
                        self.async_set_updated_data(self.data)
                    else:
                        _LOGGER.debug(
                            "Active session ended, stopping active session polling"
                        )
                        self._stop_active_session_polling()
                        await self.async_refresh()
                        break
            except AuthenticationError as err:
                _LOGGER.error(
                    "Authentication failed during active session polling: %s", str(err)
                )
                self._stop_active_session_polling()
                raise ConfigEntryAuthFailed from err
            except Exception as err:
                _LOGGER.error("Error during active session polling: %s", str(err))
                await self.polling_strategy.handle_error(err)
                # Don't immediately break the polling loop on general errors
                # It might be a temporary issue

            await asyncio.sleep(self._active_session_interval.total_seconds())

    async def manual_update_evse_status(self) -> None:
        """Manually trigger a data update for EVSE status."""
        _LOGGER.debug("Manually triggering EVSE status update")
        await self.async_refresh()
