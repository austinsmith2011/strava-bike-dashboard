from __future__ import annotations

import json
import os
import time
from datetime import datetime, date, timedelta
from pathlib import Path

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

METERS_PER_MILE = 1609.34
FEET_PER_METER = 3.28084

ACCENT_COLORS = ["#356AE6", "#34a853", "#f5a623", "#6b5ce7", "#c4314b", "#9c5cc4"]

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
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="st-"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

#MainMenu, header, footer { visibility: hidden; }
.stDeployButton { display: none; }

.stApp {
    background: #0d1526;
}

section[data-testid="stSidebar"] { display: none; }

/* Toolbar */
div[data-testid="stHorizontalBlock"].toolbar-row {
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding-bottom: 16px;
    margin-bottom: 24px;
}
div[data-testid="stSelectbox"] label {
    color: #7a8599 !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600 !important;
}

/* KPI cards */
.kpi-card {
    background: #152036;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 20px 24px;
    text-align: center;
}
.kpi-value {
    font-size: 1.9rem;
    font-weight: 700;
    color: #eef0f4;
    margin: 0;
    line-height: 1.2;
}
.kpi-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #7a8599;
    font-weight: 600;
    margin-top: 4px;
    margin-bottom: 2px;
}
.kpi-sub {
    font-size: 0.75rem;
    color: #4e5a6e;
    font-weight: 500;
    margin: 0;
}
.kpi-unit {
    font-size: 0.75rem;
    font-weight: 500;
    color: #7a8599;
    margin-left: 3px;
}

/* Bike card — uses st.container(border=True) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #152036 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    transition: border-color 0.2s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(255,255,255,0.16) !important;
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
    color: #eef0f4;
    margin: 0;
}
.bike-rides {
    font-size: 0.72rem;
    color: #7a8599;
    font-weight: 500;
    background: rgba(255,255,255,0.04);
    padding: 2px 9px;
    border-radius: 99rem;
    margin-left: auto;
}
.accent-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}

/* Metric boxes inside cards */
.metric-row {
    display: flex;
    gap: 12px;
}
.metric-box {
    flex: 1;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 4px;
    padding: 12px 14px;
}
.metric-label {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #7a8599;
    font-weight: 600;
    margin-bottom: 4px;
}
.metric-value {
    font-size: 1.3rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.2;
}
.metric-unit {
    font-size: 0.68rem;
    font-weight: 500;
    color: #7a8599;
    margin-left: 3px;
}

/* Header */
.dash-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #eef0f4;
    margin: 0;
    line-height: 1.3;
}
.dash-subtitle {
    color: #7a8599;
    font-size: 0.82rem;
    margin: 0;
}

/* Login page */
.login-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    text-align: center;
}
.login-title {
    font-size: 2.4rem;
    font-weight: 700;
    color: #eef0f4;
    margin-bottom: 8px;
}
.login-subtitle {
    color: #7a8599;
    font-size: 1rem;
    margin-bottom: 36px;
}
.strava-btn {
    display: inline-block;
    padding: 14px 36px;
    background: #fc4c02;
    color: white !important;
    border-radius: 4px;
    text-decoration: none;
    font-weight: 600;
    font-size: 1.05rem;
    transition: background 0.2s ease;
}
.strava-btn:hover {
    background: #e8430a;
    color: white !important;
}

.setup-warning {
    background: rgba(245,166,35,0.08);
    border: 1px solid rgba(245,166,35,0.2);
    border-radius: 8px;
    padding: 20px 24px;
    color: #f5a623;
    font-size: 0.9rem;
    line-height: 1.5;
}

/* Streamlit button overrides */
button[kind="secondary"] {
    border: 1px solid rgba(255,255,255,0.08) !important;
    background: transparent !important;
    border-radius: 4px !important;
    color: #7a8599 !important;
    font-size: 0.8rem !important;
}
button[kind="secondary"]:hover {
    border-color: rgba(255,255,255,0.2) !important;
    color: #eef0f4 !important;
}

