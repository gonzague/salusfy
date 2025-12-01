"""Config flow for Salus iT500 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .pyit500.auth import Auth
from .pyit500.pyit500 import PyIt500

_LOGGER = logging.getLogger(__name__)


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class NoDevices(Exception):
    """Error to indicate no devices found."""


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    auth = Auth(session, data[CONF_USERNAME], data[CONF_PASSWORD])

    try:
        await auth.refresh_token()
    except Exception as err:
        _LOGGER.error("Failed to authenticate: %s", err)
        raise InvalidAuth from err

    api = PyIt500(auth)

    try:
        device_list = await api.async_get_device_list()
    except Exception as err:
        _LOGGER.error("Failed to get device list: %s", err)
        raise CannotConnect from err

    if not device_list:
        raise NoDevices

    # Get first device info for title
    try:
        device = await api.async_get_device(device_list[0].device_id)
        title = device.description or f"Salus iT500 ({device_list[0].name})"
    except Exception:
        title = f"Salus iT500 ({device_list[0].name})"

    return {
        "title": title,
        "device_count": len(device_list),
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Salus iT500."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except NoDevices:
                errors["base"] = "no_devices"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )
