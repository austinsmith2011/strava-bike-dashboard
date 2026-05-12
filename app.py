from __future__ import annotations

import json
import os
import time
from datetime import datetime, date, timedelta
from pathlib import Path

import anthropic
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501")
AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
API_BASE = "https://www.strava.com/api/v3"

TOKENS_FILE = Path(__file__).parent / ".tokens.json"
PERSIST_TOKENS = os.getenv("PERSIST_TOKENS", "true").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

METERS_PER_MILE = 1609.34
FEET_PER_METER = 3.28084

ACCENT_COLORS = ["#7c5cfc", "#00d4aa", "#f59e42", "#38bdf8", "#fb7185", "#a78bfa"]

TIME_PRESETS = [
    "Last 3 months",
    "Last 6 months",
    "Last 12 months",
    "Year to date",
    "All time",
    "Custom range",
]


def resolve_time_preset(label: str) -> tuple[date, date]:
    today = date.today()
    mapping = {
        "Last 3 months": 90,
        "Last 6 months": 180,
        "Last 12 months": 365,
    }
    if label in mapping:
        return today - timedelta(days=mapping[label]), today
    if label == "Year to date":
        return date(today.year, 1, 1), today
    return date(2000, 1, 1), today


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700;9..40,800&display=swap');

/* ── Design tokens ── */
:root {
    --bg-base: #060918;
    --bg-glass: rgba(255, 255, 255, 0.04);
    --bg-glass-hover: rgba(255, 255, 255, 0.07);
    --border-glass: rgba(255, 255, 255, 0.07);
    --border-glass-hover: rgba(255, 255, 255, 0.14);
    --text-primary: #e8eaf0;
    --text-secondary: #8b92a5;
    --text-muted: #515972;
    --accent: #7c5cfc;
    --accent-glow: rgba(124, 92, 252, 0.35);
    --radius-lg: 16px;
    --radius-md: 12px;
    --radius-sm: 8px;
    --glass-blur: 12px;
    --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

html, body, [class*="st-"]:not([class*="material"]):not([data-testid*="Icon"]) {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}
span[class*="material"] {
    font-family: 'Material Symbols Rounded' !important;
}

#MainMenu, header, footer { visibility: hidden; }
.stDeployButton { display: none; }
[data-testid="manage-app-button"] { display: none !important; }
button[title*="keyboard"], [data-testid*="keyboard"],
[class*="StatusWidget"], [data-testid="stStatusWidget"] {
    display: none !important;
}

/* ── Background with ambient gradient orbs ── */
.stApp {
    background: var(--bg-base);
}
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 60% 50% at 15% 20%, rgba(124, 92, 252, 0.12) 0%, transparent 70%),
        radial-gradient(ellipse 50% 60% at 85% 75%, rgba(56, 189, 248, 0.08) 0%, transparent 70%),
        radial-gradient(ellipse 40% 40% at 50% 50%, rgba(0, 212, 170, 0.05) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}
.stApp > * { position: relative; z-index: 1; }

section[data-testid="stSidebar"] { display: none; }

/* ── Chat input sticks to bottom of sidebar ── */
section[data-testid="stSidebar"] [data-testid="stChatInput"] {
    position: sticky !important;
    bottom: 0 !important;
    z-index: 10 !important;
    background: linear-gradient(180deg, transparent 0%, #080716 30%) !important;
    margin-top: auto !important;
    padding: 12px 0 !important;
    border-top: 1px solid rgba(124, 92, 252, 0.08);
}

/* ── Toolbar ── */
div[data-testid="stSelectbox"] label {
    color: var(--text-secondary) !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600 !important;
}

/* ── KPI cards ── */
.kpi-card {
    background: var(--bg-glass);
    backdrop-filter: blur(var(--glass-blur));
    -webkit-backdrop-filter: blur(var(--glass-blur));
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-md);
    padding: 22px 24px;
    text-align: center;
    box-shadow: var(--glass-shadow);
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.kpi-card:hover {
    border-color: var(--border-glass-hover);
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    color: var(--text-primary);
    margin: 0;
    line-height: 1.2;
}
.kpi-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    font-weight: 600;
    margin-top: 6px;
    margin-bottom: 2px;
}
.kpi-sub {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-weight: 500;
    margin: 0;
}
.kpi-unit {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--text-secondary);
    margin-left: 3px;
}

/* ── Bike cards (glass) ── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bg-glass) !important;
    backdrop-filter: blur(var(--glass-blur)) !important;
    -webkit-backdrop-filter: blur(var(--glass-blur)) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--glass-shadow) !important;
    transition: border-color 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--border-glass-hover) !important;
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5) !important;
}
.bike-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
}
.bike-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
}
.bike-rides {
    font-size: 0.72rem;
    color: var(--text-secondary);
    font-weight: 500;
    background: rgba(255, 255, 255, 0.06);
    padding: 3px 10px;
    border-radius: 99rem;
    margin-left: auto;
    border: 1px solid rgba(255, 255, 255, 0.04);
}
.accent-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}

/* ── Metric boxes inside cards ── */
.metric-row {
    display: flex;
    gap: 10px;
}
.metric-box {
    flex: 1;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: var(--radius-sm);
    padding: 14px 14px;
}
.metric-label {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    font-weight: 600;
    margin-bottom: 6px;
}
.metric-value {
    font-size: 1.35rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.2;
}
.metric-unit {
    font-size: 0.65rem;
    font-weight: 500;
    color: var(--text-secondary);
    margin-left: 3px;
}

