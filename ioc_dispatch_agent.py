"""
PlaneSense IOC Dispatch Agent
==============================
An AI agent that automates routine Integrated Operations Center decisions
using Claude claude-sonnet-4-6 with tool use.

The agent receives a queue of 10 flight requests for December 20, 2025 —
a peak holiday demand day — and processes each one by:

  1. Checking weather on the route
  2. Verifying aircraft maintenance status (from the ML model)
  3. Finding available crew at the departure base
  4. Dispatching or escalating to a human dispatcher

Scenarios exercised:
  - Normal dispatch (weather clear, aircraft healthy, crew available)
  - Aircraft substitution (CRITICAL maintenance alert → swap to healthy tail)
  - Weather reroute (KPSM IFR conditions → 90-min delay)
  - Jetfly coordination (KPSM→EGLL→LSZH cross-border segment)
  - Human escalation (no PC-24 rated crew available)

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python ioc_dispatch_agent.py

  # Demo mode (no API key needed — uses scripted responses):
  python ioc_dispatch_agent.py --demo
"""

import argparse
import json
import os
import sys
import textwrap
import time
from datetime import datetime
from typing import Any

import anthropic
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IOC_DATA = os.path.join(BASE_DIR, "output", "ioc", "data")
MX_DATA  = os.path.join(BASE_DIR, "output", "predictive_maintenance", "data")
OUT_DIR  = os.path.join(BASE_DIR, "output", "ioc", "dispatch_log")
os.makedirs(OUT_DIR, exist_ok=True)

DEMO_DATE = "2025-12-20"

# ── Console colours ────────────────────────────────────────────────────────────
CLR = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "navy":    "\033[34m",
    "blue":    "\033[94m",
    "green":   "\033[92m",
    "yellow":  "\033[93m",
    "red":     "\033[91m",
    "cyan":    "\033[96m",
    "white":   "\033[97m",
    "dim":     "\033[2m",
}

def c(text, *codes):
    return "".join(CLR[k] for k in codes) + str(text) + CLR["reset"]

def hdr(text, width=70):
    print(f"\n{c('═'*width, 'navy')}")
    print(c(f"  {text}", "bold", "white"))
    print(c('═'*width, 'navy'))

def sub(text):
    print(c(f"\n  ── {text}", "cyan"))

def ok(text):
    print(c(f"    ✓ {text}", "green"))

def warn(text):
    print(c(f"    ⚠ {text}", "yellow"))

def err(text):
    print(c(f"    ✗ {text}", "red"))

def info(text):
    print(c(f"    → {text}", "dim"))

def tool_call(name, args_summary):
    print(c(f"    🔧 {name}({args_summary})", "blue"))


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADERS
# ══════════════════════════════════════════════════════════════════════════════

