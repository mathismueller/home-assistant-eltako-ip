import json
from pathlib import Path

fixtures_path = Path(__file__).parent.parent / "tests/fixtures/products.json"
with open(fixtures_path) as f:
    data = json.load(f)

guids = {
    "4893e06b-448c-40d5-b426-42e2e6b73656",
    "6f6d379f-4c6f-45ed-b881-671ed7ea8970",
    "791a7c28-22e3-4fab-8ecc-0084e15396c5"
}

for p in data.get("products", []):
    if p.get("productGuid") in guids:
        print("Product:", p.get("productName"), f"({p.get('productGuid')})")
        print("  Type:", p.get("productType"))
        print("  Profile:", p.get("profile"))
        print("  Functions:", p.get("functions"))
        print("  Infos:", p.get("infos"))
        print("---")
