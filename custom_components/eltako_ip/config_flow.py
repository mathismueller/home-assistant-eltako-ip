"""Config flow for Eltako Series 62/64 IP integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:
    from aioeltako_ip import (
        AuthenticationError,
        EltakoClient,
        EltakoConnectionError,
        EltakoError,
    )
except ImportError:
    import sys
    from pathlib import Path
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from aioeltako_ip import (  # type: ignore[no-redef]
        AuthenticationError,
        EltakoClient,
        EltakoConnectionError,
        EltakoError,
    )

from .const import (
    CONF_HOST,
    CONF_POP,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    REPEATER_LEVEL_OFF,
    REPEATER_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_POP): str,
    }
)


class EltakoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eltako Series 62/64 IP."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            pop = user_input[CONF_POP]

            session = async_get_clientsession(self.hass, verify_ssl=False)
            client = EltakoClient(host=host, port=port, pop=pop, session=session)
            try:
                await client.login()
                system = await client.get_system()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except EltakoConnectionError:
                errors["base"] = "cannot_connect"
            except EltakoError:
                errors["base"] = "unknown"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(system.serial_number)
                self._abort_if_unique_id_configured()

                title = f"{system.product_name} ({system.serial_number})"
                return self.async_create_entry(title=title, data=user_input)
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            pop = user_input[CONF_POP]

            session = async_get_clientsession(self.hass, verify_ssl=False)
            client = EltakoClient(host=host, port=port, pop=pop, session=session)
            try:
                await client.login()
                system = await client.get_system()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except EltakoConnectionError:
                errors["base"] = "cannot_connect"
            except EltakoError:
                errors["base"] = "unknown"
            except Exception:
                _LOGGER.exception("Unexpected exception during reconfigure")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(system.serial_number)
                self._abort_if_unique_id_mismatch(reason="another_device")

                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates=user_input,
                )
            finally:
                await client.close()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=reconfigure_entry.data.get(CONF_HOST)
                ): str,
                vol.Optional(
                    CONF_PORT,
                    default=reconfigure_entry.data.get(CONF_PORT, DEFAULT_PORT),
                ): cv.port,
                vol.Required(
                    CONF_POP, default=reconfigure_entry.data.get(CONF_POP)
                ): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get options flow handler."""
        return EltakoOptionsFlowHandler()


class EltakoOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Eltako Series 62/64 IP."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): cv.positive_int,
                vol.Optional(
                    "repeater_level",
                    default=options.get("repeater_level", REPEATER_LEVEL_OFF),
                ): vol.In(REPEATER_OPTIONS),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