/* View-rides text link button inside card */
.view-rides-btn button {
    background: none !important;
    border: none !important;
    color: #7a8599 !important;
    font-size: 0.76rem !important;
    padding: 0 !important;
    font-weight: 500 !important;
    min-height: 0 !important;
    height: auto !important;
}
.view-rides-btn button:hover {
    color: #356AE6 !important;
    background: none !important;
    border: none !important;
}

/* Right-side drawer */
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
    background: #152036 !important;
    border-left: 1px solid rgba(255,255,255,0.08);
    overflow-y: auto;
}

/* Ride list inside drawer */
.ride-list {
    display: flex;
    flex-direction: column;
}
.ride-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.ride-row:last-child { border-bottom: none; }
.ride-info {
    flex: 1;
    min-width: 0;
}
.ride-name {
    font-size: 0.92rem;
    font-weight: 600;
    color: #eef0f4;
    margin: 0 0 3px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ride-date {
    font-size: 0.72rem;
    color: #7a8599;
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
    color: #c8cdd6;
    margin: 0;
    line-height: 1.2;
}
.ride-stat-label {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #7a8599;
    margin: 0;
}
.ride-link {
    flex-shrink: 0;
    text-decoration: none;
    color: #7a8599;
    font-size: 0.85rem;
    padding: 6px;
    border-radius: 4px;
    transition: color 0.2s;
}
.ride-link:hover {
    color: #356AE6;
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
    color: #eef0f4;
    margin: 0;
}
.dialog-ride-count {
    font-size: 0.75rem;
    color: #7a8599;
    background: rgba(255,255,255,0.04);
    padding: 2px 10px;
    border-radius: 99rem;
}
.dialog-sort-note {
    font-size: 0.72rem;
    color: #4e5a6e;
    margin: 0 0 12px 0;
}
</style>
"""


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
        f'<span class="accent-dot" style="background:{accent};"></span>'
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
            'style="color:#356AE6;">strava.com/settings/gear</a></p></div>',
            unsafe_allow_html=True,
        )
        return

    # -- Toolbar row --
    first_name = athlete.get("firstname", "")
    t1, t2, t3, t4 = st.columns([3, 1.2, 0.5, 0.5])

    with t1:
        greeting = f"Hey {first_name}" if first_name else "Bike Dashboard"
        st.markdown(
            f'<p class="dash-title">{greeting}</p>',
            unsafe_allow_html=True,
        )

    with t2:
        selected_preset = st.selectbox(
            "Time range",
            TIME_PRESETS,
            index=TIME_PRESETS.index("Last 12 months"),
            label_visibility="collapsed",
        )

    with t3:
        if st.button("↻", use_container_width=True, help="Refresh data"):
            for key in list(st.session_state.keys()):
                if key.startswith("activities_") or key == "athlete":
                    del st.session_state[key]
            st.rerun()

    with t4:
        if st.button("✕", use_container_width=True, help="Log out"):
            st.session_state.clear()
            if PERSIST_TOKENS and TOKENS_FILE.exists():
                TOKENS_FILE.unlink()
            st.rerun()

    # -- Resolve dates (custom range shows a date picker row) --
    if selected_preset == "Custom range":
        today = date.today()
        one_year_ago = today - timedelta(days=365)
        if "custom_start" not in st.session_state:
            st.session_state["custom_start"] = one_year_ago
        if "custom_end" not in st.session_state:
            st.session_state["custom_end"] = today
        dc1, dc2 = st.columns(2)
        with dc1:
            start_date = st.date_input(
                "Start date", value=st.session_state["custom_start"],
                max_value=today, key="custom_start",
            )
        with dc2:
            end_date = st.date_input(
                "End date", value=st.session_state["custom_end"],
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
            '<p style="text-align:center;color:#7a8599;padding:48px 0;">No rides found in this time range.</p>',
            unsafe_allow_html=True,
        )
        return

    # -- Group by bike --
    bike_activities: dict[str, list[dict]] = {bid: [] for bid in bikes}
    for act in activities:
        gid = act.get("gear_id")
        if gid and gid in bike_activities:
            bike_activities[gid].append(act)

    # -- Bike cards (2-up grid, sorted by hours ridden desc) --
    bike_list = sorted(
        bikes.items(),
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
                f'<span class="accent-dot" style="background:{accent};"></span>'
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
