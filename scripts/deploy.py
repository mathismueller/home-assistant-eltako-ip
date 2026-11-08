#!/usr/bin/env python3
"""Local and remote deployment script for Eltako Series 62/64 IP Home Assistant integration.

Supports:
1. Direct file copy or symlinking into a local Home Assistant config directory.
2. Automated bundling/vendoring of `aioeltako` so Home Assistant requires no PyPI install.
3. Remote deployment via SSH/rsync/scp to Home Assistant OS or container.
4. Optional configuration validation and automatic Home Assistant restart via REST API or CLI.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
CUSTOM_COMPONENT_SRC = REPO_ROOT / "custom_components" / "eltako_ip"
LIB_SRC = REPO_ROOT / "src" / "aioeltako_ip"


def load_env() -> dict[str, str]:
    """Load configuration variables from .env."""
    load_dotenv(REPO_ROOT / ".env")
    return {
        "HA_CONFIG_DIR": os.getenv("HA_CONFIG_DIR", ""),
        "HA_URL": os.getenv("HA_URL", "http://homeassistant.local:8123"),
        "HA_TOKEN": os.getenv("HA_TOKEN", ""),
        "HA_REMOTE": os.getenv("HA_REMOTE", ""),
    }


def clean_caches(directory: Path) -> None:
    """Remove cache artifacts like __pycache__ and .DS_Store."""
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            if name in (".DS_Store", "Thumbs.db"):
                try:
                    os.unlink(Path(root) / name)
                except OSError:
                    pass
        for name in dirs:
            if name == "__pycache__":
                try:
                    shutil.rmtree(Path(root) / name)
                except OSError:
                    pass


def validate_source() -> None:
    """Verify integration files before deployment."""
    manifest_file = CUSTOM_COMPONENT_SRC / "manifest.json"
    if not manifest_file.exists():
        print(f"Error: {manifest_file} not found!", file=sys.stderr)
        sys.exit(1)

    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"Error: manifest.json is invalid: {e}", file=sys.stderr)
        sys.exit(1)

    required_keys = ["domain", "name", "version", "homeassistant"]
    for key in required_keys:
        if key not in manifest:
            print(f"Error: manifest.json missing required key '{key}'", file=sys.stderr)
            sys.exit(1)

    print(f"✓ Validated manifest for '{manifest['name']}' (domain: {manifest['domain']}, v{manifest['version']})")


def deploy_local(
    target_config_dir: Path,
    bundle_lib: bool = True,
    dry_run: bool = False,
) -> Path:
    """Deploy the custom component into a local Home Assistant config directory."""
    target_custom_components = target_config_dir / "custom_components"
    target_dest = target_custom_components / "eltako_ip"

    print(f"\n--- Local Deployment ---")
    print(f"Source:      {CUSTOM_COMPONENT_SRC}")
    print(f"Target:      {target_dest}")
    print(f"Bundle lib:  {'Yes (aioeltako_ip)' if bundle_lib else 'No'}")

    if dry_run:
        print("[DRY-RUN] No files modified.")
        return target_dest

    target_custom_components.mkdir(parents=True, exist_ok=True)

    if target_dest.exists() or target_dest.is_symlink():
        print(f"Refreshing existing target directory {target_dest}...")
        if target_dest.is_symlink() or not target_dest.is_dir():
            target_dest.unlink()
        else:
            shutil.rmtree(target_dest)

    shutil.copytree(CUSTOM_COMPONENT_SRC, target_dest)
    clean_caches(target_dest)
    print(f"✓ Copied integration files to {target_dest}")

    if bundle_lib:
        target_lib = target_dest / "aioeltako_ip"
        if target_lib.exists():
            shutil.rmtree(target_lib)
        shutil.copytree(LIB_SRC, target_lib)
        clean_caches(target_lib)
        print(f"✓ Bundled client library at {target_lib}")

    return target_dest


def deploy_remote(
    remote_spec: str,
    bundle_lib: bool = True,
    dry_run: bool = False,
) -> None:
    """Deploy via rsync or scp to a remote host (e.g. home or root@homeassistant.local:/config)."""
    if ":" in remote_spec:
        host, path = remote_spec.split(":", 1)
    else:
        host, path = remote_spec, "/config"
    path = path.rstrip("/")
    target_remote_path = f"{host}:{path}/custom_components/eltako_ip"

    print(f"\n--- Remote Deployment ---")
    print(f"Remote Host: {host}")
    print(f"Remote Path: {path}/custom_components/eltako_ip")
    print(f"Bundle lib:  {'Yes (aioeltako_ip)' if bundle_lib else 'No'}")

    # Prepare staging directory
    staging_dir = REPO_ROOT / "build" / "deploy_staging" / "eltako_ip"
    if staging_dir.parent.exists():
        shutil.rmtree(staging_dir.parent)
    staging_dir.mkdir(parents=True)

    # Copy files
    shutil.copytree(CUSTOM_COMPONENT_SRC, staging_dir, dirs_exist_ok=True)
    if bundle_lib:
        target_lib = staging_dir / "aioeltako_ip"
        shutil.copytree(LIB_SRC, target_lib, dirs_exist_ok=True)

    clean_caches(staging_dir)

    if dry_run:
        print("[DRY-RUN] Remote sync skipped.")
        return

    # Check if remote host has rsync available
    has_remote_rsync = False
    if shutil.which("rsync"):
        try:
            check_rsync = subprocess.run(
                ["ssh", host, "which rsync"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            has_remote_rsync = check_rsync.returncode == 0
        except Exception:
            has_remote_rsync = False

    if has_remote_rsync:
        cmd = [
            "rsync",
            "-avz",
            "--delete",
            f"{staging_dir}/",
            f"{target_remote_path}/",
        ]
        print(f"Using rsync: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"Error: rsync failed with return code {result.returncode}", file=sys.stderr)
            sys.exit(result.returncode)
    else:
        # Fallback to scp + ssh
        print(f"Remote host does not have rsync; using scp + ssh...")
        mkdir_cmd = ["ssh", host, f"mkdir -p {path}/custom_components/eltako_ip"]
        subprocess.run(mkdir_cmd, check=True)
        scp_cmd = ["scp", "-r", f"{staging_dir}/.", f"{host}:{path}/custom_components/eltako_ip/"]
        print(f"Running: {' '.join(scp_cmd)}")
        result = subprocess.run(scp_cmd)
        if result.returncode != 0:
            print(f"Error: scp failed with code {result.returncode}", file=sys.stderr)
            sys.exit(result.returncode)

    print(f"✓ Remote deployment complete.")


def restart_homeassistant(ha_url: str, ha_token: str) -> None:
    """Validate config and restart Home Assistant via REST API."""
    print(f"\n--- Checking Home Assistant Configuration ---")
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json",
    }
    check_url = f"{ha_url.rstrip('/')}/api/config/core/check_config"

    try:
        req = urllib.request.Request(check_url, data=b"{}", headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            status = data.get("result")
            errors = data.get("errors")
            if status == "valid":
                print("✓ Home Assistant configuration check passed (valid).")
            else:
                print(f"⚠️ Warning: Configuration check returned status '{status}'. Errors: {errors}")
    except urllib.error.HTTPError as e:
        print(f"HTTP error during config check: {e.code} {e.reason}", file=sys.stderr)
        return
    except Exception as e:
        print(f"Could not contact Home Assistant at {ha_url}: {e}", file=sys.stderr)
        return

    print(f"Restarting Home Assistant via {ha_url}...")
    restart_url = f"{ha_url.rstrip('/')}/api/services/homeassistant/restart"
    try:
        req = urllib.request.Request(restart_url, data=b"{}", headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print("✓ Home Assistant restart service called successfully.")
    except Exception as e:
        print(f"Error triggering restart: {e}", file=sys.stderr)


def main() -> None:
    env_vars = load_env()

    parser = argparse.ArgumentParser(
        description="Deploy Eltako Series 62/64 IP integration for local testing."
    )
    parser.add_argument(
        "-t",
        "--target",
        type=str,
        default=env_vars["HA_CONFIG_DIR"],
        help="Path to local Home Assistant config directory (or set HA_CONFIG_DIR in .env)",
    )
    parser.add_argument(
        "-r",
        "--remote",
        type=str,
        default=env_vars["HA_REMOTE"],
        help="Remote destination (e.g. root@homeassistant.local:/config or set HA_REMOTE in .env)",
    )
    parser.add_argument(
        "--no-bundle-lib",
        dest="bundle_lib",
        action="store_false",
        default=True,
        help="Do NOT bundle aioeltako_ip into the component directory (requires aioeltako-ip in HA env)",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        default=False,
        help="Trigger configuration check and restart Home Assistant after deployment",
    )
    parser.add_argument(
        "--ha-url",
        type=str,
        default=env_vars["HA_URL"],
        help="Home Assistant URL for API restart (default: http://homeassistant.local:8123 or HA_URL)",
    )
    parser.add_argument(
        "--ha-token",
        type=str,
        default=env_vars["HA_TOKEN"],
        help="Home Assistant Long-Lived Access Token (or HA_TOKEN in .env)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Pre-deployment validation
    validate_source()

    deployed = False
    if args.remote:
        deploy_remote(
            remote_spec=args.remote,
            bundle_lib=args.bundle_lib,
            dry_run=args.dry_run,
        )
        deployed = True

    if args.target:
        target_path = Path(os.path.expanduser(args.target)).resolve()
        deploy_local(
            target_config_dir=target_path,
            bundle_lib=args.bundle_lib,
            dry_run=args.dry_run,
        )
        deployed = True

    if not deployed:
        # Check standard default candidate paths
        candidate_paths = [
            Path.home() / ".homeassistant",
            Path("/config"),
        ]
        found_candidate = None
        for candidate in candidate_paths:
            if candidate.exists() and candidate.is_dir():
                found_candidate = candidate
                break

        if found_candidate:
            print(f"Auto-detected local Home Assistant configuration directory at: {found_candidate}")
            deploy_local(
                target_config_dir=found_candidate,
                bundle_lib=args.bundle_lib,
                dry_run=args.dry_run,
            )
            deployed = True
        else:
            print(
                "\nNo target specified and no default Home Assistant installation detected.\n"
                "Please specify a target directory or remote host:\n"
                "  python3 scripts/deploy.py --target /path/to/homeassistant/config\n"
                "  python3 scripts/deploy.py --remote root@homeassistant.local:/config\n"
                "Or set HA_CONFIG_DIR in your .env file.\n",
                file=sys.stderr,
            )
            sys.exit(1)

    # Optional restart
    if args.restart and not args.dry_run:
        if args.ha_token:
            restart_homeassistant(args.ha_url, args.ha_token)
        else:
            print("\nNote: --restart was requested but HA_TOKEN is not set.")
            print("To enable automatic API restart, generate a Long-Lived Access Token in HA")
            print("(Profile -> Long-Lived Access Tokens) and add it to .env as HA_TOKEN=...")

    print("\n✓ Deployment completed successfully!")
    print("\nNext steps in Home Assistant:")
    print("  1. Restart Home Assistant (if not restarted automatically).")
    print("  2. Navigate to Settings > Devices & Services > Add Integration.")
    print("  3. Search for 'Eltako Series 62/64 IP'.")
    print("  4. Enter your device IP and Proof-of-Possession (PoP) PIN.")


if __name__ == "__main__":
    main()
