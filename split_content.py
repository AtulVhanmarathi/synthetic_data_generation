"""
Split content.json into 7 focused files, dropping image assets.
"""

import json
import os
from urllib.parse import urlparse

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "data")

with open(os.path.join(DATA_DIR, "content.json"), "r", encoding="utf-8") as f:
    content = json.load(f)

buckets = {
    "content_fractional_ownership.json": [],
    "content_general.json": [],
    "content_destinations_travel.json": [],
    "content_aircraft_fleet.json": [],
    "content_comparisons_cost.json": [],
    "content_news_awards_community.json": [],
    "content_people_guides.json": [],
}

for p in content:
    path = urlparse(p["url"]).path.lower()
    title = p.get("title", "").lower()

    if "wp-content/uploads" in path:
        continue

    if any(w in path or w in title for w in [
        "destination", "resort", "bermuda", "cape-may", "outer-banks",
        "white-mountain", "spruce-peak", "ski-destination", "elk-river",
        "bakers-bay", "barber", "fredericksburg", "coastal-new-england",
        "inn-at-little", "fly-in-resort", "nantucket",
    ]):
        buckets["content_destinations_travel.json"].append(p)
    elif any(w in path or w in title for w in [
        "fractional-ownership", "fractional-aircraft", "fractional-jet",
        "what-is-fractional", "understanding-fractional", "fractional-program",
        "fractional-ops",
    ]):
        buckets["content_fractional_ownership.json"].append(p)
    elif any(w in path or w in title for w in [
        "charter", "jet-card", "jet-membership", "comparing-private",
        "whole-craft", "best-option", "cost", "price", "private-jet-cost",
        "value", "investment", "saves-time",
    ]):
        buckets["content_comparisons_cost.json"].append(p)
    elif any(w in path or w in title for w in [
        "pc-24", "pc24", "pc-12", "pc12", "pilatus", "fleet",
    ]):
        buckets["content_aircraft_fleet.json"].append(p)
    elif any(w in path or w in title for w in [
        "survey", "rank", "award", "forbes", "elite-traveler", "named",
        "celebrates", "anniversary", "history", "milestone", "30th",
        "25-year", "pearl", "super-bowl", "eclipse", "storm", "weather",
        "holiday", "summer", "food-drive", "donation", "hurricane",
        "relief", "charity", "food-bank",
    ]):
        buckets["content_news_awards_community.json"].append(p)
    elif any(w in path or w in title for w in [
        "who-flies", "testimonial", "customer", "in-their-words", "owner",
        "pilot", "training", "technician", "simulator", "vrpilot",
        "checklist", "tips", "questions", "guide", "how-to", "myths",
        "things-you-didnt", "safety", "faa", "part-91", "part-135",
        "argus", "illegal-charter", "risk",
    ]):
        buckets["content_people_guides.json"].append(p)
    else:
        buckets["content_general.json"].append(p)

total = 0
for filename, data in buckets.items():
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  {filename:45s} -> {len(data)} pages")
    total += len(data)

print(f"\nTotal: {total} pages across 7 files. Dropped 260 image assets.")
