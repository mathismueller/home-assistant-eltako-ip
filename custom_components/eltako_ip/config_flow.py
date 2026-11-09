"""Config flow for Eltako Series 62/64 IP integration."""

from __future__ import annotations

import ipaddress
import logging
from pathlib import Path
import sys
from typing import Any, Optional

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
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

try:
    from aioeltako_ip import (
        AuthenticationError,
        EltakoClient,
        EltakoConnectionError,
        EltakoError,
        EnOceanScanResultItem,
        format_eur_id_hex,
        parse_eur_id,
    )
    from aioeltako_ip.client import normalize_host
except ImportError:
    for _candidate in (
        Path(__file__).resolve().parent.parent.parent / "src",
        Path(__file__).resolve().parent,
    ):
        if (_candidate / "aioeltako_ip").is_dir() and str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
            break
    from aioeltako_ip import (  # type: ignore[no-redef]
        AuthenticationError,
        EltakoClient,
        EltakoConnectionError,
        EltakoError,
        EnOceanScanResultItem,
        format_eur_id_hex,
        parse_eur_id,
    )
    from aioeltako_ip.client import normalize_host  # type: ignore[no-redef]

from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_POP,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOCAL_WIRED_INPUT_PRODUCTS,
    PRODUCT_E2SR64NP_IPM,
    PRODUCT_ESB62NP_IP,
    PRODUCT_ESB64NP_IPM,
    PRODUCT_ESR62NP_IP,
    PRODUCT_ESR62PF_IP,
    PRODUCT_ESR64NP_IPM,
    PRODUCT_ESR64PF_IPM,
    PRODUCT_EUD62NPN_IP,
    PRODUCT_EUD62NPN_IPM,
    PRODUCT_EUD64NPN_IPM,
    PRODUCT_FSB61,
    PRODUCT_FSR61,
    PRODUCT_FTK_CONTACT,
    PRODUCT_FUD61,
    PRODUCT_NAMES_FALLBACK,
    REPEATER_LEVEL_OFF,
    REPEATER_OPTIONS,
)
from .coordinator import EltakoDataUpdateCoordinator

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

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: Optional[str] = None
        self._discovered_port: int = DEFAULT_PORT
        self._discovered_name: str = "Eltako IP"
        self._discovered_serial: Optional[str] = None
        self._discovered_model: Optional[str] = None

    def _build_discovery_host_updates(
        self,
        serial: str,
        discovered_ip: str,
        port: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """Build host/port updates for an existing entry without overwriting user-configured hostnames."""
        entries = (
            self.hass.config_entries.async_entries(DOMAIN)
            if self.hass and hasattr(self.hass, "config_entries")
            else []
        )
        existing = next(
            (e for e in entries if getattr(e, "unique_id", None) == serial),
            None,
        )
        if existing is not None:
            current_host = str(existing.data.get(CONF_HOST, "")).strip()
            if current_host:
                try:
                    ipaddress.ip_address(current_host)
                except ValueError:
                    # Existing entry uses a hostname (e.g. eltako-xxxx.local); preserve it!
                    return {CONF_PORT: port} if port is not None else None

        updates: dict[str, Any] = {CONF_HOST: discovered_ip}
        if port is not None:
            updates[CONF_PORT] = port
        return updates

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle Zeroconf (_eltako._tcp.local.) discovery."""
        host = normalize_host(str(discovery_info.host))
        port = int(discovery_info.port or DEFAULT_PORT)
        props = discovery_info.properties or {}

        serial = str(props.get("sn") or "").strip()
        if not serial and discovery_info.hostname:
            hostname_prefix = discovery_info.hostname.split(".")[0]
            if hostname_prefix.lower().startswith("eltako-"):
                serial = hostname_prefix[7:]

        product_name = str(
            props.get("pn") or props.get("md") or "Eltako Series 62/64 IP"
        ).strip()
        model = str(props.get("md") or product_name).strip()

        if serial:
            await self.async_set_unique_id(serial)
            self._abort_if_unique_id_configured(
                updates=self._build_discovery_host_updates(serial, host, port)
            )
        else:
            self._async_abort_entries_match({CONF_HOST: host})

        self._discovered_host = host
        self._discovered_port = port
        self._discovered_serial = serial or None
        self._discovered_name = product_name
        self._discovered_model = model

        label = f"{product_name} ({serial})" if serial else f"{product_name} ({host})"
        self.context["title_placeholders"] = {
            "name": label,
            "host": host,
        }
        return await self.async_step_discovery_confirm()

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP (eltako-* / MAC OUI C8:F5:D6) discovery."""
        host = normalize_host(str(discovery_info.ip))
        hostname = str(discovery_info.hostname or "").strip()
        serial = ""
        if hostname.lower().startswith("eltako-"):
            serial = hostname.split(".")[0][7:]

        if serial:
            await self.async_set_unique_id(serial)
            self._abort_if_unique_id_configured(
                updates=self._build_discovery_host_updates(serial, host)
            )
        else:
            self._async_abort_entries_match({CONF_HOST: host})

        # Probe unauthenticated /.well-known/eltako/devices to confirm it is an Eltako IP device
        session = async_get_clientsession(self.hass, verify_ssl=False)
        client = EltakoClient(host=host, port=DEFAULT_PORT, session=session)
        try:
            wk = await client.get_well_known()
            if not wk:
                return self.async_abort(reason="cannot_connect")
        except EltakoError:
            return self.async_abort(reason="cannot_connect")
        finally:
            await client.close()

        self._discovered_host = host
        self._discovered_port = DEFAULT_PORT
        self._discovered_serial = serial or None
        self._discovered_name = "Eltako Series 62/64 IP"

        label = (
            f"Eltako IP ({serial})" if serial else f"Eltako IP ({host})"
        )
        self.context["title_placeholders"] = {
            "name": label,
            "host": host,
        }
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup of a discovered Eltako IP device by entering its PoP code."""
        errors: dict[str, str] = {}
        host = self._discovered_host or ""
        port = self._discovered_port

        if user_input is not None:
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
                _LOGGER.exception("Unexpected exception during discovery setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    system.serial_number, raise_on_progress=False
                )
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: host, CONF_PORT: port}
                )
                title = f"{system.product_name} ({system.serial_number})"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_POP: pop,
                        CONF_API_KEY: client.api_key or "",
                    },
                )
            finally:
                await client.close()

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema({vol.Required(CONF_POP): str}),
            description_placeholders={
                "name": self._discovered_name,
                "host": host,
                "serial": self._discovered_serial or "unknown",
            },
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = normalize_host(user_input[CONF_HOST])
            user_input[CONF_HOST] = host
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
                user_input[CONF_API_KEY] = client.api_key or ""
                return self.async_create_entry(title=title, data=user_input)
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication when PoP or API key is rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication with updated Proof of Possession (PoP)."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            host = reauth_entry.data[CONF_HOST]
            port = reauth_entry.data.get(CONF_PORT, DEFAULT_PORT)
            pop = user_input[CONF_POP]

            session = async_get_clientsession(self.hass, verify_ssl=False)
            client = EltakoClient(host=host, port=port, pop=pop, session=session)
            try:
                await client.login()
                await client.get_system()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except EltakoConnectionError:
                errors["base"] = "cannot_connect"
            except EltakoError:
                errors["base"] = "unknown"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_POP: pop, CONF_API_KEY: ""},
                )
            finally:
                await client.close()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_POP, default=reauth_entry.data.get(CONF_POP, "")
                ): str,
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            host = normalize_host(user_input[CONF_HOST])
            user_input[CONF_HOST] = host
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
    """Handle options flow and interactive EnOcean pairing wizard for Eltako IP."""

    def __init__(self) -> None:
        """Initialize options flow state."""
        self._pending_options: dict[str, Any] = {}
        self._scan_results: list[EnOceanScanResultItem] = []

    def _get_coordinator(self) -> Optional[EltakoDataUpdateCoordinator]:
        if hasattr(self.config_entry, "runtime_data") and self.config_entry.runtime_data:
            return self.config_entry.runtime_data
        return self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage general options or launch interactive EnOcean pairing wizards."""
        if user_input is not None:
            action = user_input.pop("action", "save_settings")
            self._pending_options = {
                CONF_SCAN_INTERVAL: user_input.get(
                    CONF_SCAN_INTERVAL,
                    self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ),
                "repeater_level": user_input.get(
                    "repeater_level",
                    self.config_entry.options.get("repeater_level", REPEATER_LEVEL_OFF),
                ),
            }

            coord = self._get_coordinator()
            if coord and "repeater_level" in user_input:
                try:
                    await coord.client.set_enocean_repeater(
                        repeater_level=self._pending_options["repeater_level"]
                    )
                except EltakoError:
                    _LOGGER.debug("Could not apply repeater_level in options flow")

            if action == "pair_enocean":
                if coord:
                    try:
                        await coord.client.start_enocean_scan()
                    except EltakoError:
                        _LOGGER.debug("Could not start EnOcean scan automatically")
                return await self.async_step_pair_enocean()

            if action == "legacy_pair_enocean":
                return await self.async_step_legacy_pair_enocean()

            return self.async_create_entry(title="", data=self._pending_options)

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
                vol.Optional("action", default="save_settings"): vol.In(
                    {
                        "save_settings": "Save Settings",
                        "pair_enocean": "Pair EnOcean Sensor (Interactive Scan Wizard)",
                        "legacy_pair_enocean": "Bidirectional Legacy Actuator Pairing (FSR61/FUD61/FSB61)",
                    }
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_pair_enocean(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Interactive EnOcean sensor pairing wizard (supports radio scan + hex sticker ID entry)."""
        errors: dict[str, str] = {}
        coord = self._get_coordinator()

        if user_input is not None:
            eur_id_raw = str(user_input.get("eur_id") or "").strip()
            product_guid = user_input.get("product_guid", PRODUCT_FTK_CONTACT)
            display_name = user_input.get("display_name", "").strip()

            if user_input.get("rescan"):
                if coord:
                    try:
                        # First check if telegrams were captured during the active scan window
                        scan_res = await coord.client.get_enocean_scan_results()
                        self._scan_results = scan_res
                        if not scan_res:
                            # Restart 60s scan if nothing was captured yet
                            await coord.client.start_enocean_scan()
                    except EltakoError:
                        errors["base"] = "cannot_connect"
            elif not eur_id_raw:
                # If submitted empty, check if a sensor was discovered in the scan
                if coord:
                    try:
                        self._scan_results = await coord.client.get_enocean_scan_results()
                    except EltakoError:
                        pass
                if not self._scan_results:
                    errors["base"] = "no_device_selected"
            elif coord:
                try:
                    parsed_eur_id = parse_eur_id(eur_id_raw, prefer_hex=True)
                except ValueError:
                    errors["base"] = "invalid_eur_id"
                else:
                    try:
                        resp = await coord.client.pair_enocean_device(
                            eur_id=parsed_eur_id,
                            product_guid=str(product_guid),
                        )
                        device_guid = resp.get("deviceGuid")
                        if display_name and device_guid:
                            await coord.client.rename_device(device_guid, display_name)
                        await coord.async_request_refresh()
                        self.hass.async_create_task(
                            self.hass.config_entries.async_reload(
                                self.config_entry.entry_id
                            )
                        )
                        return self.async_create_entry(
                            title="",
                            data=self._pending_options or dict(self.config_entry.options),
                        )
                    except EltakoError:
                        errors["base"] = "pairing_failed"

        # Exclude local IP actuators and wired inputs from EnOcean profile selector
        local_non_enocean_guids = {
            PRODUCT_ESR64PF_IPM,
            PRODUCT_ESR64NP_IPM,
            PRODUCT_ESR62NP_IP,
            PRODUCT_ESR62PF_IP,
            PRODUCT_E2SR64NP_IPM,
            PRODUCT_EUD64NPN_IPM,
            PRODUCT_EUD62NPN_IP,
            PRODUCT_EUD62NPN_IPM,
            PRODUCT_ESB64NP_IPM,
            PRODUCT_ESB62NP_IP,
            *LOCAL_WIRED_INPUT_PRODUCTS,
        }

        product_options: dict[str, str] = {
            PRODUCT_FTK_CONTACT: "FTK — Solar Window/Door Contact Sensor",
            "92ec3705-e209-4117-9efb-e0cfb2d116bb": "FTKB — Battery Window/Door Contact Sensor",
            "541d4e82-5904-4a39-abd8-c5f57f9bbdee": "FTKE — Window/Door Contact Sensor",
            "07f73245-b035-40ad-a403-f8581f067ef6": "FFG7B — Window Handle Sensor",
            "067272d3-60f8-4618-bc2f-0145e99b1f0b": "F2T55E / FT55 — Wireless Rocker Pushbutton",
            PRODUCT_FSR61: PRODUCT_NAMES_FALLBACK[PRODUCT_FSR61],
            PRODUCT_FUD61: PRODUCT_NAMES_FALLBACK[PRODUCT_FUD61],
            PRODUCT_FSB61: PRODUCT_NAMES_FALLBACK[PRODUCT_FSB61],
        }

        discovered_select_options: list[SelectOptionDict] = []
        default_eur = ""
        default_product = (
            user_input.get("product_guid", PRODUCT_FTK_CONTACT)
            if user_input
            else PRODUCT_FTK_CONTACT
        )

        if coord:
            for p_guid, p_spec in coord.data.products.items():
                if (
                    p_spec.name
                    and p_guid not in local_non_enocean_guids
                    and p_guid not in product_options
                ):
                    product_options[p_guid] = p_spec.name

            try:
                scan_res = await coord.client.get_enocean_scan_results()
                self._scan_results = scan_res
                for item in scan_res:
                    hex_id = format_eur_id_hex(item.eur_id)
                    prod_label = (
                        coord.data.get_product_name(item.product_guid, "EnOcean Device")
                        if item.product_guid
                        else "EnOcean Device"
                    )
                    rssi_str = (
                        f"{item.signal_strength} dBm"
                        if item.signal_strength is not None
                        else "discovered"
                    )
                    discovered_select_options.append(
                        SelectOptionDict(
                            value=hex_id,
                            label=f"{prod_label} — ID {hex_id} ({rssi_str})",
                        )
                    )
                if scan_res:
                    default_eur = format_eur_id_hex(scan_res[0].eur_id)
                    if (
                        scan_res[0].product_guid
                        and scan_res[0].product_guid in product_options
                        and (not user_input or not user_input.get("product_guid"))
                    ):
                        default_product = scan_res[0].product_guid
            except EltakoError:
                _LOGGER.debug("Could not fetch EnOcean scan results")

        eur_selector = SelectSelector(
            SelectSelectorConfig(
                options=discovered_select_options,
                custom_value=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )

        schema = vol.Schema(
            {
                vol.Optional("eur_id", default=default_eur): eur_selector,
                vol.Optional(
                    "product_guid", default=default_product
                ): vol.In(product_options),
                vol.Optional("display_name", default=""): str,
                vol.Optional("rescan", default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="pair_enocean",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_legacy_pair_enocean(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Interactive wizard for bidirectional legacy EnOcean actuators (FSR61, FUD61, FSB61)."""
        errors: dict[str, str] = {}
        coord = self._get_coordinator()

        if user_input is not None and coord:
            step_action = user_input.get("step_action", "start")
            product_guid = user_input.get("product_guid", PRODUCT_FSR61)
            try:
                if step_action == "start":
                    await coord.client.start_enocean_legacy_pair(
                        {"productGuid": product_guid}
                    )
                elif step_action == "continue":
                    await coord.client.continue_enocean_legacy_pair(
                        {"productGuid": product_guid}
                    )
                    await coord.async_request_refresh()
                    return self.async_create_entry(
                        title="",
                        data=self._pending_options or dict(self.config_entry.options),
                    )
                elif step_action == "finish":
                    await coord.async_request_refresh()
                    return self.async_create_entry(
                        title="",
                        data=self._pending_options or dict(self.config_entry.options),
                    )
            except EltakoError:
                errors["base"] = "pairing_failed"

        legacy_products = {
            PRODUCT_FSR61: "FSR61 Relay Actuator",
            PRODUCT_FUD61: "FUD61 Dimmer Actuator",
            PRODUCT_FSB61: "FSB61 Shading/Blind Actuator",
            "23b9e65d-ec47-400b-982e-4d04ef5c33f4": "FHK14 Heating/Cooling Actuator",
        }

        schema = vol.Schema(
            {
                vol.Required("product_guid", default=PRODUCT_FSR61): vol.In(
                    legacy_products
                ),
                vol.Required("step_action", default="start"): vol.In(
                    {
                        "start": "1. Start Teach-In Telegram",
                        "continue": "2. Confirm Actuator Response & Complete",
                        "finish": "Close Wizard",
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="legacy_pair_enocean",
            data_schema=schema,
            errors=errors,
        )
