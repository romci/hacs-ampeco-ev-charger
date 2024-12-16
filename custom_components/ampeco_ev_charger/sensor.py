"""Sensor platform for EV Charger integration."""

from __future__ import annotations

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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the EV Charger sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = [
        ChargerStatusSensor(coordinator),
        ChargingSessionSensor(coordinator),
        ChargingCurrentSensor(coordinator),
        ChargingEnergySensor(coordinator),
        ChargingDurationSensor(coordinator),
        PollingIntervalSensor(coordinator),
        EVSEStatusSensor(coordinator),
        MaxCurrentSensor(coordinator),
        LastMonthStatsSensor(coordinator),
    ]

    async_add_entities(sensors)


class EVChargerBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for EV Charger sensors."""

    def __init__(
        self, coordinator: EVChargerDataUpdateCoordinator, sensor_type: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type

        # Get charger data
        charger_data = coordinator.data["status"]
        chargepoint_id = coordinator.config_entry.data["chargepoint_id"]
        evse_id = coordinator.config_entry.data["evse_id"]

        self._attr_unique_id = f"{chargepoint_id}_{evse_id}_{sensor_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, evse_id)},
            name=charger_data.get("name", f"AMPECO EV Charger {chargepoint_id}"),
            manufacturer="AMPECO",
            model=charger_data.get("evses", [{}])[0]
            .get("connectors", [{}])[0]
            .get("name", "Unknown"),
            sw_version=charger_data.get("firmware_version"),
            configuration_url=f"https://app.ampeco.global/chargers/{chargepoint_id}",  # Updated URL
        )


class ChargerStatusSensor(EVChargerBaseSensor):
    """Sensor for charger status."""

    def __init__(self, coordinator: EVChargerDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, SENSOR_TYPE_CHARGER_STATUS)
        self._attr_name = "Status"

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

    def __init__(self, coordinator: EVChargerDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, SENSOR_TYPE_CHARGING_SESSION)
        self._attr_name = "Charging Session"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "kW"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        session_data = self.coordinator.data["session"]
        return session_data.get("power", 0) if session_data else 0

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

    def __init__(self, coordinator: EVChargerDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charging_current")
        self._attr_name = "Charging Current"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data["status"].get("max_current_a")


class ChargingEnergySensor(EVChargerBaseSensor):
    """Sensor for charging energy."""

    def __init__(self, coordinator: EVChargerDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charging_energy")
        self._attr_name = "Charging Energy"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    @property
    def native_value(self):
        """Return the state of the sensor."""
        session_data = self.coordinator.data["session"]
        return float(session_data.get("energy", 0)) if session_data else 0


class ChargingDurationSensor(EVChargerBaseSensor):
    """Sensor for charging duration."""

    def __init__(self, coordinator: EVChargerDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charging_duration")
        self._attr_name = "Charging Duration"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self):
        """Return the state of the sensor."""
        session_data = self.coordinator.data["session"]
        return session_data.get("duration", 0) if session_data else 0


class PollingIntervalSensor(EVChargerBaseSensor):
    """Sensor for polling interval."""

    def __init__(self, coordinator: EVChargerDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "polling_interval")
        self._attr_name = "Polling Interval"
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

    def __init__(self, coordinator: EVChargerDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "evse_status")
        self._attr_name = "EVSE Status"
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

    def __init__(self, coordinator: EVChargerDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "max_current")
        self._attr_name = "Maximum Current"
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

    def __init__(self, coordinator: EVChargerDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "last_month_energy")
        self._attr_name = "Last Month Energy"
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
