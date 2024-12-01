"""Diagnostics support for EV Charger."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_AUTH_TOKEN, DOMAIN

TO_REDACT = {CONF_AUTH_TOKEN, "id", "name", "location"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    diagnostics_data = {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "data": {
            "status": async_redact_data(coordinator.data["status"], TO_REDACT),
            "session": async_redact_data(coordinator.data["session"], TO_REDACT),
        },
    }

    return diagnostics_data 