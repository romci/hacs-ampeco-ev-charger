"""DataUpdateCoordinator for EV Charger."""
import async_timeout
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

from .const import (
    DOMAIN,
    SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    MIN_TIME_BETWEEN_RETRIES,
)
from .api_client import EVChargerApiClient

_LOGGER = logging.getLogger(__name__)

class EVChargerDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        config_entry,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.config_entry = config_entry
        self._retry_count = 0
        self._last_retry = None
        session = async_get_clientsession(hass)
        self.api_client = EVChargerApiClient(
            host=config_entry.data["api_host"],
            chargepoint_id=config_entry.data["chargepoint_id"],
            auth_token=config_entry.data["auth_token"],
            session=session,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            async with async_timeout.timeout(DEFAULT_TIMEOUT):
                charger_status = await self.api_client.get_charger_status()
                active_session = await self.api_client.get_active_session()

            # Reset retry count on successful update
            self._retry_count = 0
            self._last_retry = None

            return {
                "status": charger_status,
                "session": active_session
            }

        except TimeoutError as error:
            self._handle_error("Timeout error")
            raise UpdateFailed("Timeout error") from error
        except aiohttp.ClientResponseError as error:
            if error.status == 401:
                raise ConfigEntryAuthFailed("Invalid authentication")
            self._handle_error(f"API error: {error.status}")
            raise UpdateFailed(f"API error: {error.status}") from error
        except Exception as error:
            self._handle_error(f"Unexpected error: {error}")
            raise UpdateFailed(f"Unexpected error: {error}") from error

    def _handle_error(self, error_msg: str) -> None:
        """Handle error and implement retry logic."""
        now = dt_util.utcnow()
        
        # Check if enough time has passed since last retry
        if (self._last_retry and 
            now - self._last_retry < MIN_TIME_BETWEEN_RETRIES):
            return

        self._retry_count += 1
        self._last_retry = now

        if self._retry_count <= MAX_RETRIES:
            _LOGGER.warning(
                "%s. Retry attempt %s/%s",
                error_msg,
                self._retry_count,
                MAX_RETRIES,
            )
            self.async_set_update_interval(SCAN_INTERVAL * self._retry_count)
        else:
            _LOGGER.error(
                "%s. Max retries (%s) exceeded. Will continue with normal update interval",
                error_msg,
                MAX_RETRIES,
            )
            self._retry_count = 0
            self.async_set_update_interval(SCAN_INTERVAL)

    async def start_charging(self, evse_id: str):
        """Start charging session."""
        return await self.api_client.start_charging(evse_id)

    async def stop_charging(self):
        """Stop charging session."""
        return await self.api_client.stop_charging() 