def _load():
    """Load all data tables once at startup."""
    return {
        "crew":     pd.read_csv(os.path.join(IOC_DATA, "crew_roster.csv")),
        "requests": pd.read_csv(os.path.join(IOC_DATA, "flight_requests.csv")),
        "weather":  pd.read_csv(os.path.join(IOC_DATA, "weather_events.csv")),
        "owners":   pd.read_csv(os.path.join(IOC_DATA, "owner_profiles.csv")),
        "aircraft": pd.read_csv(os.path.join(MX_DATA,  "aircraft_registry.csv")),
        "mx":       pd.read_csv(os.path.join(MX_DATA,  "ml_features.csv")),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# These are the "real" back-end functions the agent calls.
# ══════════════════════════════════════════════════════════════════════════════

DB: dict = {}   # populated in main()


def get_pending_flight_requests(date: str) -> dict:
    """Return all PENDING flight requests for a given date."""
    reqs = DB["requests"]
    pending = reqs[reqs["status"] == "PENDING"]
    return {
        "date": date,
        "count": len(pending),
        "requests": pending.to_dict("records"),
    }


def get_aircraft_maintenance_status(tail_number: str) -> dict:
    """Return maintenance risk for a specific aircraft (from ML model)."""
    mx = DB["mx"]
    ac = DB["aircraft"]

    ac_row = ac[ac["tail_number"] == tail_number]
    if ac_row.empty:
        return {"error": f"Aircraft {tail_number} not found"}

    mx_rows = mx[mx["tail_number"] == tail_number]
    critical = mx_rows[mx_rows["risk_tier"] == "CRITICAL"]
    high     = mx_rows[mx_rows["risk_tier"] == "HIGH"]

    alerts = []
    for _, row in critical.iterrows():
        alerts.append({
            "component":    row["component_name"],
            "risk_tier":    "CRITICAL",
            "wear_pct":     round(float(row["wear_pct_max"]), 1),
            "rul_hours":    round(float(row["remaining_useful_life_hours"]), 1),
            "action":       "GROUND — do not dispatch until component replaced",
        })
    for _, row in high.iterrows():
        alerts.append({
            "component":    row["component_name"],
            "risk_tier":    "HIGH",
            "wear_pct":     round(float(row["wear_pct_max"]), 1),
            "rul_hours":    round(float(row["remaining_useful_life_hours"]), 1),
            "action":       "Monitor — inspect before next flight",
        })

    ac_info = ac_row.iloc[0]
    return {
        "tail_number":   tail_number,
        "model":         ac_info["model"],
        "base":          ac_info["base_facility"],
        "status":        ac_info["status"],
        "total_hours":   round(float(ac_info["total_flight_hours"]), 0),
        "dispatch_safe": len(critical) == 0,
        "critical_count": len(critical),
        "high_count":    len(high),
        "alerts":        alerts[:4],   # top 4
    }


def get_available_aircraft(base: str, aircraft_type: str,
                           exclude_tails: list | None = None) -> dict:
    """Return aircraft at a base that are dispatch-safe."""
    ac  = DB["aircraft"]
    mx  = DB["mx"]
    exc = exclude_tails or []

    # Filter by base and model prefix and active status
    pool = ac[
        (ac["base_facility"] == base) &
        (ac["model"].str.startswith(aircraft_type.replace(" NGX","").replace("PC-12","PC-12").strip())) &
        (ac["status"] == "ACTIVE") &
        (~ac["tail_number"].isin(exc))
    ]

    results = []
    for _, row in pool.iterrows():
        tail = row["tail_number"]
        crit = mx[(mx["tail_number"] == tail) & (mx["risk_tier"] == "CRITICAL")]
        if crit.empty:
            results.append({
                "tail_number":  tail,
                "model":        row["model"],
                "total_hours":  round(float(row["total_flight_hours"]), 0),
                "dispatch_safe": True,
            })

    return {
        "base": base,
        "aircraft_type": aircraft_type,
        "available_count": len(results),
        "aircraft": results[:5],
    }


def get_available_crew(base: str, type_rating: str,
                       required_role: str = "Captain") -> dict:
    """Return available crew at a base with the given type rating."""
    crew = DB["crew"]
    avail = crew[
        (crew["base"] == base) &
        (crew["duty_status"] == "AVAILABLE") &
        (crew["type_ratings"].str.contains(type_rating))
    ]

    captains = avail[avail["role"] == "Captain"]
    fos      = avail[avail["role"] == "First Officer"]

    return {
        "base":            base,
        "type_rating":     type_rating,
        "captains_available": len(captains),
        "fos_available":   len(fos),
        "can_crew_flight": (len(captains) >= 1 and len(fos) >= 1),
        "suggested_captain":  captains.iloc[0]["pilot_name"] if len(captains) > 0 else None,
        "suggested_fo":       fos.iloc[0]["pilot_name"]      if len(fos) > 0 else None,
        "captain_id":         captains.iloc[0]["employee_id"] if len(captains) > 0 else None,
        "fo_id":              fos.iloc[0]["employee_id"]      if len(fos) > 0 else None,
    }


def check_weather(departure_icao: str, arrival_icao: str) -> dict:
    """Check weather advisories affecting a route."""
    wx   = DB["weather"]
    hits = []
    for _, row in wx.iterrows():
        airports = str(row["affects_airports"]).split(",")
        if departure_icao in airports or arrival_icao in airports:
            hits.append({
                "event_id":          row["event_id"],
                "type":              row["type"],
                "severity":          row["severity"],
                "description":       row["description"],
                "valid_to":          row["valid_to"],
                "recommended_action": row["recommended_action"],
            })
    return {
        "departure": departure_icao,
        "arrival":   arrival_icao,
        "advisories_count": len(hits),
        "clear_routing": len(hits) == 0,
        "advisories": hits,
    }


def check_jetfly_availability(departure_eu: str, arrival_eu: str,
                               date: str) -> dict:
    """Check Jetfly EU partner availability for cross-border segments."""
    # Simulated Jetfly response for demo
    jetfly_routes = {
        ("EGLL", "LSZH"): {"available": True,  "aircraft": "HB-FXX", "dep_time": "10:30"},
        ("EGLL", "LFPG"): {"available": True,  "aircraft": "HB-FYY", "dep_time": "11:00"},
        ("EHAM", "LSZH"): {"available": True,  "aircraft": "HB-FZZ", "dep_time": "09:45"},
        ("EGLL", "EDDB"): {"available": False, "aircraft": None,      "dep_time": None},
    }
    key = (departure_eu.upper(), arrival_eu.upper())
    route = jetfly_routes.get(key, {"available": False, "aircraft": None, "dep_time": None})
    return {
        "partner":        "Jetfly Aviation",
        "departure":      departure_eu,
        "arrival":        arrival_eu,
        "date":           date,
        "available":      route["available"],
        "aircraft_reg":   route["aircraft"],
        "estimated_dep":  route["dep_time"],
        "coordination_required": True,
        "lead_time_hours": 4,
        "note": ("Jetfly slot confirmed — coordination email required 4h prior"
                 if route["available"] else
                 "No Jetfly availability on this route — check CaptainJet alternative"),
    }


def dispatch_flight(request_id: str, tail_number: str,
                    captain_id: str, fo_id: str,
                    departure_time: str,
                    notes: str = "") -> dict:
    """Confirm dispatch of a flight with assigned crew and aircraft."""
    # Update request status in our in-memory dataframe
    DB["requests"].loc[DB["requests"]["request_id"] == request_id, "status"] = "DISPATCHED"

    # Mark crew as ON_TRIP
    DB["crew"].loc[DB["crew"]["employee_id"] == captain_id, "duty_status"] = "ON_TRIP"
    DB["crew"].loc[DB["crew"]["employee_id"] == fo_id,      "duty_status"] = "ON_TRIP"

    return {
        "status":       "DISPATCHED",
        "request_id":   request_id,
        "tail_number":  tail_number,
        "captain_id":   captain_id,
        "fo_id":        fo_id,
        "departure_time": departure_time,
        "dispatch_time":  datetime.now().strftime("%H:%M:%S"),
        "notes":        notes,
        "confirmation": f"DISP-{request_id}-{tail_number}",
    }


def escalate_to_human(request_id: str, reason: str,
                      priority: str = "NORMAL",
                      suggested_resolution: str = "") -> dict:
    """Escalate a flight request to a human dispatcher."""
    DB["requests"].loc[DB["requests"]["request_id"] == request_id, "status"] = "ESCALATED"
    return {
        "status":               "ESCALATED",
        "request_id":           request_id,
        "escalated_to":         "Senior Dispatcher on duty",
        "priority":             priority,
        "reason":               reason,
        "suggested_resolution": suggested_resolution,
        "escalation_id":        f"ESC-{request_id}-{int(time.time()) % 10000}",
        "timestamp":            datetime.now().strftime("%H:%M:%S"),
    }


def send_owner_notification(owner_id: str, message: str,
                            notification_type: str = "UPDATE") -> dict:
    """Send a status update to an owner via the app / SMS."""
    owners = DB["owners"]
    owner  = owners[owners["owner_id"] == owner_id]
    name   = owner.iloc[0]["owner_name"] if not owner.empty else owner_id
    return {
        "status":            "SENT",
        "owner_id":          owner_id,
        "owner_name":        name,
        "notification_type": notification_type,
        "message":           message,
        "channel":           "App + SMS",
        "timestamp":         datetime.now().strftime("%H:%M:%S"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY (Claude tool_use schema)
# ══════════════════════════════════════════════════════════════════════════════

TOOLS = [
    {
        "name": "get_pending_flight_requests",
        "description": "Get all PENDING flight requests in the IOC queue for a given date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"}
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_aircraft_maintenance_status",
        "description": (
            "Check the maintenance risk level for a specific aircraft tail number. "
            "Uses the predictive ML model output. Returns CRITICAL alerts that ground the aircraft."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tail_number": {"type": "string", "description": "Aircraft tail number e.g. N102AF"}
            },
            "required": ["tail_number"],
        },
    },
    {
        "name": "get_available_aircraft",
        "description": "Find dispatch-safe aircraft at a base. Returns tails with no CRITICAL maintenance alerts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "base":          {"type": "string", "description": "Base ICAO or facility code (PSM or BVU)"},
                "aircraft_type": {"type": "string", "description": "Aircraft type: PC-12 or PC-24"},
                "exclude_tails": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tail numbers already assigned or grounded",
                },
            },
            "required": ["base", "aircraft_type"],
        },
    },
    {
        "name": "get_available_crew",
        "description": "Find available crew at a base with the required type rating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "base":          {"type": "string", "description": "Base (PSM or BVU)"},
                "type_rating":   {"type": "string", "description": "Required type rating: PC-12 or PC-24"},
                "required_role": {"type": "string", "description": "Captain or First Officer", "default": "Captain"},
            },
            "required": ["base", "type_rating"],
        },
    },
    {
        "name": "check_weather",
        "description": "Check weather advisories (SIGMETs, PIREPs, NOTAMs) on a route.",
        "input_schema": {
            "type": "object",
            "properties": {
                "departure_icao": {"type": "string", "description": "Departure airport ICAO code"},
                "arrival_icao":   {"type": "string", "description": "Arrival airport ICAO code"},
            },
            "required": ["departure_icao", "arrival_icao"],
        },
    },
    {
        "name": "check_jetfly_availability",
        "description": "Check Jetfly EU partner availability for European flight segments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "departure_eu": {"type": "string", "description": "European departure airport ICAO"},
                "arrival_eu":   {"type": "string", "description": "European arrival airport ICAO"},
                "date":         {"type": "string", "description": "Flight date YYYY-MM-DD"},
            },
            "required": ["departure_eu", "arrival_eu", "date"],
        },
    },
    {
        "name": "dispatch_flight",
        "description": "Confirm and record dispatch of a flight with assigned crew and aircraft.",
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id":    {"type": "string"},
                "tail_number":   {"type": "string"},
                "captain_id":    {"type": "string"},
                "fo_id":         {"type": "string"},
                "departure_time":{"type": "string", "description": "Actual departure time HH:MM"},
                "notes":         {"type": "string", "description": "Any dispatch notes"},
            },
            "required": ["request_id", "tail_number", "captain_id", "fo_id", "departure_time"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate a request to a human dispatcher when the agent cannot resolve it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id":           {"type": "string"},
                "reason":               {"type": "string"},
                "priority":             {"type": "string", "enum": ["LOW","NORMAL","HIGH","URGENT"]},
                "suggested_resolution": {"type": "string"},
            },
            "required": ["request_id", "reason"],
        },
    },
    {
        "name": "send_owner_notification",
        "description": "Send a notification to an owner via the PlaneSense app and SMS.",
        "input_schema": {
            "type": "object",
            "properties": {
                "owner_id":          {"type": "string"},
                "message":           {"type": "string"},
                "notification_type": {
                    "type": "string",
                    "enum": ["CONFIRMATION","DELAY","UPDATE","REROUTE","ESCALATION"],
                },
            },
            "required": ["owner_id", "message"],
        },
    },
]