/* ── Header ── */
.dash-title {
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--text-primary);
    margin: 0;
    line-height: 1.3;
}
.dash-subtitle {
    color: var(--text-secondary);
    font-size: 0.82rem;
    margin: 0;
}

/* ── Login page ── */
.login-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    text-align: center;
}
.login-title {
    font-size: 2.6rem;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 8px;
}
.login-subtitle {
    color: var(--text-secondary);
    font-size: 1rem;
    margin-bottom: 36px;
}
.strava-btn {
    display: inline-block;
    padding: 14px 36px;
    background: linear-gradient(135deg, #fc4c02, #ff6a33);
    color: white !important;
    border-radius: var(--radius-sm);
    text-decoration: none;
    font-weight: 700;
    font-size: 1.05rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 4px 20px rgba(252, 76, 2, 0.3);
}
.strava-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 28px rgba(252, 76, 2, 0.45);
    color: white !important;
}

.setup-warning {
    background: rgba(245, 158, 66, 0.06);
    border: 1px solid rgba(245, 158, 66, 0.2);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    color: #f59e42;
    font-size: 0.9rem;
    line-height: 1.5;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}

/* ── Toolbar button overrides ── */
button[kind="secondary"] {
    border: 1px solid var(--border-glass) !important;
    background: var(--bg-glass) !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
    padding: 6px 10px !important;
    min-height: 0 !important;
    height: 36px !important;
    transition: all 0.25s ease !important;
}
button[kind="secondary"]:hover {
    border-color: var(--border-glass-hover) !important;
    background: var(--bg-glass-hover) !important;
    color: var(--text-primary) !important;
    box-shadow: 0 0 16px rgba(124, 92, 252, 0.15) !important;
}
button[kind="secondary"] span[data-testid="stIconMaterial"] {
    font-size: 18px !important;
}

/* ── View-rides link button ── */
.view-rides-btn button {
    background: none !important;
    border: none !important;
    color: var(--text-secondary) !important;
    font-size: 0.76rem !important;
    padding: 0 !important;
    font-weight: 500 !important;
    min-height: 0 !important;
    height: auto !important;
    transition: color 0.2s ease !important;
}
.view-rides-btn button:hover {
    color: var(--accent) !important;
    background: none !important;
    border: none !important;
}

/* ── Right-side drawer (glass) ── */
div[data-testid="stDialog"] > div {
    position: fixed !important;
    top: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    left: auto !important;
    width: 520px !important;
    max-width: 90vw !important;
    height: 100vh !important;
    max-height: 100vh !important;
    margin: 0 !important;
    border-radius: 0 !important;
    transform: none !important;
    background: rgba(8, 10, 28, 0.85) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border-left: 1px solid var(--border-glass);
    overflow-y: auto;
}

/* ── Ride list inside drawer ── */
.ride-list {
    display: flex;
    flex-direction: column;
}
.ride-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.ride-row:last-child { border-bottom: none; }
.ride-info {
    flex: 1;
    min-width: 0;
}
.ride-name {
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 3px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ride-date {
    font-size: 0.72rem;
    color: var(--text-secondary);
    margin: 0;
}
.ride-stats {
    display: flex;
    gap: 20px;
    flex-shrink: 0;
}
.ride-stat {
    text-align: right;
}
.ride-stat-value {
    font-size: 0.88rem;
    font-weight: 700;
    color: #c0c5d0;
    margin: 0;
    line-height: 1.2;
}
.ride-stat-label {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    margin: 0;
}
.ride-link {
    flex-shrink: 0;
    text-decoration: none;
    color: var(--text-secondary);
    font-size: 0.85rem;
    padding: 6px;
    border-radius: 4px;
    transition: color 0.2s ease;
}
.ride-link:hover {
    color: var(--accent);
}
.dialog-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
}
.dialog-bike-name {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
}
.dialog-ride-count {
    font-size: 0.75rem;
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.06);
    padding: 3px 10px;
    border-radius: 99rem;
    border: 1px solid rgba(255, 255, 255, 0.04);
}
.dialog-sort-note {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin: 0 0 12px 0;
}

/* ── Dataframe styling ── */
div[data-testid="stDataFrame"] {
    border-radius: var(--radius-md) !important;
    overflow: hidden;
}

</style>
"""

CHAT_OPEN_CSS = """
<style>
section[data-testid="stSidebar"] {
    display: flex !important;
    visibility: visible !important;
    width: 420px !important;
    min-width: 420px !important;
    transform: none !important;
    margin-left: 0 !important;
    background: linear-gradient(165deg, #0a0820 0%, #0d0b1f 40%, #080716 100%) !important;
    border-right: 1px solid rgba(124, 92, 252, 0.1);
}
section[data-testid="stSidebar"]::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 40% at 20% 80%, rgba(124, 92, 252, 0.08) 0%, transparent 70%),
        radial-gradient(ellipse 60% 50% at 80% 20%, rgba(56, 189, 248, 0.05) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}
