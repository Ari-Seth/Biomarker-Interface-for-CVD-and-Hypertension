import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Biomarker Monitoring",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -------------------------------------------------
# Theme toggle
# -------------------------------------------------
top_left, top_right = st.columns([8, 1])
with top_right:
    dark_mode = st.toggle("🌙", value=True)

# -------------------------------------------------
# Biomarker template with live simulation settings
# -------------------------------------------------
BIOMARKER_TEMPLATE = {
    "cTnI": {
        "full": "Cardiac Troponin I",
        "unit": "ng/mL",
        "type": "upper_only",
        "low": 0.0,
        "high": 0.04,
        "current": 0.150,
        "history": [0.012, 0.018, 0.022, 0.031, 0.044, 0.061, 0.082, 0.101, 0.118, 0.135, 0.145, 0.150],
        "card_color": "#ff5e62",
        "normal_icon": "🫀",
        "step": 0.015,
        "min_sim": 0.000,
        "max_sim": 0.200,
    },
    "BNP": {
        "full": "B-Type Natriuretic Peptide",
        "unit": "pg/mL",
        "type": "upper_only",
        "low": 0.0,
        "high": 100.0,
        "current": 160.0,
        "history": [58, 63, 70, 82, 95, 108, 116, 126, 135, 145, 152, 160],
        "card_color": "#ff5e62",
        "normal_icon": "🫀",
        "step": 15.0,
        "min_sim": 0.0,
        "max_sim": 220.0,
    },
    "Na": {
        "full": "Sodium",
        "unit": "mg/mL",
        "type": "range",
        "low": 3.06,
        "high": 3.36,
        "current": 3.18,
        "history": [3.10, 3.12, 3.14, 3.16, 3.17, 3.19, 3.20, 3.19, 3.18, 3.18, 3.17, 3.18],
        "card_color": "#4cb8a5",
        "normal_icon": "💧",
        "step": 0.060,
        "min_sim": 2.90,
        "max_sim": 3.50,
    },
    "K": {
        "full": "Potassium",
        "unit": "mg/mL",
        "type": "range",
        "low": 0.125,
        "high": 0.223,
        "current": 0.118,
        "history": [0.178, 0.171, 0.164, 0.156, 0.149, 0.142, 0.136, 0.131, 0.127, 0.123, 0.120, 0.118],
        "card_color": "#ffb347",
        "normal_icon": "🧪",
        "step": 0.015,
        "min_sim": 0.090,
        "max_sim": 0.250,
    },
    "Ca2+": {
        "full": "Calcium",
        "unit": "mg/mL",
        "type": "range",
        "low": 0.0737,
        "high": 0.109,
        "current": 0.096,
        "history": [0.089, 0.091, 0.093, 0.094, 0.095, 0.096, 0.097, 0.097, 0.096, 0.096, 0.095, 0.096],
        "card_color": "#45c0e6",
        "normal_icon": "🧬",
        "step": 0.008,
        "min_sim": 0.060,
        "max_sim": 0.120,
    },
}


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def make_time_labels(n: int = 12):
    start = datetime.now() - timedelta(seconds=(n - 1) * 2)
    return [(start + timedelta(seconds=2 * i)).strftime("%H:%M:%S") for i in range(n)]


def format_value(value, unit):
    if unit == "pg/mL":
        return f"{value:.0f} {unit}"
    if unit == "ng/mL":
        return f"{value:.3f} {unit}"
    if unit == "mg/mL":
        return f"{value:.3f} {unit}" if value < 1 else f"{value:.2f} {unit}"
    return f"{value} {unit}"


def get_status(marker: dict) -> str:
    v = marker["current"]
    low = marker["low"]
    high = marker["high"]

    if marker["type"] == "upper_only":
        return "High" if v > high else "Normal"

    if v < low:
        return "Low"
    if v > high:
        return "High"
    return "Normal"


def get_status_color(status: str) -> str:
    return "#2e9d62" if status == "Normal" else "#e14d4d"


