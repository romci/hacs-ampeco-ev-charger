"""Global fixtures for AMPECO EV Charger integration tests."""
from unittest.mock import patch
import pytest

from homeassistant.const import CONF_HOST
from custom_components.ev_charger.const import (
    DOMAIN,
    CONF_CHARGEPOINT_ID,
    CONF_AUTH_TOKEN,
    CONF_EVSE_ID,
    CONF_API_HOST,
)

@pytest.fixture
def mock_setup_entry() -> None:
    """Override async_setup_entry."""
    with patch(
        "custom_components.ev_charger.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry

@pytest.fixture
def mock_config_entry_data():
    """Create mock config entry data."""
    return {
        CONF_API_HOST: "https://app.ampeco.global",
        CONF_CHARGEPOINT_ID: "test_chargepoint_id",
        CONF_AUTH_TOKEN: "test_auth_token",
        CONF_EVSE_ID: "test_evse_id",
    }

@pytest.fixture
def mock_charger_status_response():
    """Create mock charger status response."""
    return {
        "data": {
            "id": "test_chargepoint_id",
            "name": "Test Charger",
            "status": "available",
            "max_current_a": 16,
            "allowed_max_power_kw": "11.1",
            "firmware_version": "1.0.0",
            "plug_and_charge": False,
            "is_rebooting": False,
            "evses": [
                {
                    "id": "test_evse_id",
                    "maxPower": 11000,
                    "identifier": "1234",
                    "currentType": "ac",
                    "status": "available",
                    "connectors": [
                        {
                            "name": "Type 2",
                            "icon": "type2",
                            "format": "cable",
                            "status": "available"
                        }
                    ]
                }
            ]
        }
    }

@pytest.fixture
def mock_active_session_response():
    """Create mock active session response."""
    return {
        "session": {
            "id": "test_session_id",
            "startedAt": "2024-03-14T12:00:00Z",
            "duration": 30,
            "energy": 10.5,
            "power": 11.0,
            "status": "active",
            "chargingState": "charging",
            "evseId": "test_evse_id"
        }
    } 