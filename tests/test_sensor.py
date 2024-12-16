"""Test AMPECO EV Charger sensor platform."""
from unittest.mock import patch
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ev_charger.const import DOMAIN
from custom_components.ev_charger.sensor import (
    ChargerStatusSensor,
    ChargingSessionSensor,
    ChargingCurrentSensor,
    ChargingEnergySensor,
    ChargingDurationSensor,
)

async def test_sensors(hass, mock_config_entry_data, mock_charger_status_response, mock_active_session_response):
    """Test sensor creation and values."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        entry_id="test",
    )

    with patch(
        "custom_components.ev_charger.coordinator.EVChargerDataUpdateCoordinator._async_update_data",
        return_value={
            "status": mock_charger_status_response["data"],
            "session": mock_active_session_response["session"],
        },
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Test status sensor
        state = hass.states.get("sensor.test_charger_status")
        assert state is not None
        assert state.state == "available"

        # Test session sensor
        state = hass.states.get("sensor.test_charger_charging_session")
        assert state is not None
        assert state.state == "11.0"

        # Test current sensor
        state = hass.states.get("sensor.test_charger_charging_current")
        assert state is not None
        assert state.state == "16"

        # Test energy sensor
        state = hass.states.get("sensor.test_charger_charging_energy")
        assert state is not None
        assert state.state == "10.5"

        # Test duration sensor
        state = hass.states.get("sensor.test_charger_charging_duration")
        assert state is not None
        assert state.state == "30" 