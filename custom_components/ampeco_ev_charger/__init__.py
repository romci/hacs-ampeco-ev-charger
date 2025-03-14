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

        # Add detailed debug logging
        _LOGGER.debug("Found device for start_charging: %s", device)
        _LOGGER.debug(
            "Device config entries for start_charging: %s", device.config_entries
        )
        _LOGGER.debug("Device identifiers for start_charging: %s", device.identifiers)
        _LOGGER.debug("DOMAIN: %s", DOMAIN)

        # Verify the device belongs to our integration by checking identifiers
        # A device belongs to our integration if it has an identifier with our domain
        device_belongs_to_integration = False
        for domain, identifier in device.identifiers:
            _LOGGER.debug("Checking identifier domain for start_charging: %s", domain)
            if domain == DOMAIN:
                device_belongs_to_integration = True
                _LOGGER.debug(
                    "Device belongs to our integration via identifier: %s", identifier
                )
                break

        if not device_belongs_to_integration:
            _LOGGER.error("Device %s is not an AMPECO EV Charger", device_id)
            _LOGGER.error(
                "Device identifiers: %s, DOMAIN: %s", device.identifiers, DOMAIN
            )
            raise ValueError(f"Device {device_id} is not an AMPECO EV Charger")

        # Get the coordinator for this device
        try:
            # Find a config entry for this device that belongs to our integration
            # and has a coordinator in the hass.data dictionary
            coordinator = None
            for entry_id in device.config_entries:
                # Check if this entry exists in our data dictionary
                if entry_id in hass.data.get(DOMAIN, {}):
                    coordinator = hass.data[DOMAIN][entry_id]
                    _LOGGER.debug("Found coordinator using entry_id: %s", entry_id)
                    break

            if not coordinator:
                _LOGGER.error(
                    "Failed to find coordinator for device %s. No matching entry in hass.data[DOMAIN]",
                    device_id,
                )
                raise ValueError(
                    f"Failed to get controller for device {device_id}: No matching entry found"
                )
        except Exception as err:
            _LOGGER.error(
                "Failed to find coordinator for device %s: %s", device_id, err
            )
            raise ValueError(
                f"Failed to get controller for device {device_id}"
            ) from err

        # Get the EVSE ID from the device identifiers
        try:
            evse_id = next(
                (ident[1] for ident in device.identifiers if ident[0] == DOMAIN), None
            )
            if not evse_id:
                _LOGGER.error("No EVSE ID found for device %s", device_id)
                raise ValueError(f"No EVSE ID found for device {device_id}")
        except Exception as err:
            _LOGGER.error("Error getting EVSE ID: %s", err)
            raise ValueError("Failed to get EVSE ID") from err

        # Get max_current from call data if provided
        max_current = call.data.get("max_current")
        _LOGGER.debug("Starting charging with max_current: %s", max_current)

        try:
            await coordinator.start_charging(evse_id, max_current)
        except Exception as err:
            _LOGGER.error("Failed to start charging: %s", err)
            raise

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

        # Add detailed debug logging
        _LOGGER.debug("Found device: %s", device)
        _LOGGER.debug("Device config entries: %s", device.config_entries)
        _LOGGER.debug("Device identifiers: %s", device.identifiers)
        _LOGGER.debug("DOMAIN: %s", DOMAIN)

        # Check each config entry and log details
        for entry_id in device.config_entries:
            _LOGGER.debug("Checking entry: %s", entry_id)
            _LOGGER.debug("Entry domain part: %s", entry_id.split(".")[0])

        # Verify the device belongs to our integration by checking identifiers
        # A device belongs to our integration if it has an identifier with our domain
        device_belongs_to_integration = False
        for domain, identifier in device.identifiers:
            _LOGGER.debug("Checking identifier domain: %s", domain)
            if domain == DOMAIN:
                device_belongs_to_integration = True
                _LOGGER.debug(
                    "Device belongs to our integration via identifier: %s", identifier
                )
                break

        if not device_belongs_to_integration:
            _LOGGER.error("Device %s is not an AMPECO EV Charger", device_id)
            _LOGGER.error(
                "Device identifiers: %s, DOMAIN: %s", device.identifiers, DOMAIN
            )
            raise ValueError(f"Device {device_id} is not an AMPECO EV Charger")

        # Get the coordinator for this device
        try:
            # Find a config entry for this device that belongs to our integration
            # and has a coordinator in the hass.data dictionary
            coordinator = None
            for entry_id in device.config_entries:
                # Check if this entry exists in our data dictionary
                if entry_id in hass.data.get(DOMAIN, {}):
                    coordinator = hass.data[DOMAIN][entry_id]
                    _LOGGER.debug("Found coordinator using entry_id: %s", entry_id)
                    break

            if not coordinator:
                _LOGGER.error(
                    "Failed to find coordinator for device %s. No matching entry in hass.data[DOMAIN]",
                    device_id,
                )
                raise ValueError(
                    f"Failed to get controller for device {device_id}: No matching entry found"
                )
        except Exception as err:
            _LOGGER.error(
                "Failed to find coordinator for device %s: %s", device_id, err
            )
            raise ValueError(
                f"Failed to get controller for device {device_id}"
            ) from err

        try:
            await coordinator.stop_charging()
        except Exception as err:
            _LOGGER.error("Failed to stop charging: %s", err)
            raise

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

        # Add detailed debug logging
        _LOGGER.debug("Found device for update_data: %s", device)
        _LOGGER.debug(
            "Device config entries for update_data: %s", device.config_entries
        )
        _LOGGER.debug("Device identifiers for update_data: %s", device.identifiers)
        _LOGGER.debug("DOMAIN: %s", DOMAIN)

        # Verify the device belongs to our integration by checking identifiers
        # A device belongs to our integration if it has an identifier with our domain
        device_belongs_to_integration = False
        for domain, identifier in device.identifiers:
            _LOGGER.debug("Checking identifier domain for update_data: %s", domain)
            if domain == DOMAIN:
                device_belongs_to_integration = True
                _LOGGER.debug(
                    "Device belongs to our integration via identifier: %s", identifier
                )
                break

        if not device_belongs_to_integration:
            _LOGGER.error("Device %s is not an AMPECO EV Charger", device_id)
            _LOGGER.error(
                "Device identifiers: %s, DOMAIN: %s", device.identifiers, DOMAIN
            )
            raise ValueError(f"Device {device_id} is not an AMPECO EV Charger")

        # Get the coordinator for this device
        try:
            # Find a config entry for this device that belongs to our integration
            # and has a coordinator in the hass.data dictionary
            coordinator = None
            for entry_id in device.config_entries:
                # Check if this entry exists in our data dictionary
                if entry_id in hass.data.get(DOMAIN, {}):
                    coordinator = hass.data[DOMAIN][entry_id]
                    _LOGGER.debug("Found coordinator using entry_id: %s", entry_id)
                    break

            if not coordinator:
                _LOGGER.error(
                    "Failed to find coordinator for device %s. No matching entry in hass.data[DOMAIN]",
                    device_id,
                )
                raise ValueError(
                    f"Failed to get controller for device {device_id}: No matching entry found"
                )
        except Exception as err:
            _LOGGER.error(
                "Failed to find coordinator for device %s: %s", device_id, err
            )
            raise ValueError(
                f"Failed to get controller for device {device_id}"
            ) from err

        _LOGGER.debug("Manual update triggered for device %s", device_id)
        try:
            await coordinator.manual_update_evse_status()
        except Exception as err:
            _LOGGER.error("Failed to update device status: %s", err)
            raise

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
