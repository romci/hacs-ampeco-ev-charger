"""DataUpdateCoordinator for EV Charger."""

from datetime import timedelta, datetime
import logging
import asyncio
from typing import Any

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
            evse_status = (
                charger_status.get("data", {})
                .get("evses", [{}])[0]
                .get("status", "unknown")
            )

            active_session = {}
            if evse_status == "charging":
                _LOGGER.debug("Charger is charging, fetching active session")
                try:
                    active_session = await self.api_client.get_active_session()
                    self._start_active_session_polling()
                except NoActiveSessionError:
                    _LOGGER.debug("No active session found despite charging status")
                    active_session = {}
                    self._stop_active_session_polling()
            else:
                _LOGGER.debug("Charger not charging, skipping session fetch")
                self._stop_active_session_polling()

            # Update polling strategy based on charging status
            is_charging = evse_status == "charging"
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

    async def start_charging(self, evse_id: str) -> dict[str, Any]:
        """Start charging session."""
        result = await self.api_client.start_charging(evse_id)
        self.polling_strategy.update_charging_state(True)
        await self.async_refresh()
        self._start_active_session_polling()
        return result

    async def stop_charging(self) -> dict[str, Any]:
        """Stop charging session."""
        result = await self.api_client.stop_charging()
        self.polling_strategy.update_charging_state(False)
        await self.async_refresh()
        self._stop_active_session_polling()
        return result

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
                active_session = await self.api_client.get_active_session()
                self.data["session"] = active_session.get("session", {})
                self.async_set_updated_data(self.data)
            except NoActiveSessionError:
                _LOGGER.debug("Active session ended, stopping active session polling")
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
                raise UpdateFailed(f"Active session polling failed: {err}") from err

            await asyncio.sleep(self._active_session_interval.total_seconds())

    async def manual_update_evse_status(self) -> None:
        """Manually trigger a data update for EVSE status."""
        _LOGGER.debug("Manually triggering EVSE status update")
        await self.async_refresh()
