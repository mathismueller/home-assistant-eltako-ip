"""Standalone dev server for the Eltako on-device automation studio.

Stdlib only. Serves studio/ static files and a thin JSON bridge that mirrors
the future Home Assistant WebSocket API shape:

  GET    /api/status               -> {mode, host, rule_count}
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
  python3 studio/server.py --live --read-only  # explore live box, block writes
  python3 studio/server.py --port 8099 --live --host 192.168.1.100
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

    def __init__(self, host: str, port: int, pop: str) -> None:
        self.base = f"https://{host}:{port}/api/v0"
        self.pop = pop
        self.api_key: str | None = None
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
        self.automations: list[dict] = load_fixture("automations", [])
        self.devices: list[dict] = load_fixture("devices", [])
        self.enocean_devices: list[dict] = load_fixture("enocean_devices", [])
        # products.json is {"products": [...]} on gateways; normalize to list
        raw_products = load_fixture("products", [])
        if isinstance(raw_products, dict):
            raw_products = raw_products.get("products", list(raw_products.values()))
        self.products: list[dict] = (
            list(raw_products) if isinstance(raw_products, list) else []
        )

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
    read_only: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STUDIO_DIR), **kwargs)

    def log_message(self, format: str, *args):  # noqa: A002 - stdlib signature
        sys.stderr.write("[studio] " + format % args + "\n")

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
            count = len(self.state.list_automations())
            return self._send_json(
                {
                    "mode": self.mode,
                    "host": self.gateway_host,
                    "rule_count": count,
                    "read_only": self.read_only,
                }
            )
        if parsed.path == "/api/automations":
            return self._send_json(self.state.list_automations())
        if parsed.path == "/api/devices":
            if self.state.live:
                try:
                    data = self.state.live._call("GET", "/devices")
                    items = data if isinstance(data, list) else data.get("devices", data)
                    return self._send_json(items)
                except Exception as err:  # noqa: BLE001
                    return self._send_json({"error": str(err)}, 502)
            return self._send_json(self.state.devices)
        if parsed.path == "/api/enocean_devices":
            return self._send_json(self.state.enocean_devices)
        if parsed.path == "/api/products":
            return self._send_json(self.state.products)
        if parsed.path == "/api/capabilities":
            try:
                build_capabilities = _automations.build_capabilities
            except (AttributeError, NameError):
                return self._send_json({"error": "capabilities unavailable"}, 501)
            if self.state.live:
                try:
                    devices = self.state.live._call("GET", "/devices")
                    products = self.state.live._call("GET", "/products")
                except Exception as err:  # noqa: BLE001
                    return self._send_json({"error": str(err)}, 502)
                return self._send_json(build_capabilities(devices, products))
            return self._send_json(
                build_capabilities(self.state.devices, self.state.products)
            )
        if parsed.path in ("/", "/index.html"):
            self.path = "/index.html"
        return super().do_GET()

    def _blocked_read_only(self, parsed) -> bool:
        if self.read_only and parsed.path.startswith("/api/automations"):
            self._send_json({"error": "read-only mode: mutations disabled"}, 403)
            return True
        return False

    def do_POST(self):
        parsed = urlparse(self.path)
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
            if self._blocked_read_only(parsed):
                return
            try:
                item = self.state.create_automation(self._read_json())
                return self._send_json(item, 201)
            except Exception as err:  # noqa: BLE001
                return self._send_json({"error": str(err)}, 502)
        return self._send_json({"error": "not found"}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if self._blocked_read_only(parsed):
            return
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
        if self._blocked_read_only(parsed):
            return
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


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Eltako automation studio dev server")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--live", action="store_true", help="proxy live gateway")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="reject mutating calls (POST/PUT/DELETE on /api/automations)",
    )
    parser.add_argument("--host", default=os.environ.get("ELTAKO_HOST", ""))
    parser.add_argument("--gateway-port", type=int, default=int(os.environ.get("ELTAKO_PORT", "443")))
    parser.add_argument("--pop", default=os.environ.get("ELTAKO_POP", ""))
    args = parser.parse_args()

    live = None
    mode = "mock"
    if args.live:
        if not args.host or not args.pop:
            parser.error("--live needs --host and --pop (or ELTAKO_HOST/ELTAKO_POP in .env)")
        live = GatewayProxy(args.host, args.gateway_port, args.pop)
        live.login()
        mode = "live"

    Handler.state = StudioState(live)
    Handler.mode = mode
    Handler.gateway_host = args.host if live else "mock fixtures"
    Handler.read_only = args.read_only

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    ro = " read-only" if args.read_only else ""
    print(f"[studio] {mode}{ro} mode → http://127.0.0.1:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