def get_status_bg(status: str, dark_mode: bool = False) -> str:
    if dark_mode:
        return "#123524" if status == "Normal" else "#3b1219"
    return "#edf8f1" if status == "Normal" else "#ffe4e6"


def compute_overall_status() -> str:
    biomarkers = st.session_state.biomarkers
    abnormal = [get_status(v) for v in biomarkers.values() if get_status(v) != "Normal"]

    if any(x == "High" for x in abnormal) and get_status(biomarkers["cTnI"]) == "High":
        return "DANGER"
    if abnormal:
        return "WARNING"
    return "STABLE"


def simulate_next_value(marker: dict) -> float:
    current = marker["current"]
    step = marker["step"]

    # Stronger random movement
    drift = random.uniform(-2.5 * step, 2.5 * step)

    # Weak pull back toward center for range biomarkers
    if marker["type"] == "range":
        center = (marker["low"] + marker["high"]) / 2
        pull = (center - current) * 0.02
    else:
        pull = 0.0

    new_value = current + drift + pull
    new_value = max(marker["min_sim"], min(marker["max_sim"], new_value))

    if marker["unit"] == "pg/mL":
        return round(new_value, 1)
    if marker["unit"] == "ng/mL":
        return round(new_value, 3)
    return round(new_value, 4)


def update_live_readings():
    for marker in st.session_state.biomarkers.values():
        new_value = simulate_next_value(marker)
        marker["current"] = new_value
        marker["history"] = marker["history"][1:] + [new_value]

    now_label = datetime.now().strftime("%H:%M:%S")
    st.session_state.time_labels = st.session_state.time_labels[1:] + [now_label]
    st.session_state.last_update = now_label


