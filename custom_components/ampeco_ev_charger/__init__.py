"""The EV Charger integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, config_validation as cv
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers.service import verify_domain_control

from .const import (
    DOMAIN,
    SCAN_INTERVAL,
    SERVICE_START_CHARGING,
    SERVICE_STOP_CHARGING,
)
from .coordinator import EVChargerDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]

_LOGGER = logging.getLogger(__name__)

# Schema for service data, including device_id for direct service calls
SERVICE_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): cv.string,
        vol.Optional("max_current"): vol.All(vol.Coerce(int), vol.Range(min=6, max=32)),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EV Charger from a config entry."""
    coordinator = EVChargerDataUpdateCoordinator(
        hass,
        config_entry=entry,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Register services
    async def handle_start_charging(call: ServiceCall) -> None:
        """Handle the start charging service call."""
        _LOGGER.debug("Start charging service called with: %s", call.data)

        # Get device_id from call data
        device_id = call.data.get("device_id")
        if not device_id:
            _LOGGER.error("No device_id provided in service call")
            raise ValueError("No device_id provided in service call data")

        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)

        if not device:
            _LOGGER.error("Device %s not found", device_id)
            raise ValueError(f"Device {device_id} not found")

        # Get the coordinator for this device
        entry_id = next(iter(device.config_entries))
        coordinator = hass.data[DOMAIN][entry_id]

        # Get the EVSE ID from the device identifiers
        evse_id = next(
            (ident[1] for ident in device.identifiers if ident[0] == DOMAIN), None
        )
        if not evse_id:
            _LOGGER.error("No EVSE ID found for device %s", device_id)
            raise ValueError(f"No EVSE ID found for device {device_id}")

        # Get max_current from call data if provided
        max_current = call.data.get("max_current")
        _LOGGER.debug("Starting charging with max_current: %s", max_current)

        await coordinator.start_charging(evse_id, max_current)

    async def handle_stop_charging(call: ServiceCall) -> None:
        """Handle the stop charging service call."""
        _LOGGER.debug("Stop charging service called with: %s", call.data)

        # Get device_id from call data
        device_id = call.data.get("device_id")
        if not device_id:
            _LOGGER.error("No device_id provided in service call")
            raise ValueError("No device_id provided in service call data")

        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)

        if not device:
            _LOGGER.error("Device %s not found", device_id)
            raise ValueError(f"Device {device_id} not found")

        # Get the coordinator for this device
        entry_id = next(iter(device.config_entries))
        coordinator = hass.data[DOMAIN][entry_id]

        await coordinator.stop_charging()

    async def handle_update_data(call: ServiceCall) -> None:
        """Handle the update data service call."""
        _LOGGER.debug("Update data service called with: %s", call.data)

        # Get device_id from call data
        device_id = call.data.get("device_id")
        if not device_id:
            _LOGGER.error("No device_id provided in service call")
            raise ValueError("No device_id provided in service call data")

        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)

        if not device:
            _LOGGER.error("Device %s not found", device_id)
            raise ValueError(f"Device {device_id} not found")

        # Get the coordinator for this device
        entry_id = next(iter(device.config_entries))
        coordinator = hass.data[DOMAIN][entry_id]

        _LOGGER.debug("Manual update triggered for device %s", device_id)
        await coordinator.manual_update_evse_status()

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_CHARGING,
        handle_start_charging,
        schema=SERVICE_DATA_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_CHARGING,
        handle_stop_charging,
        schema=SERVICE_DATA_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        "update_data",
        handle_update_data,
        schema=SERVICE_DATA_SCHEMA,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # Remove services if this is the last config entry
        if not hass.data[DOMAIN]:
            for service in [
                SERVICE_START_CHARGING,
                SERVICE_STOP_CHARGING,
                "update_data",
            ]:
                if hass.services.has_service(DOMAIN, service):
                    hass.services.async_remove(DOMAIN, service)

    return unload_ok
