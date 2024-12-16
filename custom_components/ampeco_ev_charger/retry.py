"""Retry strategy implementation."""
from datetime import datetime, timedelta
import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    MAX_RETRIES,
    MIN_TIME_BETWEEN_RETRIES,
    BACKOFF_MULTIPLIER,
    SCAN_INTERVAL,
    IDLE_SCAN_INTERVAL,
)
from .exceptions import AmpecoEVChargerError, NoActiveSessionError

_LOGGER = logging.getLogger(__name__)

class AdaptivePollingStrategy:
    """Handles adaptive polling intervals based on charging state."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the strategy."""
        self.hass = hass
        self._retry_count = 0
        self._last_retry: Optional[datetime] = None
        self._current_interval = SCAN_INTERVAL
        self._is_charging = False
        _LOGGER.debug(
            "Initializing AdaptivePollingStrategy with initial interval: %s",
            self._current_interval
        )

    def update_charging_state(self, has_active_session: bool) -> None:
        """Update the charging state and adjust polling interval."""
        old_state = self._is_charging
        old_interval = self._current_interval
        
        self._is_charging = has_active_session
        self._current_interval = SCAN_INTERVAL if has_active_session else IDLE_SCAN_INTERVAL
        
        _LOGGER.debug(
            "Charging state changed: %s -> %s, interval: %s -> %s",
            old_state,
            self._is_charging,
            old_interval,
            self._current_interval
        )

    async def handle_error(self, error: Exception) -> None:
        """Handle errors and implement retry logic."""
        now = datetime.now()
        _LOGGER.debug("Handling error: %s", str(error))

        if isinstance(error, NoActiveSessionError):
            _LOGGER.debug("No active session, updating charging state to False")
            self.update_charging_state(False)
            return None

        if (self._last_retry and 
            now - self._last_retry < MIN_TIME_BETWEEN_RETRIES):
            _LOGGER.debug(
                "Too many retries. Last retry: %s, minimum delay: %s",
                self._last_retry,
                MIN_TIME_BETWEEN_RETRIES
            )
            raise UpdateFailed("Too many requests") from error

        self._retry_count += 1
        self._last_retry = now
        _LOGGER.debug("Retry count increased to: %d", self._retry_count)

        if self._retry_count <= MAX_RETRIES:
            delay = MIN_TIME_BETWEEN_RETRIES * (BACKOFF_MULTIPLIER ** (self._retry_count - 1))
            _LOGGER.warning(
                "Update failed. Retry %d/%d in %s: %s",
                self._retry_count,
                MAX_RETRIES,
                delay,
                str(error),
            )
            raise UpdateFailed("Temporary failure") from error
        
        _LOGGER.debug("Max retries exceeded, resetting retry count")
        self._retry_count = 0
        raise UpdateFailed("Update failed") from error

    @property
    def update_interval(self) -> timedelta:
        """Get the current update interval."""
        _LOGGER.debug("Current update interval: %s", self._current_interval)
        return self._current_interval