section[data-testid="stSidebar"] > div:first-child {
    width: 420px !important;
    background: transparent !important;
    position: relative;
    z-index: 1;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    background: transparent !important;
    padding-top: 16px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarCollapsedControl"],
section[data-testid="stSidebar"] button[kind="header"],
section[data-testid="stSidebar"] [data-testid="collapsedControl"],
section[data-testid="stSidebar"] button[title="Close sidebar"],
section[data-testid="stSidebar"] [class*="closeButton"] {
    display: none !important;
    pointer-events: none !important;
}
section[data-testid="stSidebar"] [data-testid="stToolbar"],
section[data-testid="stSidebar"] [data-testid="stSidebarNav"],
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
    display: none !important;
}
</style>
"""

CHAT_UNCOLLAPSE_JS = """
<script>
// Force sidebar expanded in Streamlit's localStorage state
try {
    const keys = Object.keys(localStorage);
    for (const k of keys) {
        if (k.includes('sidebarState') || k.includes('sidebar')) {
            localStorage.removeItem(k);
        }
    }
} catch(e) {}
</script>
"""

CLAUDE_TOOLS = [
    {
        "name": "set_time_range",
        "description": (
            "Change the dashboard time filter. Use a preset name OR custom start/end dates. "
            "Presets: 'Last 3 months', 'Last 6 months', 'Last 12 months', 'Year to date', 'All time'. "
            "For custom ranges, provide both start_date and end_date as YYYY-MM-DD strings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "preset": {
                    "type": "string",
                    "description": "One of the preset names, or 'Custom range' if using dates.",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date as YYYY-MM-DD (only with 'Custom range').",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date as YYYY-MM-DD (only with 'Custom range').",
                },
            },
            "required": ["preset"],
        },
    }
]


# ---------------------------------------------------------------------------
# Chat helpers
# ---------------------------------------------------------------------------

def build_chat_context(
    athlete: dict,
    bikes: dict[str, str],
    selected_preset: str,
    start_date: date,
    end_date: date,
    activities: list[dict],
) -> str:
    first = athlete.get("firstname", "")
    last = athlete.get("lastname", "")

    total_dist = meters_to_miles(sum(a.get("distance", 0) for a in activities))
    total_elev = meters_to_feet(sum(a.get("total_elevation_gain", 0) for a in activities))
    total_time = sum(a.get("moving_time", 0) for a in activities)
    n = max(len(activities), 1)

    has_power = any(a.get("average_watts") for a in activities)
    has_hr = any(a.get("has_heartrate") for a in activities)

    bike_groups: dict[str, list[dict]] = {bid: [] for bid in bikes}
    for a in activities:
        gid = a.get("gear_id")
        if gid and gid in bike_groups:
            bike_groups[gid].append(a)

    bike_lines = []
    for bid, bname in bikes.items():
        ba = bike_groups.get(bid, [])
        bd = meters_to_miles(sum(a.get("distance", 0) for a in ba))
        be = meters_to_feet(sum(a.get("total_elevation_gain", 0) for a in ba))
        bt = sum(a.get("moving_time", 0) for a in ba)
        bike_lines.append(f"  - {bname}: {len(ba)} rides, {bd:,.1f} mi, {be:,.0f} ft elev, {seconds_to_hm(bt)}")

    sorted_acts = sorted(activities, key=lambda a: a.get("start_date_local", ""), reverse=True)
    ride_rows = []
    for a in sorted_acts:
        raw_date = a.get("start_date_local", a.get("start_date", ""))[:10]
        name = a.get("name", "Untitled")
        gear_id = a.get("gear_id", "")
        bname = bikes.get(gear_id, "Unknown")
        dist = meters_to_miles(a.get("distance", 0))
        elev = meters_to_feet(a.get("total_elevation_gain", 0))
        mt = a.get("moving_time", 0) // 60
        avg_spd = a.get("average_speed", 0) * 2.23694
        kj = a.get("kilojoules")
        suffer = a.get("suffer_score")

        parts = [
            raw_date, name, bname,
            f"{dist:.1f}mi", f"{elev:.0f}ft", f"{mt}min",
            f"{avg_spd:.1f}mph",
        ]
        if kj:
            parts.append(f"{int(kj)}kJ")
        if a.get("average_watts"):
            parts.append(f"{int(a['average_watts'])}w avg")
        if a.get("weighted_average_watts"):
            parts.append(f"{int(a['weighted_average_watts'])}w NP")
        if a.get("average_heartrate"):
            parts.append(f"{int(a['average_heartrate'])}bpm avg")
        if a.get("max_heartrate"):
            parts.append(f"{int(a['max_heartrate'])}bpm max")
        if suffer:
            parts.append(f"suffer:{int(suffer)}")

        ride_rows.append(" | ".join(parts))

    rides_table = "\n".join(ride_rows) if ride_rows else "(no rides)"

    data_notes = [
        "Primary metrics: duration, distance, elevation, average speed. Always lean on these first."
    ]
    if has_power:
        data_notes.append("Power data IS available for some rides. Use it for TSS/CTL/ATL/TSB analysis where present — it's the best intensity signal when you have it.")
    else:
        data_notes.append("No power data available. Estimate load from duration, distance, elevation, and speed.")
    if has_hr:
        data_notes.append("Heart rate data IS available for some rides. Treat it as a secondary/supporting metric — useful for spotting fatigue trends or confirming intensity, but don't center your analysis on it.")
    else:
        data_notes.append("No heart rate data available.")

    return f"""You are an expert cycling coach with deep knowledge of exercise physiology, periodization, and race preparation. You have access to {first}'s Strava data. Your job is to answer questions about training, recovery, and race readiness using that data as evidence — not decoration.

