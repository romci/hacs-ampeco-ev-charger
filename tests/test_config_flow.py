"""Test AMPECO EV Charger config flow."""
from unittest.mock import patch
import pytest
from homeassistant import config_entries, data_entry_flow
from custom_components.ev_charger.const import DOMAIN

async def test_form(hass, mock_charger_status_response):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.ev_charger.config_flow.validate_input",
        return_value={"title": "AMPECO EV Charger Test", "evse_id": "test_evse_id"},
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "api_host": "https://app.ampeco.global",
                "chargepoint_id": "test_chargepoint_id",
                "auth_token": "test_token",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "AMPECO EV Charger Test"
    assert result2["data"]["chargepoint_id"] == "test_chargepoint_id"
    assert result2["data"]["auth_token"] == "test_token"
    assert result2["data"]["evse_id"] == "test_evse_id"

async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ev_charger.config_flow.validate_input",
        side_effect=InvalidAuth,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "api_host": "https://app.ampeco.global",
                "chargepoint_id": "test_chargepoint_id",
                "auth_token": "test_token",
            },
        )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["errors"]["base"] == "invalid_auth" 