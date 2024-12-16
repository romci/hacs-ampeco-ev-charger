"""DataUpdateCoordinator for EV Charger."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, SCAN_INTERVAL, DEFAULT_TIMEOUT
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

            try:
                _LOGGER.debug("Fetching active session")
                active_session = await self.api_client.get_active_session()

                # Check if we actually have session data
                has_active_session = bool(
                    active_session and active_session.get("session")
                )
                _LOGGER.debug(
                    "Active session check: %s, updating polling strategy",
                    "found" if has_active_session else "not found",
                )
                self.polling_strategy.update_charging_state(has_active_session)

            except NoActiveSessionError:
                _LOGGER.debug("No active session found")
                active_session = {}
                self.polling_strategy.update_charging_state(False)

            # Update the coordinator's update interval
            old_interval = self.update_interval
            self.update_interval = self.polling_strategy.update_interval
            _LOGGER.debug(
                "Updated coordinator interval from to: %s -> %s",
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
        return result

    async def stop_charging(self) -> dict[str, Any]:
        """Stop charging session."""
        result = await self.api_client.stop_charging()
        self.polling_strategy.update_charging_state(False)
        await self.async_refresh()
        return result