## How to behave

- Be direct. Answer the question first, then explain your reasoning if needed.
- Talk like a knowledgeable coach sitting across the table, not like a sports science textbook or a motivational poster.
- No hype, no cheerleading, no "great job getting out there." The rider doesn't want encouragement. They want accurate, useful feedback.
- If the data doesn't support a clear answer, say so. Don't hedge everything — but don't fake certainty either.

## How to use the data

You will receive structured Strava activity data below.

**Do not summarize every ride.** The rider already knows what they did. Instead:

- Reference specific rides only when they matter to the answer (e.g., "That 3-hour ride on Saturday with 4,000ft of climbing — that's a big load to drop in right before a taper").
- Default to weekly or multi-day blocks when discussing load and volume (e.g., "You averaged about 8 hours/week the last three weeks, which is up from your usual 6").
- Use totals, trends, and patterns. Not play-by-play recaps.

If the rider asks about a specific ride, then go into detail on that ride. Otherwise, keep it high-level.

## What you know

Ground your advice in established, well-supported training principles:

- **Periodization**: Base → build → peak → taper. Understand where the rider is in a cycle and what kind of work makes sense right now.
- **Supercompensation and recovery**: Training stress requires recovery to produce adaptation. More is not always better. Be specific about recovery timelines (e.g., "After a block like that, you probably need 2-3 easy days before you'll feel good again").
- **Intensity distribution**: Polarized and pyramidal models. Most volume should be easy. Hard days should be hard. Avoid the middle gray zone unless there's a reason.
- **Tapering**: For a target event, reduce volume 40-60% while keeping some intensity. Timing depends on the event and the rider's recent load.
- **Energy systems**: Know when to recommend VO2max intervals vs. threshold work vs. endurance rides vs. sprint work, and why. Tie recommendations to the demands of the target event.
- **TSS / training load** (if power data is available): Use CTL, ATL, and TSB concepts to inform readiness assessments. If power data isn't available, estimate load from duration, elevation, and speed. Heart rate is a useful secondary signal for confirming intensity or spotting fatigue, but don't build your analysis around it.
- **Fatigue signatures**: Recognize when data suggests accumulated fatigue — declining power at similar effort levels, shorter ride durations, increased rest days, drops in average speed on similar routes, etc.

If the rider asks about something outside your expertise (nutrition, bike fit, injury diagnosis), say so clearly. You can offer general guidance but flag that it's not your lane.

## Response style

- Keep answers concise. A few short paragraphs is usually enough.
- Use numbers when they help (hours, TSS, watts, percentages) but don't drown the rider in metrics.
- If you're making an assumption (e.g., estimating intensity from heart rate because there's no power data), call it out briefly.
- When recommending workouts, be specific: "Do 4x8min at threshold with 4min recovery" is better than "do some threshold work."
- If the rider asks a broad question ("How's my training going?"), pick the 2-3 most important observations and lead with those. Don't try to cover everything.

## Tools

- If the user asks to change the time window or see different data, use the set_time_range tool.

---

## RIDER DATA

