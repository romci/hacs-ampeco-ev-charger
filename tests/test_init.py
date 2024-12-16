"""Test AMPECO EV Charger setup."""
from homeassistant.exceptions import ConfigEntryNotReady
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ev_charger import (
    async_setup_entry,
    async_unload_entry,
)
from custom_components.ev_charger.const import DOMAIN

async def test_setup_entry(hass, mock_config_entry_data, mock_charger_status_response):
    """Test setup entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        entry_id="test",
    )

    with patch(
        "custom_components.ev_charger.coordinator.EVChargerDataUpdateCoordinator._async_update_data",
        return_value={
            "status": mock_charger_status_response["data"],
            "session": {},
        },
    ):
        assert await async_setup_entry(hass, config_entry)
        await hass.async_block_till_done()
        assert DOMAIN in hass.data
        assert config_entry.entry_id in hass.data[DOMAIN]

async def test_unload_entry(hass, mock_config_entry_data):
    """Test unloading entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        entry_id="test",
    )

    with patch(
        "custom_components.ev_charger.coordinator.EVChargerDataUpdateCoordinator._async_update_data",
        return_value={"status": {}, "session": {}},
    ):
        assert await async_setup_entry(hass, config_entry)
        await hass.async_block_till_done()
        assert await async_unload_entry(hass, config_entry)
        assert config_entry.entry_id not in hass.data[DOMAIN] 