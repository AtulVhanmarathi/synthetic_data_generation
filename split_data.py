"""
Split all_pages.json into focused files by category grouping.
Keeps the original file untouched.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "data")
INPUT_FILE = os.path.join(DATA_DIR, "all_pages.json")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    all_pages = json.load(f)

# Group 1: Content (403 pages)
content = [p for p in all_pages if p.get("category") == "content"]

# Group 2: Fleet (110 pages)
fleet = [p for p in all_pages if p.get("category") == "fleet"]

# Group 3: Clubbed — Why PlaneSense + Programs + Utility + Blog + Home
clubbed_categories = {"why_planesense", "programs", "utility", "blog", "home"}
clubbed = [p for p in all_pages if p.get("category") in clubbed_categories]

# Save files
files = {
    "content.json": content,
    "fleet.json": fleet,
    "company_overview.json": clubbed,
}

for filename, data in files.items():
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  {filename:30s} -> {len(data)} pages")

print(f"\nOriginal all_pages.json untouched ({len(all_pages)} pages)")
