"""Sensor platform for EV Charger integration."""

from __future__ import annotations

import re
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.helpers.entity import EntityCategory
from typing import Any

from .const import DOMAIN, SENSOR_TYPE_CHARGER_STATUS, SENSOR_TYPE_CHARGING_SESSION
from .coordinator import EVChargerDataUpdateCoordinator


def generate_slug(text: str) -> str:
    """Generate a slug from a string.

    Args:
        text: The string to convert to a slug

    Returns:
        A lowercase string with non-alphanumeric characters removed
    """
    # Convert to lowercase and replace any non-alphanumeric characters with underscores
    return re.sub(r"[^a-z0-9]", "_", text.lower())


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the EV Charger sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    chargepoint_id = config_entry.data["chargepoint_id"]

    # Create a slug from the chargepoint ID for use in entity IDs
    chargepoint_slug = generate_slug(chargepoint_id)

    sensors = [
        ChargerStatusSensor(coordinator, chargepoint_slug),
        ChargingSessionSensor(coordinator, chargepoint_slug),
        ChargingCurrentSensor(coordinator, chargepoint_slug),
        ChargingEnergySensor(coordinator, chargepoint_slug),
        ChargingDurationSensor(coordinator, chargepoint_slug),
        PollingIntervalSensor(coordinator, chargepoint_slug),
        EVSEStatusSensor(coordinator, chargepoint_slug),
        MaxCurrentSensor(coordinator, chargepoint_slug),
        LastMonthStatsSensor(coordinator, chargepoint_slug),
        SessionIDSensor(coordinator, chargepoint_slug),
    ]

    async_add_entities(sensors)


class EVChargerBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for EV Charger sensors."""

    def __init__(
        self,
        coordinator: EVChargerDataUpdateCoordinator,
        sensor_type: str,
        chargepoint_slug: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._chargepoint_slug = chargepoint_slug

        # Get charger data
        charger_data = coordinator.data["status"]
        chargepoint_id = coordinator.config_entry.data["chargepoint_id"]
        evse_id = coordinator.config_entry.data["evse_id"]

        # Store user-friendly name from config/charger data
        self._charger_name = charger_data.get(
            "name", f"AMPECO Charger {chargepoint_id}"
        )

        # Create a unique ID for this sensor (used internally by HA)
        self._attr_unique_id = f"{chargepoint_id}_{evse_id}_{sensor_type}"

        # Set a custom entity ID for this sensor - this is what users will see as sensor.xyz
        self.entity_id = f"sensor.evse_{chargepoint_slug}_{sensor_type}"

        # Define a friendly display name
        sensor_type_name = sensor_type.replace("_", " ").title()
        self._attr_name = f"{self._charger_name} {sensor_type_name}"

        # It's important that device_info identifiers remain consistent
        # This is how services find the device when called with device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, evse_id)},
            name=self._charger_name,
            manufacturer="AMPECO",
            model=charger_data.get("evses", [{}])[0]
            .get("connectors", [{}])[0]
            .get("name", "Unknown"),
            sw_version=charger_data.get("firmware_version"),
            configuration_url=f"https://app.ampeco.global/chargers/{chargepoint_id}",
        )


class ChargerStatusSensor(EVChargerBaseSensor):
    """Sensor for charger status."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, SENSOR_TYPE_CHARGER_STATUS, chargepoint_slug)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data["status"].get("status")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        status_data = self.coordinator.data["status"]
        return {
            "max_current_a": status_data.get("max_current_a"),
            "allowed_max_power_kw": status_data.get("allowed_max_power_kw"),
            "firmware_version": status_data.get("firmware_version"),
            "plug_and_charge": status_data.get("plug_and_charge"),
            "is_rebooting": status_data.get("is_rebooting"),
            "smart_charging_enabled": status_data.get("smart_charging_enabled"),
            "allowed_min_current_a": status_data.get("allowed_min_current_a"),
            "allowed_solar_min_power_kw": status_data.get("allowed_solar_min_power_kw"),
        }


