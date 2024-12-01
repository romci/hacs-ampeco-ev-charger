"""Config flow for EV Charger integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import EVChargerApiClient
from .const import CONF_AUTH_TOKEN, CONF_CHARGEPOINT_ID, CONF_EVSE_ID, DOMAIN, DEFAULT_API_HOST

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_HOST, default=DEFAULT_API_HOST): str,
        vol.Required(CONF_CHARGEPOINT_ID): str,
        vol.Required(CONF_AUTH_TOKEN): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    
    client = EVChargerApiClient(
        host="https://api.example.com",  # Replace with actual API host
        chargepoint_id=data[CONF_CHARGEPOINT_ID],
        auth_token=data[CONF_AUTH_TOKEN],
        session=session,
    )

    try:
        status = await client.get_charger_status()
        if not status:
            raise InvalidAuth
            
        # Get the first EVSE ID from the charger status
        evses = status.get("evses", [])
        if not evses:
            raise CannotConnect("No EVSE found for this charger")
            
        evse_id = evses[0].get("id")
        if not evse_id:
            raise CannotConnect("Invalid EVSE configuration")

        return {
            "title": f"AMPECO EV Charger {data[CONF_CHARGEPOINT_ID]}",
            "evse_id": evse_id,
        }
            
    except aiohttp.ClientResponseError as err:
        if err.status == 401:
            raise InvalidAuth from err
        raise CannotConnect from err
    except aiohttp.ClientError as err:
        raise CannotConnect from err

class EVChargerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EV Charger."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        **user_input,
                        CONF_EVSE_ID: info["evse_id"],
                    }
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
  