import yaml
import json
from pathlib import Path

spec_path = Path(__file__).parent / "api.yaml"
with open(spec_path) as f:
    spec = yaml.safe_load(f)

print("=== Tags ===")
for tag in spec.get("tags", []):
    desc = tag.get("description", "").splitlines()[0] if tag.get("description") else ""
    print(f"- {tag.get('name')}: {desc}")

print("\n=== EnOcean Endpoints ===")
for p, methods in spec["paths"].items():
    if "enocean" in p:
        for m, op in methods.items():
            if m in ["get", "post", "put", "delete", "patch"]:
                print(f"{m.upper():6} {p}")
                print(f"       Summary: {op.get('summary')}")

print("\n=== Actuator Endpoints ===")
for p, methods in spec["paths"].items():
    if "actuator" in p:
        for m, op in methods.items():
            if m in ["get", "post", "put", "delete", "patch"]:
                print(f"{m.upper():6} {p} : {op.get('summary')}")

print("\n=== Matter Endpoints ===")
for p, methods in spec["paths"].items():
    if "matter" in p:
        for m, op in methods.items():
            if m in ["get", "post", "put", "delete", "patch"]:
                print(f"{m.upper():6} {p} : {op.get('summary')}")

print("\n=== Devices Endpoints ===")
for p, methods in spec["paths"].items():
    if "/devices" in p and "enocean" not in p and "actuator" not in p and "matter" not in p:
        for m, op in methods.items():
            if m in ["get", "post", "put", "delete", "patch"]:
                print(f"{m.upper():6} {p} : {op.get('summary')}")