class ChargingSessionSensor(EVChargerBaseSensor):
    """Sensor for charging session."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, SENSOR_TYPE_CHARGING_SESSION, chargepoint_slug)
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        session_data = self.coordinator.data["session"]
        if not session_data:
            return 0

        # Get power and convert from W to kW if needed
        power = session_data.get("power", 0)
        # If power is very large, it's likely in W instead of kW
        if power > 1000:  # If power is more than 1000, assume it's in watts
            power = power / 1000
        return round(power, 2)  # Round to 2 decimal places

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        session_data = self.coordinator.data["session"]
        if not session_data:
            return {}

        return {
            "session_id": session_data.get("id"),
            "started_at": session_data.get("startedAt"),
            "duration": session_data.get("duration"),
            "energy": session_data.get("energy"),
            "status": session_data.get("status"),
            "charging_state": session_data.get("chargingState"),
            "amount": session_data.get("amount"),
            "evse_status": session_data.get("evseStatus"),
            "total_duration": session_data.get("totalDuration"),
            "total_amount": session_data.get("totalAmount"),
        }


class ChargingCurrentSensor(EVChargerBaseSensor):
    """Sensor for charging current."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charging_current", chargepoint_slug)
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data["status"].get("max_current_a")


class ChargingEnergySensor(EVChargerBaseSensor):
    """Sensor for charging energy."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charging_energy", chargepoint_slug)
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    @property
    def native_value(self):
        """Return the state of the sensor."""
        session_data = self.coordinator.data["session"]
        if not session_data:
            return 0

        # Get energy value
        energy = session_data.get("energy", 0)
        try:
            energy = float(energy)
        except (ValueError, TypeError):
            return 0

        # If energy is very large (more than 100), it's likely in Wh instead of kWh
        if energy > 100:
            energy = energy / 1000

        return round(energy, 2)  # Round to 2 decimal places


class ChargingDurationSensor(EVChargerBaseSensor):
    """Sensor for charging duration."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charging_duration", chargepoint_slug)
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self):
        """Return the state of the sensor."""
        session_data = self.coordinator.data["session"]
        if not session_data:
            return 0

        # Get duration value
        duration = session_data.get("duration", 0)
        try:
            duration = int(duration)
        except (ValueError, TypeError):
            return 0

        # The API returns duration in seconds, convert to minutes
        if duration > 0:
            duration = round(duration / 60)  # Convert seconds to minutes and round

        return duration


class PollingIntervalSensor(EVChargerBaseSensor):
    """Sensor for polling interval."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "polling_interval", chargepoint_slug)
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = True

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.update_interval.total_seconds()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "is_charging": self.coordinator.polling_strategy._is_charging,
            "retry_count": self.coordinator.polling_strategy._retry_count,
            "last_retry": self.coordinator.polling_strategy._last_retry,
        }


class EVSEStatusSensor(EVChargerBaseSensor):
    """Sensor for EVSE status."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "evse_status", chargepoint_slug)
        self._attr_icon = "mdi:ev-station"
        self._attr_entity_category = None  # This is important enough to show in main UI

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.data["status"].get("evses"):
            return "unavailable"
        return self.coordinator.data["status"]["evses"][0]["status"]


class MaxCurrentSensor(EVChargerBaseSensor):
    """Sensor for maximum allowed current."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "max_current", chargepoint_slug)
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return float(self.coordinator.data["status"].get("max_current_a", 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        status = self.coordinator.data["status"]
        return {
            "allowed_min_current": status.get("allowed_min_current_a"),
            "allowed_max_current": status.get("allowed_max_current_a"),
        }


class LastMonthStatsSensor(EVChargerBaseSensor):
    """Sensor for last month's statistics."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "last_month_energy", chargepoint_slug)
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return float(self.coordinator.data["status"].get("last_month_energy_kwh", 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        status = self.coordinator.data["status"]
        return {
            "electricity_cost": status.get("last_month_electricity_cost", 0),
            "tax_name": status.get("electricity_cost_tax_name"),
            "tax_percent": status.get("electricity_cost_tax_percent"),
        }


class SessionIDSensor(EVChargerBaseSensor):
    """Sensor for active session ID."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, chargepoint_slug: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "session_id", chargepoint_slug)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False  # Hidden by default
        self._attr_icon = "mdi:identifier"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        session_data = self.coordinator.data["session"]
        return session_data.get("id") if session_data else None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        session_data = self.coordinator.data["session"]
        if not session_data:
            return {}

        return {
            "started_at": session_data.get("startedAt"),
            "status": session_data.get("status"),
            "evse_status": session_data.get("evseStatus"),
            "charging_state": session_data.get("chargingState"),
        }
