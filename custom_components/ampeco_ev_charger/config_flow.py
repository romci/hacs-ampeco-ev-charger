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
from .const import (
    DOMAIN,
    CONF_AUTH_TOKEN,
    CONF_CHARGEPOINT_ID,
    CONF_EVSE_ID,
    CONF_API_HOST,
    DEFAULT_API_HOST,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_HOST, default=DEFAULT_API_HOST): str,
        vol.Required(CONF_AUTH_TOKEN): str,
    }
)


async def validate_auth(
    hass: HomeAssistant, host: str, token: str
) -> list[dict[str, Any]]:
    """Validate the user input allows us to connect and fetch chargepoints."""
    session = async_get_clientsession(hass)
    client = EVChargerApiClient(
        host=host,
        chargepoint_id="",  # Not needed for initial validation
        auth_token=token,
        session=session,
    )

    try:
        _LOGGER.debug("Attempting to get chargepoints list")
        response = await client._make_request(
            "GET", "app/personal/charge-points", headers=client._headers
        )
        _LOGGER.debug("Received chargepoints: %s", response)

        if not response or "data" not in response:
            raise InvalidAuth

        chargepoints = response["data"]
        if not chargepoints:
            raise NoChargepointsFound

        return chargepoints

    except aiohttp.ClientResponseError as err:
        _LOGGER.error("HTTP error during validation: %s", err)
        if err.status == 401:
            raise InvalidAuth from err
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.exception("Unexpected error during validation: %s", err)
        raise


class EVChargerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EV Charger."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._host: str | None = None
        self._token: str | None = None
        self._chargepoints: list[dict[str, Any]] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                chargepoints = await validate_auth(
                    self.hass,
                    user_input[CONF_API_HOST],
                    user_input[CONF_AUTH_TOKEN],
                )

                self._host = user_input[CONF_API_HOST]
                self._token = user_input[CONF_AUTH_TOKEN]
                self._chargepoints = chargepoints

                return await self.async_step_select_chargepoint()

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except NoChargepointsFound:
                errors["base"] = "no_chargepoints"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_chargepoint(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the chargepoint selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            chargepoint = next(
                (
                    cp
                    for cp in self._chargepoints
                    if cp["id"] == user_input[CONF_CHARGEPOINT_ID]
                ),
                None,
            )
            if chargepoint:
                evse = chargepoint["evses"][0] if chargepoint.get("evses") else None
                if evse:
                    return self.async_create_entry(
                        title=f"AMPECO EV Charger {chargepoint['name']}",
                        data={
                            CONF_API_HOST: self._host,
                            CONF_AUTH_TOKEN: self._token,
                            CONF_CHARGEPOINT_ID: chargepoint["id"],
                            CONF_EVSE_ID: evse["id"],
                        },
                    )

        chargepoint_options = {
            cp["id"]: f"{cp['name']} ({cp['id']})" for cp in self._chargepoints
        }

        return self.async_show_form(
            step_id="select_chargepoint",
            data_schema=vol.Schema(
                {vol.Required(CONF_CHARGEPOINT_ID): vol.In(chargepoint_options)}
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoChargepointsFound(HomeAssistantError):
    """Error to indicate no chargepoints were found."""