DASHBOARD FILTER: {selected_preset} ({start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')})

ATHLETE: {first} {last}

DATA AVAILABILITY:
{chr(10).join('  ' + n for n in data_notes)}

BIKES:
{chr(10).join(bike_lines) if bike_lines else '  (none)'}

PERIOD TOTALS ({len(activities)} rides):
  Distance: {total_dist:,.1f} mi (avg {total_dist / n:,.1f} mi/ride)
  Elevation: {total_elev:,.0f} ft (avg {total_elev / n:,.0f} ft/ride)
  Time: {seconds_to_hm(total_time)} (avg {total_time / n / 60:,.0f} min/ride)

RIDE LOG (most recent first):
{rides_table}"""


def handle_tool_call(tool_name: str, tool_input: dict) -> str | None:
    if tool_name == "set_time_range":
        preset = tool_input.get("preset", "")
        valid_presets = [p for p in TIME_PRESETS if p != "Custom range"]
        if preset in valid_presets:
            st.session_state["chat_filter_preset"] = preset
            return f"Changed dashboard filter to **{preset}**."
        elif preset == "Custom range":
            sd = tool_input.get("start_date")
            ed = tool_input.get("end_date")
            if sd and ed:
                try:
                    parsed_start = datetime.strptime(sd, "%Y-%m-%d").date()
                    parsed_end = datetime.strptime(ed, "%Y-%m-%d").date()
                    st.session_state["chat_filter_preset"] = "Custom range"
                    st.session_state["_chat_custom_start"] = parsed_start
                    st.session_state["_chat_custom_end"] = parsed_end
                    return f"Changed dashboard filter to **{sd} – {ed}**."
                except ValueError:
                    return None
            return None
        return None
    return None


# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------

def build_auth_url() -> str:
    return (
        f"{AUTH_URL}?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=read_all,activity:read_all,profile:read_all"
        f"&approval_prompt=force"
    )


def exchange_code_for_token(code: str) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()


def get_valid_token() -> str | None:
    if "access_token" not in st.session_state:
        _load_tokens_from_disk()
    if "access_token" not in st.session_state:
        return None
    if time.time() >= st.session_state.get("expires_at", 0):
        data = refresh_access_token(st.session_state["refresh_token"])
        _store_tokens(data)
    return st.session_state["access_token"]


def _store_tokens(data: dict):
    st.session_state["access_token"] = data["access_token"]
    st.session_state["refresh_token"] = data["refresh_token"]
    st.session_state["expires_at"] = data["expires_at"]
    if PERSIST_TOKENS:
        TOKENS_FILE.write_text(json.dumps({
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data["expires_at"],
        }))


def _load_tokens_from_disk():
    if not PERSIST_TOKENS or not TOKENS_FILE.exists():
        return
    try:
        data = json.loads(TOKENS_FILE.read_text())
        st.session_state["access_token"] = data["access_token"]
        st.session_state["refresh_token"] = data["refresh_token"]
        st.session_state["expires_at"] = data["expires_at"]
    except (json.JSONDecodeError, KeyError):
        pass


# ---------------------------------------------------------------------------
# Strava API helpers
# ---------------------------------------------------------------------------

def get_athlete(token: str) -> dict:
    resp = requests.get(f"{API_BASE}/athlete", headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()


def get_all_activities(token: str, after: int | None = None, before: int | None = None) -> list[dict]:
    activities: list[dict] = []
    page = 1
    while True:
        params: dict = {"per_page": 200, "page": page}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before
        resp = requests.get(
            f"{API_BASE}/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        resp.raise_for_status()
        batch = resp.json()
        rides = [a for a in batch if a.get("type") == "Ride"]
        activities.extend(rides)
        if len(batch) < 200:
            break
        page += 1
    return activities


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def meters_to_miles(m: float) -> float:
    return m / METERS_PER_MILE


def meters_to_feet(m: float) -> float:
    return m * FEET_PER_METER


def seconds_to_hm(s: int) -> str:
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h}h {m}m"


# ---------------------------------------------------------------------------
# Ride detail dialog
# ---------------------------------------------------------------------------

@st.dialog("Rides", width="large")
def show_rides_dialog(bike_name: str, acts: list[dict], accent: str):
    sorted_acts = sorted(acts, key=lambda a: a.get("moving_time", 0), reverse=True)
    cnt = len(sorted_acts)
    ride_label = "ride" if cnt == 1 else "rides"

    st.markdown(
        f'<div class="dialog-header">'
        f'<span class="accent-dot" style="background:{accent};box-shadow:0 0 8px {accent};"></span>'
        f'<p class="dialog-bike-name">{bike_name}</p>'
        f'<span class="dialog-ride-count">{cnt} {ride_label}</span>'
        f'</div>'
        f'<p class="dialog-sort-note">Sorted by longest ride first</p>',
        unsafe_allow_html=True,
    )

    rows = []
    for a in sorted_acts:
        name = a.get("name", "Untitled")
        act_id = a.get("id", "")
        dist = meters_to_miles(a.get("distance", 0))
        elev = meters_to_feet(a.get("total_elevation_gain", 0))
        mt = a.get("moving_time", 0)
        raw_date = a.get("start_date_local", a.get("start_date", ""))
        try:
            dt = datetime.strptime(raw_date[:10], "%Y-%m-%d").strftime("%b %d, %Y")
        except (ValueError, TypeError):
            dt = ""
        strava_url = f"https://www.strava.com/activities/{act_id}"

        rows.append(
            f'<div class="ride-row">'
            f'<div class="ride-info">'
            f'<p class="ride-name">{name}</p>'
            f'<p class="ride-date">{dt}</p>'
            f'</div>'
            f'<div class="ride-stats">'
            f'<div class="ride-stat"><p class="ride-stat-value">{dist:,.1f} mi</p>'
            f'<p class="ride-stat-label">Distance</p></div>'
            f'<div class="ride-stat"><p class="ride-stat-value">{elev:,.0f} ft</p>'
            f'<p class="ride-stat-label">Elevation</p></div>'
            f'<div class="ride-stat"><p class="ride-stat-value">{seconds_to_hm(mt)}</p>'
            f'<p class="ride-stat-label">Time</p></div>'
            f'</div>'
            f'<a class="ride-link" href="{strava_url}" target="_blank" title="Open in Strava">↗</a>'
            f'</div>'
        )

    st.markdown(f'<div class="ride-list">{"".join(rows)}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chat sidebar
# ---------------------------------------------------------------------------

def _render_chat_sidebar(
    athlete: dict,
    bikes: dict[str, str],
    selected_preset: str,
    start_date: date,
    end_date: date,
    activities: list[dict],
):
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    with st.sidebar:
        hdr1, hdr2 = st.columns([6, 1])
        with hdr1:
            st.markdown("**AI Coach** `Beta`")
        with hdr2:
            if st.button("", icon=":material/close:", key="chat_close", use_container_width=True):
                st.session_state["chat_open"] = False
                st.rerun()

        messages = st.session_state["chat_messages"]

        if not messages:
            st.caption(
                "Ask anything about your rides. Try:\n\n"
                "*\"Based on my last 3 weeks, how much rest do I need "
                "before Tuesday's group ride?\"*"
            )

        for msg in messages:
            if msg["role"] == "filter_applied":
                st.info(msg["content"])
            else:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("Message AI Coach...", key="chat_input"):
            if not ANTHROPIC_API_KEY:
                st.error("Set ANTHROPIC_API_KEY in your .env file to use AI Coach.")
                return

            messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            system_prompt = build_chat_context(
                athlete, bikes, selected_preset, start_date, end_date, activities
            )

            api_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in messages
                if m["role"] in ("user", "assistant")
            ]

            with st.chat_message("assistant"):
                stream_placeholder = st.empty()
                result = _stream_claude_response(system_prompt, api_messages, stream_placeholder)

            if result is not None:
                response_text = result.get("text", "")
                tool_result = result.get("tool_result")

                if tool_result:
                    messages.append({"role": "filter_applied", "content": tool_result["display"]})
                    st.info(tool_result["display"])

                    if response_text:
                        messages.append({"role": "assistant", "content": response_text})

                    with st.chat_message("assistant"):
                        followup_placeholder = st.empty()
                        follow_up = _get_tool_followup(
                            system_prompt, api_messages, result["raw_response"],
                            tool_result, followup_placeholder,
                        )
                    if follow_up:
                        messages.append({"role": "assistant", "content": follow_up})
                elif response_text:
                    messages.append({"role": "assistant", "content": response_text})

            st.rerun()


def _stream_claude_response(
    system_prompt: str, api_messages: list[dict], container
) -> dict | None:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response_text = ""
        tool_result = None
        raw_content = []

        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=api_messages,
            tools=CLAUDE_TOOLS,
        ) as stream:
            tool_use_block = None
            for event in stream:
                if not hasattr(event, "type"):
                    continue
                if event.type == "content_block_start":
                    if hasattr(event.content_block, "type"):
                        if event.content_block.type == "tool_use":
                            tool_use_block = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input_json": "",
                            }
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        response_text += event.delta.text
                        container.markdown(response_text + "▌")
                    elif hasattr(event.delta, "partial_json"):
                        if tool_use_block is not None:
                            tool_use_block["input_json"] += event.delta.partial_json
                elif event.type == "content_block_stop":
                    if tool_use_block is not None:
                        try:
                            tool_input = json.loads(tool_use_block["input_json"])
                        except json.JSONDecodeError:
                            tool_input = {}
                        display = handle_tool_call(tool_use_block["name"], tool_input)
                        if display:
                            tool_result = {
                                "tool_use_id": tool_use_block["id"],
                                "display": display,
                            }
                        raw_content.append({
                            "type": "tool_use",
                            "id": tool_use_block["id"],
                            "name": tool_use_block["name"],
                            "input": tool_input,
                        })
                        tool_use_block = None

        if response_text:
            raw_content.insert(0, {"type": "text", "text": response_text})

        container.empty()
        return {
            "text": response_text,
            "tool_result": tool_result,
            "raw_response": raw_content,
        }

    except anthropic.APIError as e:
        container.error(f"API error: {e.message}")
        return None
    except Exception as e:
        container.error(f"Error: {e}")
        return None


def _get_tool_followup(
    system_prompt: str,
    original_messages: list[dict],
    assistant_content: list[dict],
    tool_result: dict,
    container,
) -> str | None:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        messages = original_messages + [
            {"role": "assistant", "content": assistant_content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_result["tool_use_id"],
                        "content": tool_result["display"],
                    }
                ],
            },
        ]

        response_text = ""
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=CLAUDE_TOOLS,
        ) as stream:
            for event in stream:
                if not hasattr(event, "type"):
                    continue
                if event.type == "content_block_delta" and hasattr(event.delta, "text"):
                    response_text += event.delta.text
                    container.markdown(response_text + "▌")

        container.empty()
        return response_text if response_text else None

    except Exception:
        container.empty()
        return None


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# List View
# ---------------------------------------------------------------------------

def _render_list_view(activities, bikes):
    from datetime import datetime
    import pandas as pd

    sorted_acts = sorted(
        activities,
        key=lambda a: a.get("start_date_local", ""),
        reverse=True,
    )

    rows = []
    for a in sorted_acts:
        dt = datetime.fromisoformat(a.get("start_date_local", "")[:19])
        moving = a.get("moving_time", 0)
        hrs, rem = divmod(moving, 3600)
        mins = rem // 60
        time_str = f"{hrs}h {mins:02d}m" if hrs else f"{mins}m"

        dist_mi = a.get("distance", 0) / 1609.34
        elev_ft = a.get("total_elevation_gain", 0) * 3.28084
        avg_speed_mph = a.get("average_speed", 0) * 2.23694
        kj = a.get("kilojoules")

        gear_id = a.get("gear_id")
        bike_name = bikes.get(gear_id, "--") if gear_id else "--"

        rows.append({
            "Date": dt.strftime("%b %-d, %Y"),
            "Name": a.get("name", ""),
            "Bike": bike_name,
            "Distance (mi)": round(dist_mi, 1),
            "Elevation (ft)": int(round(elev_ft)),
            "Time": time_str,
            "Avg Speed (mph)": round(avg_speed_mph, 1) if avg_speed_mph else "--",
            "Kilojoules": int(round(kj)) if kj else "--",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# Pages
# ---------------------------------------------------------------------------

def show_login():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if not CLIENT_ID or CLIENT_ID == "your_client_id_here":
        st.markdown(
            '<div class="login-container">'
            '<p class="login-title">Strava Bike Dashboard</p>'
            '<div class="setup-warning"><strong>Setup required</strong><br>'
            'Open the <code>.env</code> file and add your Strava Client ID and Client Secret. '
            'See the README for instructions.</div></div>',
            unsafe_allow_html=True,
        )
        return

    auth_link = build_auth_url()
    st.markdown(
        '<div class="login-container">'
        '<p class="login-title">Strava Bike Dashboard</p>'
        '<p class="login-subtitle">Connect your Strava account to view your bike stats.</p>'
        f'<a href="{auth_link}" target="_self" class="strava-btn">Connect with Strava</a>'
        '</div>',
        unsafe_allow_html=True,
    )


def show_dashboard():
    token = get_valid_token()
    if token is None:
        show_login()
        return

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # -- Fetch athlete --
    if "athlete" not in st.session_state:
        with st.spinner("Loading your profile..."):
            st.session_state["athlete"] = get_athlete(token)

    athlete = st.session_state["athlete"]
    bikes = {b["id"]: b["name"] for b in athlete.get("bikes", [])}

    if not bikes:
        st.markdown(
            '<div class="login-container">'
            '<p class="login-title">Strava Bike Dashboard</p>'
            '<p class="login-subtitle">No bikes found on your Strava profile.<br>'
            'Add bikes at <a href="https://www.strava.com/settings/gear" '
            'style="color:#7c5cfc;">strava.com/settings/gear</a></p></div>',
            unsafe_allow_html=True,
        )
        return

    # -- Toolbar row --
    chat_open = st.session_state.get("chat_open", False)
    if chat_open:
        st.markdown(CHAT_OPEN_CSS, unsafe_allow_html=True)
        import streamlit.components.v1 as components
        components.html(CHAT_UNCOLLAPSE_JS, height=0, width=0)

    first_name = athlete.get("firstname", "")
    view_mode = st.session_state.get("view_mode", "cards")
    VIEW_OPTIONS = {"cards": ":material/grid_view:", "list": ":material/view_list:"}

    tb_title, tb_date, tb_view, tb_ai, tb_refresh, tb_logout = st.columns(
        [3, 1.2, 0.6, 0.3, 0.3, 0.3], vertical_alignment="center"
    )

    with tb_title:
        greeting = f"Hey {first_name}" if first_name else "Bike Dashboard"
        st.markdown(
            f'<p class="dash-title">{greeting}</p>',
            unsafe_allow_html=True,
        )

    preset_index = TIME_PRESETS.index("Last 12 months")
    if "chat_filter_preset" in st.session_state:
        override = st.session_state.pop("chat_filter_preset")
        if override in TIME_PRESETS:
            preset_index = TIME_PRESETS.index(override)

    with tb_date:
        selected_preset = st.selectbox(
            "Time range",
            TIME_PRESETS,
            index=preset_index,
            label_visibility="collapsed",
        )

    with tb_view:
        selected_view = st.segmented_control(
            "View",
            options=list(VIEW_OPTIONS.keys()),
            format_func=lambda v: VIEW_OPTIONS[v],
            default=view_mode,
            selection_mode="single",
            label_visibility="collapsed",
            key="view_toggle",
        )
        if selected_view and selected_view != view_mode:
            st.session_state["view_mode"] = selected_view
            st.rerun()

    with tb_ai:
        if st.button("", icon=":material/auto_awesome:", use_container_width=True, help="AI Coach"):
            st.session_state["chat_open"] = not chat_open
            st.rerun()

    with tb_refresh:
        if st.button("", icon=":material/refresh:", use_container_width=True, help="Refresh data"):
            for key in list(st.session_state.keys()):
                if key.startswith("activities_") or key == "athlete":
                    del st.session_state[key]
            st.rerun()

    with tb_logout:
        if st.button("", icon=":material/logout:", use_container_width=True, help="Log out"):
            st.session_state.clear()
            if PERSIST_TOKENS and TOKENS_FILE.exists():
                TOKENS_FILE.unlink()
            st.rerun()

    # -- Resolve dates (custom range shows a date picker row) --
    if selected_preset == "Custom range":
        today = date.today()
        one_year_ago = today - timedelta(days=365)
        default_start = st.session_state.pop("_chat_custom_start", None)
        default_end = st.session_state.pop("_chat_custom_end", None)
        if default_start is not None:
            st.session_state["custom_start"] = default_start
        if default_end is not None:
            st.session_state["custom_end"] = default_end
        if "custom_start" not in st.session_state:
            st.session_state["custom_start"] = one_year_ago
        if "custom_end" not in st.session_state:
            st.session_state["custom_end"] = today
        dc1, dc2 = st.columns(2)
        with dc1:
            start_date = st.date_input(
                "Start date",
                max_value=today, key="custom_start",
            )
        with dc2:
            end_date = st.date_input(
                "End date",
                max_value=today, key="custom_end",
            )
    else:
        start_date, end_date = resolve_time_preset(selected_preset)
    after_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
    before_ts = int(datetime.combine(end_date, datetime.max.time()).timestamp())
    cache_key = f"activities_{after_ts}_{before_ts}"

    if cache_key not in st.session_state:
        with st.spinner("Fetching rides from Strava..."):
            st.session_state[cache_key] = get_all_activities(token, after=after_ts, before=before_ts)

    activities = st.session_state[cache_key]

    # -- AI Coach sidebar --
    if chat_open:
        _render_chat_sidebar(athlete, bikes, selected_preset, start_date, end_date, activities)

    # -- Subtitle with date context --
    ride_count = len(activities)
    st.markdown(
        f'<p class="dash-subtitle">'
        f'{selected_preset} &nbsp;·&nbsp; '
        f'{start_date.strftime("%b %d, %Y")} – {end_date.strftime("%b %d, %Y")}'
        f' &nbsp;·&nbsp; {ride_count} ride{"s" if ride_count != 1 else ""}'
        f'</p>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # -- KPI row --
    total_dist = sum(a.get("distance", 0) for a in activities)
    total_elev = sum(a.get("total_elevation_gain", 0) for a in activities)
    total_time = sum(a.get("moving_time", 0) for a in activities)
    n = max(ride_count, 1)

    dist_mi = meters_to_miles(total_dist)
    elev_ft = meters_to_feet(total_elev)

    k1, k2, k3, k4 = st.columns(4)
    kpis = [
        (k1, "Total Distance", f"{dist_mi:,.0f}", "mi", f"{dist_mi / n:,.1f} mi/ride"),
        (k2, "Total Elevation", f"{elev_ft:,.0f}", "ft", f"{elev_ft / n:,.0f} ft/ride"),
        (k3, "Total Time", seconds_to_hm(total_time), "", f"{total_time / n / 60:,.0f} min/ride"),
        (k4, "Total Rides", str(ride_count), "", f"{len(bikes)} bike{'s' if len(bikes) != 1 else ''}"),
    ]
    for col, label, value, unit, sub in kpis:
        with col:
            st.markdown(
                f'<div class="kpi-card">'
                f'<p class="kpi-value">{value}<span class="kpi-unit">{unit}</span></p>'
                f'<p class="kpi-label">{label}</p>'
                f'<p class="kpi-sub">{sub}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    if not activities:
        st.markdown(
            '<p style="text-align:center;color:var(--text-secondary);padding:48px 0;">No rides found in this time range.</p>',
            unsafe_allow_html=True,
        )
        return

    if view_mode == "list":
        _render_list_view(activities, bikes)
    else:
        # -- Group by bike --
        bike_activities: dict[str, list[dict]] = {bid: [] for bid in bikes}
        for act in activities:
            gid = act.get("gear_id")
            if gid and gid in bike_activities:
                bike_activities[gid].append(act)

        # -- Bike cards (2-up grid, sorted by hours ridden desc, hide empty) --
        bike_list = sorted(
            [(bid, bname) for bid, bname in bikes.items() if bike_activities.get(bid)],
            key=lambda b: sum(a.get("moving_time", 0) for a in bike_activities.get(b[0], [])),
            reverse=True,
        )
        for row_start in range(0, len(bike_list), 2):
            row_bikes = bike_list[row_start:row_start + 2]
            cols = st.columns(2)
            for col_idx, (bike_id, bike_name) in enumerate(row_bikes):
                acts = bike_activities.get(bike_id, [])
                accent = ACCENT_COLORS[(row_start + col_idx) % len(ACCENT_COLORS)]
                cnt = len(acts)
                ride_label = "ride" if cnt == 1 else "rides"

                td = meters_to_miles(sum(a.get("distance", 0) for a in acts))
                te = meters_to_feet(sum(a.get("total_elevation_gain", 0) for a in acts))
                tt = sum(a.get("moving_time", 0) for a in acts)

                boxes = (
                    f'<div class="metric-box">'
                    f'<div class="metric-label">Distance</div>'
                    f'<p class="metric-value" style="color:{accent};">'
                    f'{td:,.1f}<span class="metric-unit">mi</span></p></div>'
                    f'<div class="metric-box">'
                    f'<div class="metric-label">Elevation</div>'
                    f'<p class="metric-value" style="color:{accent};">'
                    f'{te:,.0f}<span class="metric-unit">ft</span></p></div>'
                    f'<div class="metric-box">'
                    f'<div class="metric-label">Time</div>'
                    f'<p class="metric-value" style="color:{accent};">'
                    f'{seconds_to_hm(tt)}</p></div>'
                )

                header_html = (
                    f'<div class="bike-card-header">'
                    f'<span class="accent-dot" style="background:{accent};box-shadow:0 0 8px {accent};"></span>'
                    f'<p class="bike-name">{bike_name}</p>'
                    f'<span class="bike-rides">{cnt} {ride_label}</span>'
                    f'</div>'
                    f'<div class="metric-row">{boxes}</div>'
                )

                with cols[col_idx]:
                    with st.container(border=True):
                        st.markdown(header_html, unsafe_allow_html=True)
                        st.markdown('<div class="view-rides-btn">', unsafe_allow_html=True)
                        if st.button(f"View {cnt} {ride_label} →", key=f"view_{bike_id}"):
                            show_rides_dialog(bike_name, acts, accent)
                        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Strava Bike Dashboard", page_icon="🚲", layout="wide")

if "access_token" not in st.session_state:
    _load_tokens_from_disk()

query_params = st.query_params
if "code" in query_params and "access_token" not in st.session_state:
    code = query_params["code"]
    try:
        token_data = exchange_code_for_token(code)
        _store_tokens(token_data)
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Authentication failed: {e}")

if "access_token" in st.session_state:
    show_dashboard()
else:
    show_login()
