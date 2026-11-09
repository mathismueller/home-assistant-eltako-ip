"""Standalone dev server for the Eltako on-device automation studio.

Stdlib only. Serves studio/ static files and a thin JSON bridge that mirrors
the future Home Assistant WebSocket API shape:

  GET    /api/status               -> {mode, host, rule_count}
  GET    /api/gateways             -> {gateways: [{name, host, port, ips, source}]}
  POST   /api/mode                 -> {mode: "live", host?, port?, pop?} | {mode: "mock"}
  GET    /api/automations          -> list[automation raw dict]
  POST   /api/automations          -> create rule (body = configuration payload)
  PUT    /api/automations/{guid}   -> update rule
  DELETE /api/automations/{guid}   -> delete rule
  DELETE /api/automations          -> reset to factory defaults
  GET    /api/devices              -> list[device raw dict]
  GET    /api/enocean_devices      -> list[enocean device raw dict]
  GET    /api/products             -> list[product raw dict]
  POST   /api/validate             -> {ok, problems[]} for a draft rule payload
      (spec-based pre-write check, same code the client library uses)

Mock mode (default): reads tests/fixtures/local/*.json, CRUD happens in memory.
Live mode (--live): proxies to https://HOST:PORT/api/v0/... using POP login
from .env (ELTAKO_HOST / ELTAKO_PORT / ELTAKO_POP). Handles self-signed TLS
and the apiKey Authorization header so the browser never talks to the
gateway directly (avoids CORS + cert issues).

Usage:
  python3 studio/server.py                  # mock on :8099
  python3 studio/server.py --live           # live gateway from .env
  python3 studio/server.py --port 8099 --live --host 192.168.1.100

  Either mode can also be flipped at runtime with the gateway button in the
  header (GET /api/gateways for mDNS discovery, POST /api/mode to connect).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import ssl
import sys
import threading
import urllib.request
import urllib.error
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "local"
STUDIO_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(REPO_ROOT / "src"))
try:
    # Load stdlib-only modules by path: importing the package would pull in
    # aiohttp (client.py), which the dev server must not require.
    import importlib.util

    def _load_module(name: str):
        spec = importlib.util.spec_from_file_location(
            f"studio_{name}", REPO_ROOT / "src" / "aioeltako_ip" / f"{name}.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"studio_{name}"] = module
        spec.loader.exec_module(module)
        return module

    _models = _load_module("models")
    _automations = _load_module("automations")
    validate_rule = _automations.validate_rule
    AutomationRule = _models.AutomationRule
except (ImportError, AssertionError, AttributeError):  # pragma: no cover
    validate_rule = None  # type: ignore[assignment]
    AutomationRule = None  # type: ignore[assignment]


def load_dotenv() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def load_fixture(name: str, default: list | dict):
    path = FIXTURE_DIR / f"{name}.json"
    if not path.is_file():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError):
        return copy.deepcopy(default)


class GatewayProxy:
    """Minimal urllib-based proxy for live gateway access (stdlib only)."""

    def __init__(self, host: str, port: int, pop: str, api_key: str | None = None) -> None:
        self.base = f"https://{host}:{port}/api/v0"
        self.pop = pop
        self.api_key = api_key
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        # Firmware drops concurrent connections; serialize all access.
        self._lock = threading.Lock()

    def _call(self, method: str, path: str, body: dict | list | None = None):
        with self._lock:
            return self._call_locked(method, path, body)

    def _call_locked(self, method: str, path: str, body: dict | list | None = None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = self.api_key
        req = urllib.request.Request(
            f"{self.base}{path}", data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=15) as resp:
                text = resp.read().decode()
                return json.loads(text) if text.strip() else True
        except urllib.error.HTTPError as err:
            if err.code == 401 and self.pop:
                self.login()
                try:
                    if self.api_key:
                        persist_env_value("ELTAKO_API_KEY", self.api_key)
                except OSError:
                    pass
                headers["Authorization"] = self.api_key or ""
                req = urllib.request.Request(
                    f"{self.base}{path}", data=data, headers=headers, method=method
                )
                with urllib.request.urlopen(req, context=self.ctx, timeout=15) as resp:
                    text = resp.read().decode()
                    return json.loads(text) if text.strip() else True
            raise

    def login(self) -> None:
        payload = json.dumps({"user": "admin", "password": self.pop}).encode()
        req = urllib.request.Request(
            f"{self.base}/login",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, context=self.ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        self.api_key = data.get("apiKey")
        if not self.api_key:
            raise RuntimeError("Live login failed: no apiKey returned")


class StudioState:
    def __init__(self, live: GatewayProxy | None) -> None:
        self.live = live
        self.automations: list[dict] = []
        self.devices: list[dict] = []
        self.enocean_devices: list[dict] = []
        self.products: list[dict] = []
        self.load_mock()

    def load_mock(self) -> None:
        """(Re)load demo fixture data (used at startup and when leaving live)."""
        self.automations = load_fixture("automations", [])
        self.devices = load_fixture("devices", [])
        self.enocean_devices = load_fixture("enocean_devices", [])
        # products.json is {"products": [...]} on gateways; normalize to list
        raw_products = load_fixture("products", [])
        if isinstance(raw_products, dict):
            raw_products = raw_products.get("products", list(raw_products.values()))
        self.products = (
            list(raw_products) if isinstance(raw_products, list) else []
        )

    def set_live(self, live: GatewayProxy) -> None:
        """Switch to live gateway proxying (mock data stays cached, unused)."""
        self.live = live

    def set_mock(self) -> None:
        """Switch back to demo mode with fresh fixture data."""
        self.live = None
        self.load_mock()

    # -- device origins -------------------------------------------------
    def device_origins(self) -> tuple[set, set]:
        """Return (gateway_guids, enocean_guids) for origin pills.

        Gateway guids are linked in /services/actuator/devices (the
        gateway's own hardware configurations); EnOcean guids are paired
        external sensors from /services/enocean/devices.
        """
        if self.live:
            try:
                act = self.live._call("GET", "/services/actuator/devices")
            except Exception:
                act = []
            try:
                eo = self.live._call("GET", "/services/enocean/devices")
            except Exception:
                eo = []
        else:
            act = load_fixture("actuator_devices", [])
            eo = self.enocean_devices
        gw = {
            d.get("deviceGuid")
            for d in (act or [])
            if isinstance(d, dict) and d.get("deviceGuid")
        }
        ex = {
            d.get("deviceGuid")
            for d in (eo or [])
            if isinstance(d, dict) and d.get("deviceGuid")
        }
        return gw, ex

    def annotated_devices(self, items: list) -> list:
        """Copy device dicts with gateway/pairedEnOcean origin flags."""
        gw, ex = self.device_origins()
        out = []
        for dev in items if isinstance(items, list) else []:
            if not isinstance(dev, dict):
                continue
            guid = dev.get("deviceGuid", "")
            item = dict(dev)
            item["gateway"] = guid in gw
            item["pairedEnOcean"] = guid in ex
            out.append(item)
        return out

    def rename_device(self, guid: str, display_name: str) -> dict:
        """Rename a device (PUT /devices/{guid} with updated displayName)."""
        if self.live:
            cur = self.live._call("GET", f"/devices/{guid}")
            if not isinstance(cur, dict):
                raise KeyError(guid)
            cur["displayName"] = display_name
            self.live._call("PUT", f"/devices/{guid}", cur)
            return {"ok": True, "deviceGuid": guid, "displayName": display_name}
        for dev in self.devices:
            if isinstance(dev, dict) and dev.get("deviceGuid") == guid:
                dev["displayName"] = display_name
                return {"ok": True, "deviceGuid": guid, "displayName": display_name}
        raise KeyError(guid)

    # -- automations ------------------------------------------------------
    def list_automations(self):
        if self.live:
            data = self.live._call("GET", "/services/eltako/automations")
            return data if isinstance(data, list) else []
        return self.automations

    def create_automation(self, payload: dict):
        if self.live:
            return self.live._call("POST", "/services/eltako/automations", payload)
        item = copy.deepcopy(payload)
        cfg = item.setdefault("configuration", {})
        cfg.setdefault("automationGuid", str(uuid.uuid4()))
        item.setdefault("enabled", True)
        item.setdefault("operatingStatus", "success")
        item.setdefault("errors", [])
        self.automations.append(item)
        return item

    def update_automation(self, guid: str, payload: dict):
        if self.live:
            return self.live._call(
                "PUT", f"/services/eltako/automations/{guid}", payload
            )
        for i, item in enumerate(self.automations):
            if item.get("configuration", {}).get("automationGuid") == guid:
                self.automations[i] = copy.deepcopy(payload)
                return self.automations[i]
        raise KeyError(guid)

    def delete_automation(self, guid: str):
        if self.live:
            return self.live._call("DELETE", f"/services/eltako/automations/{guid}")
        before = len(self.automations)
        self.automations = [
            a for a in self.automations
            if a.get("configuration", {}).get("automationGuid") != guid
        ]
        if len(self.automations) == before:
            raise KeyError(guid)
        return True

    def reset_automations(self):
        if self.live:
            return self.live._call("DELETE", "/services/eltako/automations")
        # Mirror hardware: reset recreates the factory default automation
        # (spec: "the default factory settings automation is recreated with
        # a new automationGuid"), i.e. wired input -> relay impulse switch.
        self.automations = []
        default = self._factory_default()
        if default is not None:
            self.automations.append(default)
        return True

    def _factory_default(self) -> dict | None:
        input_guid = input_char = None
        for dev in self.devices:
            ids = [
                c.get("identifier")
                for c in dev.get("functions", [])
                if isinstance(c, dict)
            ]
            for candidate in ("input", "inputChannel1"):
                if candidate in ids:
                    input_guid = dev["deviceGuid"]
                    input_char = candidate
                    break
            if input_guid:
                break
        output_guid = output_char = None
        for dev in self.devices:
            ids = [
                c.get("identifier")
                for c in dev.get("functions", [])
                if isinstance(c, dict)
            ]
            for candidate in ("relay", "relayChannel1"):
                if candidate in ids:
                    output_guid = dev["deviceGuid"]
                    output_char = candidate
                    break
            if output_guid:
                break
        if not input_guid or not output_guid:
            return None
        return {
            "enabled": True,
            "description": "Default impulse switch automation",
            "configuration": {
                "automationGuid": str(uuid.uuid4()),
                "logic": "buttonImpulseSwitch",
                "inputDeviceGuid": input_guid,
                "inputCharacteristicIdentifier": input_char,
                "outputDeviceGuid": output_guid,
                "outputCharacteristicIdentifier": output_char,
                "addOns": [],
                "logicConfiguration": {},
            },
            "operatingStatus": "success",
            "errors": [],
        }


class Handler(SimpleHTTPRequestHandler):
    state: StudioState
    mode: str = "mock"
    gateway_host: str = ""
    gateway_config: dict = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STUDIO_DIR), **kwargs)

    def log_message(self, format: str, *args):  # noqa: A002 - stdlib signature
        sys.stderr.write("[studio] " + format % args + "\n")

    def end_headers(self):
        # Dev harness: never cache HTML/JS so UI edits apply on reload.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _live_devices_products(self):
        """Fetch live /devices + /products; returns (devices, products) or (None, error)."""
        assert self.state.live is not None
        try:
            devices = self.state.live._call("GET", "/devices")
            products = self.state.live._call("GET", "/products")
            return devices, products
        except Exception as err:  # noqa: BLE001
            return None, str(err)

    def _send_json(self, obj, status: int = 200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode() or "{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            try:
                count = len(self.state.list_automations())
            except Exception as err:  # noqa: BLE001 - never drop the connection
                return self._send_json({"error": str(err)}, 502)
            return self._send_json(
                {"mode": self.mode, "host": self.gateway_host, "rule_count": count}
            )
        if parsed.path == "/api/automations":
            try:
                return self._send_json(self.state.list_automations())
            except Exception as err:  # noqa: BLE001
                return self._send_json({"error": str(err)}, 502)
        if parsed.path == "/api/devices":
            if self.state.live:
                try:
                    data = self.state.live._call("GET", "/devices")
                    items = data if isinstance(data, list) else data.get("devices", data)
                    return self._send_json(self.state.annotated_devices(items))
                except Exception as err:  # noqa: BLE001
                    return self._send_json({"error": str(err)}, 502)
            return self._send_json(self.state.annotated_devices(self.state.devices))
        if parsed.path == "/api/enocean_devices":
            return self._send_json(self.state.enocean_devices)
        if parsed.path == "/api/products":
            return self._send_json(self.state.products)
        if parsed.path == "/api/device_settings":
            try:
                describe = _automations.device_settings
            except (AttributeError, NameError):
                return self._send_json({"error": "device settings unavailable"}, 501)
            if self.state.live:
                devices, products = self._live_devices_products()
                if devices is None:
                    return self._send_json({"error": products}, 502)
                return self._send_json(describe(devices, products))
            return self._send_json(
                describe(self.state.devices, self.state.products)
            )
        if parsed.path == "/api/capabilities":
            try:
                build_capabilities = _automations.build_capabilities
            except (AttributeError, NameError):
                return self._send_json({"error": "capabilities unavailable"}, 501)
            if self.state.live:
                devices, products = self._live_devices_products()
                if devices is None:
                    return self._send_json({"error": products}, 502)
                return self._send_json(build_capabilities(devices, products))
            return self._send_json(
                build_capabilities(self.state.devices, self.state.products)
            )
        if parsed.path == "/api/gateways":
            try:
                discovered = discover_gateways()
            except Exception:  # noqa: BLE001
                discovered = []
            cfg = Handler.gateway_config
            configured_host = str(cfg.get("host") or "").strip()

            def _norm(host: str) -> str:
                host = host.strip().lower().rstrip(".")
                return host[: -len(".local")] if host.endswith(".local") else host

            if configured_host and not any(
                _norm(g["host"]) == _norm(configured_host) for g in discovered
            ):
                discovered.insert(
                    0,
                    {
                        "name": configured_host,
                        "host": configured_host,
                        "port": int(cfg.get("port") or 443),
                        "ips": [],
                        "source": "configured",
                    },
                )
            import socket as _sock

            for g in discovered:
                if not g["ips"]:
                    try:
                        for fam, _, _, _, sa in _sock.getaddrinfo(
                            g["host"] + ".local", None, type=_sock.SOCK_STREAM
                        ):
                            if fam in (_sock.AF_INET, _sock.AF_INET6):
                                ip = sa[0]
                                if ip not in g["ips"]:
                                    g["ips"].append(ip)
                    except OSError:
                        pass
            return self._send_json({"gateways": discovered})
        if parsed.path in ("/", "/index.html"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/mode":
            body = self._read_json()
            want = str(body.get("mode", "")).lower()
            if want == "live":
                cfg = Handler.gateway_config
                host = str(body.get("host") or cfg.get("host") or "").strip()
                try:
                    port = int(body.get("port") or cfg.get("port") or 443)
                except (TypeError, ValueError):
                    return self._send_json({"error": "invalid port"}, 400)
                pop = str(body.get("pop") or cfg.get("pop") or "")
                if body.get("pop"):
                    cfg["pop"] = pop  # per-device PIN, session-only (not persisted)
                if not host or not pop:
                    return self._send_json(
                        {"error": "live gateway needs a host and a device PIN (ELTAKO_HOST/ELTAKO_POP)"},
                        400,
                    )
                try:
                    stored = os.environ.get("ELTAKO_API_KEY", "").strip() or None
                    prev = str(cfg.get("host") or "").strip().lower().rstrip(".")
                    if prev.endswith(".local"):
                        prev = prev[: -len(".local")]
                    if "." not in host:
                        host += ".local"  # bare mDNS names don't resolve via the system resolver
                    now = host.lower().rstrip(".")
                    if now.endswith(".local"):
                        now = now[: -len(".local")]
                    if now != prev:
                        stored = None  # API keys are per-device
                    live = GatewayProxy(host, port, pop, api_key=stored)
                    if not live.api_key:
                        live.login()
                        if live.api_key:
                            try:
                                persist_env_value("ELTAKO_API_KEY", live.api_key)
                            except OSError:
                                pass
                            os.environ["ELTAKO_API_KEY"] = live.api_key
                    # Verify contact (and credentials) before committing:
                    # a stored key skips login, so only a real roundtrip
                    # proves the gateway is reachable.
                    probe = live._call("GET", "/services/eltako/automations")
                    count = len(probe) if isinstance(probe, list) else 0
                except Exception as err:  # noqa: BLE001
                    return self._send_json(
                        {"error": f"live login failed: {err}"}, 502
                    )
                # Commit only after verified contact.
                self.state.set_live(live)
                Handler.mode = "live"
                Handler.gateway_host = host
                if now != prev:
                    try:
                        persist_env_value("ELTAKO_HOST", host)
                    except OSError:
                        pass
                cfg["host"] = host
                cfg["port"] = port
                return self._send_json(
                    {"mode": "live", "host": cfg["host"], "rule_count": count}
                )
            if want == "mock":
                self.state.set_mock()
                Handler.mode = "mock"
                Handler.gateway_host = "mock fixtures"
                return self._send_json(
                    {
                        "mode": "mock",
                        "host": "mock fixtures",
                        "rule_count": len(self.state.automations),
                    }
                )
            return self._send_json({"error": "unknown mode (use live|mock)"}, 400)
        if parsed.path == "/api/validate":
            if validate_rule is None or AutomationRule is None:
                return self._send_json({"ok": True, "problems": []})
            assert validate_rule is not None and AutomationRule is not None
            try:
                rule = AutomationRule.from_dict(self._read_json())
                problems = validate_rule(rule)
                return self._send_json({"ok": not problems, "problems": problems})
            except (ValueError, KeyError, TypeError) as err:
                return self._send_json({"ok": False, "problems": [f"Malformed rule: {err}"]}, 400)
        if parsed.path == "/api/automations":
            try:
                item = self.state.create_automation(self._read_json())
                return self._send_json(item, 201)
            except Exception as err:  # noqa: BLE001
                return self._send_json({"error": str(err)}, 502)
        return self._send_json({"error": "not found"}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/devices/"):
            guid = parsed.path.rsplit("/", 1)[-1]
            name = str(self._read_json().get("displayName", "")).strip()
            if not name:
                return self._send_json({"error": "displayName must not be empty"}, 400)
            if len(name) > 128:
                return self._send_json({"error": "displayName too long (max 128)"}, 400)
            try:
                return self._send_json(self.state.rename_device(guid, name))
            except KeyError:
                return self._send_json({"error": "unknown guid"}, 404)
            except Exception as err:  # noqa: BLE001
                return self._send_json({"error": str(err)}, 502)
        if parsed.path.startswith("/api/automations/"):
            guid = parsed.path.rsplit("/", 1)[-1]
            try:
                item = self.state.update_automation(guid, self._read_json())
                return self._send_json(item)
            except KeyError:
                return self._send_json({"error": "unknown guid"}, 404)
            except Exception as err:  # noqa: BLE001
                return self._send_json({"error": str(err)}, 502)
        return self._send_json({"error": "not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/automations":
            try:
                self.state.reset_automations()
                return self._send_json({"ok": True})
            except Exception as err:  # noqa: BLE001
                return self._send_json({"error": str(err)}, 502)
        if parsed.path.startswith("/api/automations/"):
            guid = parsed.path.rsplit("/", 1)[-1]
            try:
                self.state.delete_automation(guid)
                return self._send_json({"ok": True})
            except KeyError:
                return self._send_json({"error": "unknown guid"}, 404)
            except Exception as err:  # noqa: BLE001
                return self._send_json({"error": str(err)}, 502)
        return self._send_json({"error": "not found"}, 404)


def persist_env_value(key: str, value: str) -> None:
    """Upsert a KEY=value line in the repo .env (preserves other lines)."""
    path = REPO_ROOT / ".env"
    lines = path.read_text().splitlines() if path.is_file() else []
    entry = f"{key}={value}"
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = entry
            break
    else:
        lines.append(entry)
    path.write_text("\n".join(lines) + "\n")


def discover_gateways(timeout: float = 3.0) -> list[dict]:
    """Browse _hap._tcp and _http._tcp via mDNS, return Eltako gateways.

    Stdlib-only best effort: joins 224.0.0.251 on an ephemeral port (no
    need to bind UDP/5353, which the OS resolver usually owns) and
    correlates PTR/SRV/A records collected within the timeout window.
    Service enumeration (_services._dns-sd) picks up Eltako-specific
    service types (e.g. _eltako._tcp); only instances whose name or
    target host contains "eltako" are kept.
    """

    import socket as _socket
    import struct as _struct
    import time as _time

    def encode_name(name: str) -> bytes:
        out = b""
        for part in name.rstrip(".").split("."):
            raw = part.encode("utf-8")
            out += bytes([len(raw)]) + raw
        return out + b"\x00"

    def decode_name(msg: bytes, off: int) -> tuple[str, int]:
        labels: list[str] = []
        end = off
        jumped = False
        loops = 0
        while loops < 64:
            loops += 1
            if off >= len(msg):
                break
            length = msg[off]
            if length == 0:
                if not jumped:
                    end = off + 1
                break
            if length & 0xC0 == 0xC0:
                if off + 1 >= len(msg):
                    break
                ptr = ((length & 0x3F) << 8) | msg[off + 1]
                if not jumped:
                    end = off + 2
                off = ptr
                jumped = True
                continue
            off += 1
            labels.append(msg[off:off + length].decode("utf-8", "replace"))
            off += length
            if not jumped:
                end = off
        return (".".join(labels), end)

    def query(name: str, qtype: int = 12) -> bytes:
        return (
            _struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0)
            + encode_name(name)
            + _struct.pack(">HH", qtype, 1)  # qtype, IN
        )

    found: dict[str, dict] = {}
    addrs: dict[str, list[str]] = {}
    queried: set[tuple[str, int]] = set()

    def send_query(sock: "_socket.socket", name: str, qtype: int = 12) -> None:
        key = (name.lower().rstrip("."), qtype)
        if key in queried:
            return
        queried.add(key)
        try:
            sock.sendto(query(name, qtype), ("224.0.0.251", 5353))
        except OSError:
            pass

    try:
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM, _socket.IPPROTO_UDP)
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        sock.bind(("", 0))
        mreq = _struct.pack(
            "4s4s",
            _socket.inet_aton("224.0.0.251"),
            _socket.inet_aton("0.0.0.0"),
        )
        sock.setsockopt(_socket.IPPROTO_IP, _socket.IP_ADD_MEMBERSHIP, mreq)
        sock.settimeout(0.3)
        for service in (
            "_services._dns-sd._udp.local",
            "_hap._tcp.local",
            "_http._tcp.local",
            "_eltako._tcp.local",
        ):
            send_query(sock, service)
        deadline = _time.time() + timeout
        while _time.time() < deadline:
            try:
                data, _ = sock.recvfrom(4096)
            except _socket.timeout:
                continue
            except OSError:
                break
            try:
                if len(data) < 12:
                    continue
                _, _, qdcount, ancount, nscount, arcount = _struct.unpack(
                    ">HHHHHH", data[:12]
                )
                off = 12
                for _ in range(qdcount):
                    _, off = decode_name(data, off)
                    off += 4
                for _ in range(ancount + nscount + arcount):
                    name, off = decode_name(data, off)
                    rtype, _rclass, _ttl, rdlen = _struct.unpack(
                        ">HHIH", data[off:off + 10]
                    )
                    off += 10
                    rdata = data[off:off + rdlen]
                    rstart = off
                    off += rdlen
                    lname = name.lower()
                    if rtype == 12:  # PTR -> service instance / service type
                        target, _ = decode_name(data, rstart)
                        if lname == "_services._dns-sd._udp.local":
                            # Service enumeration: follow Eltako service types.
                            if "eltako" in target.lower():
                                send_query(sock, target.rstrip("."))
                        else:
                            found.setdefault(
                                target.lower(),
                                {"instance": target, "service": lname},
                            )
                    elif rtype == 33:  # SRV -> instance target host + port
                        port = _struct.unpack(">H", rdata[4:6])[0]
                        thost, _ = decode_name(rdata, 6)
                        ent = found.setdefault(
                            lname, {"instance": name, "service": ""}
                        )
                        ent["target"] = thost
                        ent["port"] = port
                        if thost.lower() not in addrs:
                            send_query(sock, thost, 1)  # A record for the host
                    elif rtype == 1 and len(rdata) >= 4:  # A
                        addrs.setdefault(lname, []).append(
                            _socket.inet_ntoa(rdata[:4])
                        )
                    elif rtype == 28 and len(rdata) >= 16:  # AAAA
                        addrs.setdefault(lname, []).append(
                            _socket.inet_ntop(_socket.AF_INET6, rdata[:16])
                        )
            except (ValueError, IndexError, _struct.error, UnicodeError):
                continue
    except OSError:
        return []
    finally:
        try:
            sock.close()
        except (NameError, OSError):
            pass

    gateways: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for key, ent in found.items():
        instance = str(ent.get("instance", ""))
        target = str(ent.get("target", ""))
        if "eltako" not in instance.lower() and "eltako" not in target.lower():
            continue
        host = target.rstrip(".")
        if host.lower().endswith(".local"):
            host = host[: -len(".local")]
        port = int(ent.get("port") or 443)
        if (host.lower(), port) in seen:
            continue
        seen.add((host.lower(), port))
        short = instance.split(".")[0] if instance else host
        gateways.append(
            {
                "name": short,
                "host": host,
                "port": port,
                "ips": addrs.get(target.lower(), []),
                "source": "mdns",
            }
        )
    return sorted(gateways, key=lambda g: g["name"].lower())


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Eltako automation studio dev server")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--live", action="store_true", help="proxy live gateway")
    parser.add_argument("--host", default=os.environ.get("ELTAKO_HOST", ""))
    parser.add_argument("--gateway-port", type=int, default=int(os.environ.get("ELTAKO_PORT", "443")))
    parser.add_argument("--pop", default=os.environ.get("ELTAKO_POP", ""))
    args = parser.parse_args()

    live = None
    mode = "mock"
    if args.live:
        if not args.host or not args.pop:
            parser.error("--live needs --host and --pop (or ELTAKO_HOST/ELTAKO_POP in .env)")
        stored_key = os.environ.get("ELTAKO_API_KEY", "").strip() or None
        live = GatewayProxy(args.host, args.gateway_port, args.pop, api_key=stored_key)
        if not live.api_key:
            live.login()
            if live.api_key and live.api_key != stored_key:
                persist_env_value("ELTAKO_API_KEY", live.api_key)
        mode = "live"

    Handler.state = StudioState(live)
    Handler.mode = mode
    Handler.gateway_host = args.host if live else "mock fixtures"
    Handler.gateway_config = {"host": args.host, "port": args.gateway_port, "pop": args.pop}

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[studio] {mode} mode → http://127.0.0.1:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