TOOL_FUNCTIONS = {
    "get_pending_flight_requests":    get_pending_flight_requests,
    "get_aircraft_maintenance_status": get_aircraft_maintenance_status,
    "get_available_aircraft":         get_available_aircraft,
    "get_available_crew":             get_available_crew,
    "check_weather":                  check_weather,
    "check_jetfly_availability":      check_jetfly_availability,
    "dispatch_flight":                dispatch_flight,
    "escalate_to_human":              escalate_to_human,
    "send_owner_notification":        send_owner_notification,
}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT LOOP
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are the PlaneSense IOC Dispatch AI — an intelligent operations agent
for PlaneSense, the largest US commercial Pilatus fleet operator (62 aircraft, 240+ pilots,
40+ bases, running 24/7).

Your job: process the flight request queue efficiently, dispatch every flight that can be
dispatched safely, and escalate only what genuinely requires human judgment.

Decision rules:
1. SAFETY FIRST — never dispatch an aircraft with a CRITICAL maintenance alert.
   If the preferred aircraft is grounded, find a substitute at the same base.
2. WEATHER — if a SIGMET or LOW_VIS advisory affects the departure airport,
   assess severity. IFR conditions at departure → delay 90 minutes and notify owner.
   PIREP light turbulence → dispatch with flight plan note, no owner notification needed.
