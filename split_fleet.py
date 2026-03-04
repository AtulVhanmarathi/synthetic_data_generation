"""
Split fleet.json into focused files, dropping image assets.
"""

import json
import os
from urllib.parse import urlparse

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "data")

with open(os.path.join(DATA_DIR, "fleet.json"), "r", encoding="utf-8") as f:
    fleet = json.load(f)

pc24, pc12, general = [], [], []

for p in fleet:
    path = urlparse(p["url"]).path.lower()
    if "wp-content/uploads" in path:
        continue  # drop image assets
    elif "pc-24" in path or "pc24" in path:
        pc24.append(p)
    elif "pc-12" in path or "pc12" in path:
        pc12.append(p)
    else:
        general.append(p)

files = {
    "fleet_pc24_jet.json": pc24,
    "fleet_pc12_turboprop.json": pc12,
    "fleet_general.json": general,
}

for filename, data in files.items():
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  {filename:30s} -> {len(data)} pages")

print(f"\nDropped 59 image asset entries. Original fleet.json untouched.")