def build_chart(marker: dict, dark_mode: bool):
    time_labels = st.session_state.time_labels
    y = marker["history"]
    x = list(range(len(time_labels)))
    current = marker["current"]
    low = marker["low"]
    high = marker["high"]
    status = get_status(marker)
    current_color = "#34d399" if status == "Normal" else "#f87171"

    ymin = min(min(y), low, current)
    ymax = max(max(y), high, current)
    padding = (ymax - ymin) * 0.12 if ymax != ymin else 0.1
    ymin = max(0, ymin - padding)
    ymax = ymax + padding

    bg = "#111827" if dark_mode else "white"
    fg = "#e5e7eb" if dark_mode else "#24324a"
    grid = "#334155" if dark_mode else "#dbe4f0"
    trend = "#60a5fa" if dark_mode else "#2f5fa7"
    limit = "#22c55e" if dark_mode else "#18a957"

    fig, ax = plt.subplots(figsize=(10, 4.2))
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)

    if marker["type"] == "range":
        ax.axhspan(low, high, alpha=0.14, color="#22c55e")
        ax.axhline(low, linestyle="--", linewidth=2, color=limit, label="Lower limit")
        ax.axhline(high, linestyle="--", linewidth=2, color=limit, label="Upper range")
    else:
        ax.axhspan(high, ymax, alpha=0.10, color="#ef4444")
        ax.axhline(high, linestyle="--", linewidth=2, color=limit, label="Upper limit")

    ax.plot(x, y, marker="o", linewidth=3, markersize=6, color=trend, label="Trend")
    ax.axhline(current, linewidth=4, color=current_color, label="Current ISF level")
    ax.scatter([x[-1]], [current], s=120, color=current_color, edgecolors="white", linewidths=2, zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels(time_labels, fontsize=9, color=fg)
    ax.set_ylabel(f"Concentration ({marker['unit']})", color=fg)
    ax.set_xlabel("Time", color=fg)
    ax.set_ylim(ymin, ymax)
    ax.grid(True, axis="y", alpha=0.25, color=grid)
    ax.grid(False, axis="x")

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    ax.spines["left"].set_color(grid)
    ax.spines["bottom"].set_color(grid)
    ax.tick_params(axis="y", colors=fg)
    ax.tick_params(axis="x", colors=fg)
    legend = ax.legend(loc="upper left", frameon=False, ncol=2, fontsize=9)
    for text in legend.get_texts():
        text.set_color(fg)

    plt.tight_layout()
    return fig


def metric_row_html(key: str, marker: dict, dark_mode: bool = False) -> str:
    status = get_status(marker)
    status_color = get_status_color(status)
    status_bg = get_status_bg(status, dark_mode)
    val = format_value(marker["current"], marker["unit"])

    is_abnormal = status != "Normal"
    display_icon = "⚠️" if is_abnormal else marker.get("normal_icon", "●")

    if dark_mode:
        card_border = "#ef4444" if is_abnormal else "rgba(255,255,255,0.05)"
        card_shadow = "0 10px 22px rgba(239,68,68,0.20)" if is_abnormal else "0 10px 22px rgba(0,0,0,0.18)"
        abnormal_bg = "#2a1316" if is_abnormal else "#1f2937"
    else:
        card_border = "#ef4444" if is_abnormal else "rgba(54,78,120,0.08)"
        card_shadow = "0 10px 22px rgba(239,68,68,0.18)" if is_abnormal else "0 10px 22px rgba(33,53,88,0.08)"
        abnormal_bg = "#fff5f5" if is_abnormal else "linear-gradient(180deg, #ffffff 0%, #fbfcff 100%)"

    return f"""
    <div class="metric-card" style="
        border: 2px solid {card_border};
        box-shadow: {card_shadow};
        background: {abnormal_bg};
    ">
        <div class="left-badge" style="background:{marker['card_color']};">
            <div class="left-icon">{display_icon}</div>
            <div class="left-key">{key}</div>
        </div>
        <div class="metric-content">
            <div class="metric-title-row">
                <div class="metric-title">{key}</div>
                <div class="metric-subtitle">{marker['full']}</div>
            </div>
            <div class="reading-pill" style="background:{status_bg}; color:{status_color};">
                <span class="reading-status">{status}</span>
                <span class="reading-value">{val}</span>
            </div>
        </div>
    </div>
    """


def details_html(key: str, marker: dict) -> str:
    status = get_status(marker)
    low = marker["low"]
    high = marker["high"]

    if marker["type"] == "upper_only":
        range_text = f"Normal: 0 – {high} {marker['unit']}<br>Unhealthy: &gt; {high} {marker['unit']}"
    else:
        range_text = f"Healthy ISF range: {low} – {high} {marker['unit']}"

    return f"""
    <div class="detail-summary">
        <div class="detail-chip"><strong>Biomarker</strong><br>{key}</div>
        <div class="detail-chip"><strong>Status</strong><br>{status}</div>
        <div class="detail-chip"><strong>Current ISF</strong><br>{format_value(marker['current'], marker['unit'])}</div>
        <div class="detail-chip"><strong>Reference</strong><br>{range_text}</div>
    </div>
    """


def interpretation_text(selected_key: str, selected_marker: dict, selected_status: str):
    if selected_marker["type"] == "upper_only":
        reference_text = (
            f"Normal: 0 – {selected_marker['high']} {selected_marker['unit']}<br>"
            f"Unhealthy: &gt; {selected_marker['high']} {selected_marker['unit']}"
        )
    else:
        reference_text = (
            f"Healthy ISF range: {selected_marker['low']} – {selected_marker['high']} "
            f"{selected_marker['unit']}"
        )

    interpretation_note = ""
    if selected_key == "cTnI":
        if selected_status == "High":
            interpretation_note = (
                "The current cTnI level is above the normal threshold and may indicate "
                "myocardial injury. This reading should be clinically correlated."
            )
        else:
            interpretation_note = "The current cTnI level is within the normal threshold."
    elif selected_key == "BNP":
        if selected_status == "High":
            interpretation_note = (
                "The current BNP level is above the normal threshold and may indicate "
                "elevated cardiac stress, hypertension or heart failure risk."
            )
        else:
            interpretation_note = "The current BNP level is within the normal threshold."
    elif selected_key == "Na":
        if selected_status == "Low":
            interpretation_note = "The sodium concentration is below the healthy ISF range."
        elif selected_status == "High":
            interpretation_note = "The sodium concentration is above the healthy ISF range with correlation with hypertensive risk."
        else:
            interpretation_note = "The sodium concentration is within the healthy ISF range."
    elif selected_key == "K":
        if selected_status == "Low":
            interpretation_note = (
                "The potassium concentration is below the healthy ISF range and may warrant "
                "closer monitoring."
            )
        elif selected_status == "High":
            interpretation_note = "The potassium concentration is above the healthy ISF range with correlation with hypertensive risk."
        else:
            interpretation_note = "The potassium concentration is within the healthy ISF range."
    elif selected_key == "Ca2+":
        if selected_status == "Low":
            interpretation_note = "The calcium concentration is below the healthy ISF range."
        elif selected_status == "High":
            interpretation_note = "The calcium concentration is above the healthy ISF range with correlation with hypertensive risk."
        else:
            interpretation_note = "The calcium concentration is within the healthy ISF range."

    return reference_text, interpretation_note


# -------------------------------------------------
# Session state
# -------------------------------------------------
if "selected_marker" not in st.session_state:
    st.session_state.selected_marker = "cTnI"

if "live_mode" not in st.session_state:
    st.session_state.live_mode = True

if "biomarkers" not in st.session_state:
    st.session_state.biomarkers = {
        k: {**v, "history": v["history"][:]}
        for k, v in BIOMARKER_TEMPLATE.items()
    }

if "time_labels" not in st.session_state:
    st.session_state.time_labels = make_time_labels(12)

if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.now().strftime("%H:%M:%S")

# -------------------------------------------------
# Auto-refresh live updates
# -------------------------------------------------
if st.session_state.live_mode:
    st_autorefresh(interval=2000, key="live_refresh")
    update_live_readings()

# -------------------------------------------------
# Theme CSS
# -------------------------------------------------
if dark_mode:
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
        color: #e5e7eb;
    }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .app-shell { max-width: 760px; margin: 0 auto; }
    .top-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        border-radius: 28px;
        padding: 24px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.28);
    }
    .glass-card {
        background: rgba(17,24,39,0.86);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 28px;
        padding: 16px;
        margin-bottom: 18px;
        box-shadow: 0 14px 34px rgba(0,0,0,0.22);
    }
    .section-title {
        font-size: 1.32rem;
        font-weight: 800;
        color: #f3f4f6;
        margin-bottom: 14px;
    }
    .metric-card {
        display:flex;
        align-items:center;
        gap:14px;
        border-radius:22px;
        padding:12px;
        margin-bottom:10px;
    }
    .left-badge {
        min-width:104px;
        width:104px;
        border-radius:18px;
        color:white;
        text-align:center;
        padding:12px 8px;
    }
    .left-icon { font-size:1.25rem; margin-bottom:6px; }
    .left-key { font-size:1.55rem; font-weight:800; }
    .metric-content { flex:1; min-width:0; }
    .metric-title-row {
        display:flex;
        flex-wrap:wrap;
        gap:8px;
        align-items:baseline;
        margin-bottom:10px;
    }
    .metric-title { font-size:1.35rem; font-weight:800; color:#f3f4f6; }
    .metric-subtitle { font-size:0.98rem; color:#9ca3af; font-weight:600; }
    .reading-pill {
        border-radius:14px;
        padding:10px 14px;
        display:inline-flex;
        gap:10px;
        font-weight:800;
        font-size:1.12rem;
    }
    .overall-banner {
        border-radius:18px;
        padding:16px 18px;
        color:white;
        font-weight:800;
        text-align:center;
        font-size:1.65rem;
        margin-top:6px;
        margin-bottom:14px;
    }
    .meta-row {
        display:flex;
        justify-content:space-between;
        gap:12px;
        flex-wrap:wrap;
        color:#cbd5e1;
        font-weight:700;
    }
    .detail-summary {
        display:grid;
        grid-template-columns:repeat(2,minmax(0,1fr));
        gap:10px;
        margin-bottom:14px;
    }
    .detail-chip {
        background:#111827;
        border:1px solid rgba(255,255,255,0.06);
        border-radius:18px;
        padding:12px 14px;
        color:#e5e7eb;
    }
    .small-note {
        color:#cbd5e1;
        font-size:0.93rem;
        margin-top:4px;
    }
    .footer-note {
        text-align:center;
        color:#9ca3af;
        font-size:0.90rem;
        padding:10px 0 18px 0;
    }
    .stTabs [data-baseweb="tab"] {
        background:#1f2937;
        color:#e5e7eb;
        border-radius:14px;
    }
    .stTabs [aria-selected="true"] { background:#374151 !important; }
    .interpret-card {
        background: #111827;
        border-radius: 18px;
        padding: 18px;
        border: 1px solid rgba(255,255,255,0.06);
        color: #e5e7eb;
    }
    .interpret-title {
        font-size: 1.15rem;
        font-weight: 800;
        margin-bottom: 12px;
        color: #f3f4f6;
    }
    .interpret-row {
        margin-bottom: 12px;
        line-height: 1.55;
        color: #d1d5db;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(90,124,187,0.10), transparent 30%),
            linear-gradient(180deg, #edf3fb 0%, #f7f9fc 100%);
    }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .app-shell { max-width: 760px; margin: 0 auto; }
    .top-hero {
        background: linear-gradient(135deg, #28467d 0%, #3a5d9c 100%);
        border-radius: 28px;
        padding: 24px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 16px 40px rgba(30, 55, 100, 0.22);
    }
    .glass-card {
        background: rgba(255,255,255,0.78);
        border-radius: 28px;
        padding: 16px;
        margin-bottom: 18px;
        box-shadow: 0 14px 34px rgba(24, 47, 87, 0.10);
    }
    .section-title {
        font-size: 1.32rem;
        font-weight: 800;
        color: #22324f;
        margin-bottom: 14px;
    }
    .metric-card {
        display:flex;
        align-items:center;
        gap:14px;
        border-radius:22px;
        padding:12px;
        margin-bottom:10px;
    }
    .left-badge {
        min-width:104px;
        width:104px;
        border-radius:18px;
        color:white;
        text-align:center;
        padding:12px 8px;
    }
    .left-icon { font-size:1.25rem; margin-bottom:6px; }
    .left-key { font-size:1.55rem; font-weight:800; }
    .metric-content { flex:1; min-width:0; }
    .metric-title-row {
        display:flex;
        flex-wrap:wrap;
        gap:8px;
        align-items:baseline;
        margin-bottom:10px;
    }
    .metric-title { font-size:1.35rem; font-weight:800; color:#1d2940; }
    .metric-subtitle { font-size:0.98rem; color:#75829a; font-weight:600; }
    .reading-pill {
        border-radius:14px;
        padding:10px 14px;
        display:inline-flex;
        gap:10px;
        font-weight:800;
        font-size:1.12rem;
    }
    .overall-banner {
        border-radius:18px;
        padding:16px 18px;
        color:white;
        font-weight:800;
        text-align:center;
        font-size:1.65rem;
        margin-top:6px;
        margin-bottom:14px;
    }
    .meta-row {
        display:flex;
        justify-content:space-between;
        gap:12px;
        flex-wrap:wrap;
        color:#53627d;
        font-weight:700;
    }
    .detail-summary {
        display:grid;
        grid-template-columns:repeat(2,minmax(0,1fr));
        gap:10px;
        margin-bottom:14px;
    }
    .detail-chip {
        background:#f6f9fe;
        border-radius:18px;
        padding:12px 14px;
        color:#2b3b57;
    }
    .small-note {
        color:#6b7b95;
        font-size:0.93rem;
        margin-top:4px;
    }
    .footer-note {
        text-align:center;
        color:#8290a9;
        font-size:0.90rem;
        padding:10px 0 18px 0;
    }
    .stTabs [data-baseweb="tab"] {
        background:#eef4fb;
        color:#334764;
        border-radius:14px;
    }
    .stTabs [aria-selected="true"] { background:#dfeaf9 !important; }
    .interpret-card {
        background: #f8fbff;
        border-radius: 18px;
        padding: 18px;
        border: 1px solid rgba(54,78,120,0.08);
        color: #22324f;
    }
    .interpret-title {
        font-size: 1.15rem;
        font-weight: 800;
        margin-bottom: 12px;
        color: #1d2940;
    }
    .interpret-row {
        margin-bottom: 12px;
        line-height: 1.55;
        color: #2b3b57;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# Layout
# -------------------------------------------------
biomarkers = st.session_state.biomarkers
overall = compute_overall_status()
overall_color = "#ef5350" if overall == "DANGER" else "#ffb347" if overall == "WARNING" else "#2e9d62"

st.markdown('<div class="app-shell">', unsafe_allow_html=True)

st.markdown("""
<div class="top-hero">
    <div>
        <div style="font-size:2rem; font-weight:800;">Biomarker Monitoring</div>
        <div style="font-size:1.02rem; opacity:0.95;">Connected to wearable biosensor</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.toggle("Live simulation", key="live_mode")

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Live Biomarker Summary</div>', unsafe_allow_html=True)

for key, marker in biomarkers.items():
    c1, c2 = st.columns([5.2, 1.2], vertical_alignment="center")
    with c1:
        st.markdown(metric_row_html(key, marker, dark_mode), unsafe_allow_html=True)
    with c2:
        if st.button("Open", key=f"open_{key}"):
            st.session_state.selected_marker = key

st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Overall Status</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="overall-banner" style="background:{overall_color};">{overall}</div>',
    unsafe_allow_html=True,
)
st.markdown(f"""
<div class="meta-row">
    <div><strong>Last Update:</strong> {st.session_state.last_update}</div>
    <div><strong>Signal Quality:</strong> Good</div>
</div>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

selected_key = st.session_state.selected_marker
selected_marker = biomarkers[selected_key]
selected_status = get_status(selected_marker)

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown(f'<div class="section-title">{selected_key} Details</div>', unsafe_allow_html=True)
st.markdown(details_html(selected_key, selected_marker), unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Trend", "History", "Interpretation"])

with tab1:
    fig = build_chart(selected_marker, dark_mode)
    st.pyplot(fig, use_container_width=True)

    if selected_marker["type"] == "upper_only":
        st.markdown(
            '<div class="small-note">The green dashed threshold marks the maximum healthy limit. The solid current ISF line turns <strong>red</strong> when the current biomarker level exceeds that limit and <strong>green</strong> when it remains below it.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="small-note">The healthy ISF band is shaded in green. The solid current ISF line turns <strong>green</strong> when the current value remains within the acceptable range and <strong>red</strong> if it falls below the lower limit or exceeds the upper limit.</div>',
            unsafe_allow_html=True,
        )

with tab2:
    df = pd.DataFrame({
        "Time": st.session_state.time_labels,
        "Concentration": [format_value(v, selected_marker["unit"]) for v in selected_marker["history"]],
    })
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab3:
    reference_text, interpretation_note = interpretation_text(
        selected_key, selected_marker, selected_status
    )

    st.markdown(
        f"""
        <div class="interpret-card">
            <div class="interpret-title">Clinical Interpretation</div>
            <div class="interpret-row"><strong>Reference range:</strong><br>{reference_text}</div>
            <div class="interpret-row"><strong>Current ISF reading:</strong><br>{format_value(selected_marker['current'], selected_marker['unit'])}</div>
            <div class="interpret-row"><strong>Status:</strong><br>{selected_status}</div>
            <div class="interpret-row"><strong>Interpretation note:</strong><br>{interpretation_note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)
st.markdown(
    '<div class="footer-note">Wearable biosensor interface concept for continuous ISF-based cardiovascular monitoring</div>',
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)