3. CREW — always assign a Captain + First Officer with the correct type rating.
   If no rated crew is available at the base, escalate to human (HIGH priority).
4. JETFLY SEGMENTS — for requests involving European airports, check Jetfly availability
   for the EU leg. Coordinate the US leg (PlaneSense) + EU leg (Jetfly) separately.
5. ESCALATE ONLY when you cannot resolve: no substitute aircraft, no qualified crew,
   ambiguous safety situation, or owner VIP + multiple issues compounding.

For each request:
- Start with weather check, then aircraft, then crew.
- Use the most specific tools available.
- After dispatching, send the owner a concise confirmation notification.
- After escalating, suggest a resolution path for the human dispatcher.

Work through ALL 10 requests systematically. Be decisive. Show your reasoning briefly.
"""


def run_agent(client: anthropic.Anthropic) -> list[dict]:
    """Run the full agentic dispatch loop and return the dispatch log."""

    messages = [{"role": "user", "content":
        f"Good morning. Today is {DEMO_DATE}. Please process all pending flight "
        f"requests in the IOC queue. Start by retrieving the full queue, then "
        f"work through each request systematically: check weather, verify aircraft "
        f"maintenance, confirm crew availability, and dispatch or escalate. "
        f"After completing the queue, give me a summary of how many flights were "
        f"dispatched vs escalated and any patterns worth flagging for the IOC team."
    }]

    dispatch_log = []
    tool_call_count = 0

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Show any text the model produces
        for block in response.content:
            if hasattr(block, "text") and block.text.strip():
                wrapped = textwrap.fill(block.text.strip(), width=70,
                                        initial_indent="    ", subsequent_indent="    ")
                print(c(wrapped, "white"))

        # If no tool calls, we're done
        if response.stop_reason == "end_turn":
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name  = block.name
            tool_input = block.input
            tool_call_count += 1

            # Pretty-print the call
            args_str = ", ".join(f"{k}={repr(v)[:40]}" for k, v in tool_input.items())
            tool_call(tool_name, args_str)

            # Execute
            fn = TOOL_FUNCTIONS.get(tool_name)
            if fn is None:
                result = {"error": f"Unknown tool: {tool_name}"}
            else:
                result = fn(**tool_input)

            # Show key result lines
            if "dispatch_safe" in result:
                if result["dispatch_safe"]:
                    ok(f"Aircraft {result.get('tail_number','')} — dispatch safe "
                       f"({result['model']}, {result['total_hours']:.0f}h total)")
                else:
                    err(f"Aircraft {result.get('tail_number','')} — "
                        f"{result['critical_count']} CRITICAL alert(s): "
                        + "; ".join(a['component'] for a in result.get('alerts',[])))

            elif "clear_routing" in result:
                if result["clear_routing"]:
                    ok(f"Weather {result['departure']}→{result['arrival']}: CLEAR")
                else:
                    sev = result["advisories"][0]["severity"] if result["advisories"] else ""
                    warn(f"Weather {result['departure']}→{result['arrival']}: "
                         f"{result['advisories_count']} advisory ({sev}) — "
                         + result["advisories"][0].get("recommended_action","")[:60])

            elif "can_crew_flight" in result:
                if result["can_crew_flight"]:
                    ok(f"Crew {result['base']} {result['type_rating']}: "
                       f"{result['suggested_captain']} / {result['suggested_fo']}")
                else:
                    err(f"Crew {result['base']} {result['type_rating']}: "
                        f"{'no captain' if not result['captains_available'] else 'no FO'}")

            elif "status" in result:
                st = result["status"]
                rid = result.get("request_id","")
                if st == "DISPATCHED":
                    ok(f"DISPATCHED {rid} → {result['tail_number']} | "
                       f"Dep {result['departure_time']} | {result['confirmation']}")
                    dispatch_log.append({"request_id": rid, "outcome": "DISPATCHED",
                                         "tail": result["tail_number"],
                                         "dep_time": result["departure_time"]})
                elif st == "ESCALATED":
                    warn(f"ESCALATED {rid} [{result['priority']}]: {result['reason'][:60]}")
                    dispatch_log.append({"request_id": rid, "outcome": "ESCALATED",
                                         "reason": result["reason"]})
                elif st == "SENT":
                    info(f"Owner notified: {result['owner_name']} — {result['message'][:60]}")

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     json.dumps(result),
            })

        # Add model turn + tool results to history
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user",      "content": tool_results})

    print(c(f"\n  [Total tool calls: {tool_call_count}]", "dim"))
    return dispatch_log


# ══════════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════

def print_dispatch_report(log: list[dict]) -> None:
    dispatched = [r for r in log if r["outcome"] == "DISPATCHED"]
    escalated  = [r for r in log if r["outcome"] == "ESCALATED"]

    hdr("DISPATCH SUMMARY — December 20, 2025")
    total = len(DB["requests"])
    print(f"\n  {'Total requests:':<30} {total}")
    print(c(f"  {'Dispatched:':<30} {len(dispatched)}", "green"))
    print(c(f"  {'Escalated to human:':<30} {len(escalated)}", "yellow"))

    if dispatched:
        print(c("\n  Dispatched flights:", "bold"))
        for r in dispatched:
            print(f"    {r['request_id']}  →  {r['tail']}  dep {r.get('dep_time','')}")

    if escalated:
        print(c("\n  Escalations:", "bold"))
        for r in escalated:
            print(f"    {r['request_id']}  →  {r.get('reason','')[:65]}")

    # Save
    log_path = os.path.join(OUT_DIR, f"dispatch_log_{DEMO_DATE}.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(c(f"\n  Log saved → {os.path.relpath(log_path, BASE_DIR)}", "dim"))


# ══════════════════════════════════════════════════════════════════════════════
# DEMO MODE (no API key required — scripted agent replay)
# ══════════════════════════════════════════════════════════════════════════════

def _add_mins(time_str: str, minutes: int) -> str:
    """Add minutes to a HH:MM string."""
    h, m = map(int, time_str.split(":"))
    total = h * 60 + m + minutes
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


def run_demo() -> list[dict]:
    """
    Scripted demo — drives the real tool functions in a deterministic sequence.
    No API key required. Demonstrates all 5 dispatch scenarios:
      1. Normal dispatch (clear weather, healthy aircraft, crew available)
      2. Weather delay (IFR at KPSM → 90-min delay + owner notification)
      3. Aircraft maintenance check with CRITICAL → substitute
      4. Jetfly EU coordination (KPSM→EGLL→LSZH)
      5. Human escalation (no qualified crew available)
    """
    dispatch_log: list[dict] = []
    tool_count   = 0

    def _call(name: str, **kwargs) -> Any:
        nonlocal tool_count
        tool_count += 1
        args_str = ", ".join(f"{k}={repr(v)[:45]}" for k, v in kwargs.items())
        tool_call(name, args_str)
        result = TOOL_FUNCTIONS[name](**kwargs)
        return result

    # ── Load queue ─────────────────────────────────────────────────────────
    sub("Load IOC flight queue")
    queue = _call("get_pending_flight_requests", date=DEMO_DATE)
    ok(f"Queue loaded — {queue['count']} pending requests for {DEMO_DATE}")

    assigned_tails: list[str] = []   # aircraft already assigned this day

    # ── Process each request ───────────────────────────────────────────────
    for req in queue["requests"]:
        rid      = req["request_id"]
        dep      = req["departure_icao"]
        arr      = req["arrival_icao"]
        base     = "PSM" if "PSM" in dep else "BVU"
        ac_pref  = req["aircraft_preference"]
        req_time = req["requested_dep_time"].split(" ")[1]   # "HH:MM"
        owner_id = req["owner_id"]
        pax      = req["pax_count"]
        # Coerce NaN (pandas float) to empty string
        notes_raw = req.get("special_notes", "")
        notes_in  = str(notes_raw).strip() if isinstance(notes_raw, str) else ""
        priority  = req.get("priority", "NORMAL")

        sub(f"{rid}  {dep} → {arr}  "
            f"({ac_pref}, {pax} pax, {priority})  dep {req_time}")
        if notes_in:
            info(f"Notes: {notes_in}")

        # ── Step 1: Weather ─────────────────────────────────────────────
        wx = _call("check_weather", departure_icao=dep, arrival_icao=arr)

        weather_delay_min = 0
        wx_notes: list[str] = []
        for adv in wx.get("advisories", []):
            sev   = adv["severity"]
            etype = adv["type"]
            if sev == "LOW_VIS":
                weather_delay_min = max(weather_delay_min, 90)
                new_dep = _add_mins(req_time, weather_delay_min)
                wx_notes.append(f"IFR at {dep}: new departure {new_dep} (+90 min)")
            elif sev == "MODERATE":
                weather_delay_min = max(weather_delay_min, 120)
                new_dep = _add_mins(req_time, weather_delay_min)
                wx_notes.append(
                    f"MODERATE {etype}: new dep {new_dep} (+2h); file alternate, extra fuel")
            elif sev == "LIGHT":
                wx_notes.append("Light turbulence: plan cruise above FL200")
            elif sev == "INFO":
                wx_notes.append(
                    "KATL GDP in effect — advise owner of potential 45-min arrival delay")

        if weather_delay_min > 0:
            warn(f"{rid}: Weather delay {weather_delay_min} min → "
                 f"new dep {_add_mins(req_time, weather_delay_min)}")

        # ── Step 2: Jetfly EU coordination (RQ-009 KPSM→EGLL→LSZH) ────
        if rid == "RQ-009":
            jf = _call("check_jetfly_availability",
                       departure_eu="EGLL", arrival_eu="LSZH", date=DEMO_DATE)
            if jf["available"]:
                ok(f"Jetfly slot confirmed: EGLL→LSZH  |  {jf['aircraft_reg']}  "
                   f"dep {jf['estimated_dep']}  |  coordination email required 4h prior")
                wx_notes.append("Jetfly EGLL→LSZH leg confirmed — send coordination email by 12:00")
            else:
                warn("Jetfly EGLL→LSZH: no availability — check CaptainJet alternative")

        # ── Step 3: Aircraft maintenance check ──────────────────────────
        # For PC-24 requests at PSM show an explicit per-tail maintenance check
        # before calling get_available_aircraft — demonstrates the ML integration.
        if ac_pref == "PC-24" and base == "PSM":
            psm_pc24 = DB["aircraft"][
                (DB["aircraft"]["base_facility"] == "PSM") &
                (DB["aircraft"]["model"] == "PC-24") &
                (DB["aircraft"]["status"] == "ACTIVE") &
                (~DB["aircraft"]["tail_number"].isin(assigned_tails))
            ]
            if not psm_pc24.empty:
                check_tail = psm_pc24.iloc[0]["tail_number"]
                mx_status  = _call("get_aircraft_maintenance_status",
                                   tail_number=check_tail)
                if not mx_status["dispatch_safe"]:
                    warn(f"Aircraft {check_tail} has "
                         f"{mx_status['critical_count']} CRITICAL alert(s) — "
                         "finding substitute")
                    # Exclude grounded tail when searching for available aircraft
                    assigned_tails.append(check_tail)

        # ── Step 4: Find dispatch-safe aircraft ─────────────────────────
        ac_res = _call("get_available_aircraft",
                       base=base, aircraft_type=ac_pref,
                       exclude_tails=list(assigned_tails))

        if ac_res["available_count"] == 0:
            esc = _call("escalate_to_human",
                        request_id=rid,
                        reason=(f"No dispatch-safe {ac_pref} aircraft "
                                f"available at {base} base"),
                        priority="HIGH",
                        suggested_resolution=(
                            f"Check other bases for {ac_pref} ferry or "
                            "consider aircraft substitution with owner approval"))
            dispatch_log.append({"request_id": rid, "outcome": "ESCALATED",
                                  "reason": esc["reason"]})
            continue

        tail = ac_res["aircraft"][0]["tail_number"]

        # ── Step 5: Crew availability ────────────────────────────────────
        crew_res = _call("get_available_crew",
                         base=base, type_rating=ac_pref)

        if not crew_res["can_crew_flight"]:
            role_missing = ("captain" if crew_res["captains_available"] == 0
                            else "first officer")
            other_base   = "BVU" if base == "PSM" else "PSM"
            esc = _call("escalate_to_human",
                        request_id=rid,
                        reason=(f"No {ac_pref}-rated {role_missing} "
                                f"available at {base}"),
                        priority="HIGH",
                        suggested_resolution=(
                            f"Check {other_base} for crew repositioning; "
                            "activate standby reserve list"))
            dispatch_log.append({"request_id": rid, "outcome": "ESCALATED",
                                  "reason": esc["reason"]})
            continue

        # ── Step 6: Dispatch ─────────────────────────────────────────────
        h, m    = map(int, req_time.split(":"))
        dep_min = h * 60 + m + weather_delay_min
        actual_dep = f"{dep_min // 60 % 24:02d}:{dep_min % 60:02d}"

        dispatch_notes = "; ".join(filter(None,
                                          wx_notes + ([notes_in] if notes_in else [])))

        disp = _call("dispatch_flight",
                     request_id    = rid,
                     tail_number   = tail,
                     captain_id    = crew_res["captain_id"],
                     fo_id         = crew_res["fo_id"],
                     departure_time= actual_dep,
                     notes         = dispatch_notes)

        assigned_tails.append(tail)
        dispatch_log.append({"request_id": rid, "outcome": "DISPATCHED",
                              "tail": tail, "dep_time": actual_dep})

        # ── Step 7: Owner notification ───────────────────────────────────
        capt_name = crew_res["suggested_captain"] or "Captain TBD"
        fo_name   = crew_res["suggested_fo"]   or "FO TBD"
        if weather_delay_min > 0:
            notif_type = "DELAY"
            msg = (f"Your {ac_pref} flight {dep}→{arr} is confirmed with a "
                   f"{weather_delay_min}-min weather delay. New departure: "
                   f"{actual_dep}. Crew: {capt_name} / {fo_name}. "
                   f"Aircraft: {tail}.")
        else:
            notif_type = "CONFIRMATION"
            msg = (f"Your {ac_pref} flight {dep}→{arr} is confirmed for "
                   f"{actual_dep}. Crew: {capt_name} / {fo_name}. "
                   f"Aircraft: {tail}.")

        _call("send_owner_notification",
              owner_id=owner_id, message=msg,
              notification_type=notif_type)

    print(c(f"\n  [Total tool calls: {tool_count}]", "dim"))
    return dispatch_log


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true",
                        help="Run without API key (scripted tool-use replay)")
    args = parser.parse_args()

    # Load all data
    global DB
    DB = _load()

    hdr(f"PlaneSense IOC DISPATCH AGENT  |  {DEMO_DATE}", width=70)
    print(f"\n  Fleet         : {len(DB['aircraft'])} aircraft "
          f"({(DB['aircraft']['model']=='PC-12 NGX').sum()} PC-12 + "
          f"{(DB['aircraft']['model']=='PC-24').sum()} PC-24)")
    print(f"  Crew on duty  : {(DB['crew']['duty_status']=='AVAILABLE').sum()} available, "
          f"{(DB['crew']['duty_status']=='ON_REST').sum()} returning")

    # Count CRITICAL maintenance alerts
    mx_crit = DB["mx"][DB["mx"]["risk_tier"] == "CRITICAL"]["tail_number"].nunique()
    print(c(f"  ⚠  {mx_crit} aircraft with CRITICAL maintenance alerts — "
            f"will NOT be dispatched", "yellow"))

    print(f"  Pending queue : {(DB['requests']['status']=='PENDING').sum()} requests")
    print(f"  Weather alerts: {len(DB['weather'])} active advisories")

    if args.demo:
        print(c(f"\n  Mode: DEMO (scripted replay)  |  Tools: {len(TOOLS)}", "dim"))
        sub("Starting scripted dispatch replay…")
        log = run_demo()
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print(c("\n  ERROR: ANTHROPIC_API_KEY not set.", "red"))
            print(c("  Set the env var, or use --demo for a scripted replay.", "dim"))
            sys.exit(1)
        print(c(f"\n  Model: claude-sonnet-4-6  |  Tools: {len(TOOLS)}", "dim"))
        sub("Starting agentic dispatch loop…")
        client = anthropic.Anthropic(api_key=api_key)
        try:
            log = run_agent(client)
        except anthropic.AuthenticationError:
            print(c("\n  Invalid API key. Set ANTHROPIC_API_KEY correctly.", "red"))
            sys.exit(1)

    print_dispatch_report(log)


if __name__ == "__main__":
    main()
