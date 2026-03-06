import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random

st.set_page_config(
    page_title="Biomarker Monitoring",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

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
        "soft_color": "#fff2db",
        "icon": "⚠️",
        "step": 0.004,
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
        "soft_color": "#fff2db",
        "icon": "⚠️",
        "step": 4.0,
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
        "soft_color": "#e8f8ef",
        "icon": "💧",
        "step": 0.015,
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
        "soft_color": "#fff2db",
        "icon": "🧪",
        "step": 0.004,
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
        "soft_color": "#e8f8ef",
        "icon": "🧬",
        "step": 0.002,
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

def get_status_bg(status: str) -> str:
    return "#edf8f1" if status == "Normal" else "#fff2db"

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

    drift = random.uniform(-step, step)

    if marker["type"] == "range":
        center = (marker["low"] + marker["high"]) / 2
        pull = (center - current) * 0.10
    else:
        target = max(marker["high"] * 1.4, current * 0.99)
        pull = (target - current) * 0.04

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

def build_chart(marker_key: str, marker: dict):
    time_labels = st.session_state.time_labels
    y = marker["history"]
    x = list(range(len(time_labels)))
    current = marker["current"]
    low = marker["low"]
    high = marker["high"]
    status = get_status(marker)
    current_color = "#2e9d62" if status == "Normal" else "#e14d4d"

    ymin = min(min(y), low, current)
    ymax = max(max(y), high, current)
    padding = (ymax - ymin) * 0.12 if ymax != ymin else 0.1
    ymin = max(0, ymin - padding)
    ymax = ymax + padding

    fig, ax = plt.subplots(figsize=(10, 4.2))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    if marker["type"] == "range":
        ax.axhspan(low, high, alpha=0.14, color="#2e9d62")
        ax.axhline(low, linestyle="--", linewidth=2, color="#18a957", label="Lower limit")
        ax.axhline(high, linestyle="--", linewidth=2, color="#18a957", label="Upper range")
    else:
        ax.axhspan(high, ymax, alpha=0.08, color="#e14d4d")
        ax.axhline(high, linestyle="--", linewidth=2, color="#18a957", label="Upper limit")

    ax.plot(x, y, marker="o", linewidth=3, markersize=6, color="#2f5fa7", label="Trend")
    ax.axhline(current, linewidth=4, color=current_color, label="Current ISF level")
    ax.scatter([x[-1]], [current], s=120, color=current_color, edgecolors="white", linewidths=2, zorder=5, label="Current value")

    ax.set_xticks(x)
    ax.set_xticklabels(time_labels, rotation=0, fontsize=9)
    ax.set_ylabel(f"Concentration ({marker['unit']})", fontsize=11)
    ax.set_xlabel("Time", fontsize=11)
    ax.set_ylim(ymin, ymax)
    ax.grid(True, axis="y", alpha=0.2)
    ax.grid(False, axis="x")

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    ax.spines["left"].set_alpha(0.2)
    ax.spines["bottom"].set_alpha(0.2)
    ax.tick_params(axis="both", colors="#24324a")
    ax.legend(loc="upper left", frameon=False, ncol=2, fontsize=9)

    plt.tight_layout()
    return fig

def metric_row_html(key: str, marker: dict) -> str:
    status = get_status(marker)
    status_color = get_status_color(status)
    status_bg = get_status_bg(status)
    val = format_value(marker["current"], marker["unit"])

    return f"""
    <div class="metric-card">
        <div class="left-badge" style="background:{marker['card_color']};">
            <div class="left-icon">{marker['icon']}</div>
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

# -------------------------------------------------
# Session state
# -------------------------------------------------
if "selected_marker" not in st.session_state:
    st.session_state.selected_marker = "cTnI"

if "live_mode" not in st.session_state:
    st.session_state.live_mode = False

if "biomarkers" not in st.session_state:
    st.session_state.biomarkers = {
        k: {**v, "history": v["history"][:]}
        for k, v in BIOMARKER_TEMPLATE.items()
    }

if "time_labels" not in st.session_state:
    st.session_state.time_labels = make_time_labels(12)

# -------------------------------------------------
# Styling
# -------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(90,124,187,0.10), transparent 30%),
            linear-gradient(180deg, #edf3fb 0%, #f7f9fc 100%);
    }

    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
    }

    [data-testid="stToolbar"] {
        right: 1rem;
    }

    .app-shell {
        max-width: 760px;
        margin: 0 auto;
    }

    .top-hero {
        background: linear-gradient(135deg, #28467d 0%, #3a5d9c 100%);
        border-radius: 28px;
        padding: 24px 24px 20px 24px;
        color: white;
        box-shadow: 0 16px 40px rgba(30, 55, 100, 0.22);
        margin-bottom: 18px;
    }

    .top-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 8px;
    }

    .hero-sub {
        font-size: 1.02rem;
        opacity: 0.95;
    }

    .connection-pill {
        padding: 10px 14px;
        border-radius: 999px;
        background: rgba(255,255,255,0.18);
        font-weight: 600;
        font-size: 0.95rem;
        white-space: nowrap;
    }

    .glass-card {
        background: rgba(255,255,255,0.78);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255,255,255,0.55);
        border-radius: 28px;
        box-shadow: 0 14px 34px rgba(24, 47, 87, 0.10);
        padding: 16px;
        margin-bottom: 18px;
    }

    .section-title {
        font-size: 1.32rem;
        font-weight: 800;
        color: #22324f;
        margin: 4px 4px 14px 4px;
    }

    .metric-card {
        display: flex;
        align-items: center;
        gap: 14px;
        background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
        border-radius: 22px;
        padding: 12px;
        box-shadow: 0 10px 22px rgba(33, 53, 88, 0.08);
        border: 1px solid rgba(54,78,120,0.08);
        margin-bottom: 10px;
    }

    .left-badge {
        min-width: 104px;
        width: 104px;
        border-radius: 18px;
        color: white;
        text-align: center;
        padding: 12px 8px;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.15);
    }

    .left-icon {
        font-size: 1.25rem;
        margin-bottom: 6px;
    }

    .left-key {
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.0;
    }

    .metric-content {
        flex: 1;
        min-width: 0;
    }

    .metric-title-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: baseline;
        margin-bottom: 10px;
    }

    .metric-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #1d2940;
    }

    .metric-subtitle {
        font-size: 0.98rem;
        color: #75829a;
        font-weight: 600;
    }

    .reading-pill {
        border-radius: 14px;
        padding: 10px 14px;
        display: inline-flex;
        gap: 10px;
        flex-wrap: wrap;
        align-items: center;
        font-weight: 800;
        font-size: 1.12rem;
    }

    .reading-status {
        text-transform: capitalize;
    }

    .overall-banner {
        border-radius: 18px;
        padding: 16px 18px;
        color: white;
        font-weight: 800;
        text-align: center;
        font-size: 1.65rem;
        margin-top: 6px;
        margin-bottom: 14px;
    }

    .meta-row {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
        color: #53627d;
        font-size: 1rem;
        font-weight: 700;
    }

    .detail-summary {
        display: grid;
        grid-template-columns: repeat(2, minmax(0,1fr));
        gap: 10px;
        margin-bottom: 14px;
    }

    .detail-chip {
        background: #f6f9fe;
        border: 1px solid rgba(54,78,120,0.08);
        border-radius: 18px;
        padding: 12px 14px;
        color: #2b3b57;
        font-size: 0.97rem;
        line-height: 1.45;
    }

    .small-note {
        color: #6b7b95;
        font-size: 0.93rem;
        margin-top: 4px;
    }

    .footer-note {
        text-align: center;
        color: #8290a9;
        font-size: 0.90rem;
        padding: 10px 0 18px 0;
    }

    div[data-testid="stHorizontalBlock"] > div {
        align-self: stretch;
    }

    .stButton > button {
        width: 100%;
        border-radius: 16px;
        border: none;
        background: linear-gradient(135deg, #27467d 0%, #3c65af 100%);
        color: white;
        font-weight: 700;
        min-height: 48px;
        box-shadow: 0 10px 18px rgba(37, 63, 111, 0.18);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 14px;
        padding-left: 18px;
        padding-right: 18px;
        background: #eef4fb;
        color: #334764;
        font-weight: 700;
    }

    .stTabs [aria-selected="true"] {
        background: #dfeaf9 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Live update fragment
# -------------------------------------------------
@st.fragment(run_every="2s")
def live_update_fragment():
    if st.session_state.live_mode:
        update_live_readings()

live_update_fragment()

# -------------------------------------------------
# Layout
# -------------------------------------------------
biomarkers = st.session_state.biomarkers
overall = compute_overall_status()
overall_color = "#ef5350" if overall == "DANGER" else "#ffb347" if overall == "WARNING" else "#2e9d62"

st.markdown('<div class="app-shell">', unsafe_allow_html=True)

st.markdown(
    """
    <div class="top-hero">
        <div class="top-row">
            <div>
                <div class="hero-title">Biomarker Monitoring</div>
                <div class="hero-sub">Connected to wearable biosensor</div>
            </div>
            <div class="connection-pill">● Live connection</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

live_col1, live_col2 = st.columns([1, 1])
with live_col1:
    st.toggle("Live simulation", key="live_mode")
with live_col2:
    if st.button("Generate one new reading"):
        update_live_readings()
        st.rerun()

# Summary cards
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Live Biomarker Summary</div>', unsafe_allow_html=True)

for key, marker in biomarkers.items():
    c1, c2 = st.columns([5.2, 1.2], vertical_alignment="center")
    with c1:
        st.markdown(metric_row_html(key, marker), unsafe_allow_html=True)
    with c2:
        if st.button("Open", key=f"open_{key}"):
            st.session_state.selected_marker = key

st.markdown("</div>", unsafe_allow_html=True)

# Overall status
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Overall Status</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="overall-banner" style="background:{overall_color};">{overall}</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f"""
    <div class="meta-row">
        <div><strong>Last Update:</strong> {datetime.now().strftime("%H:%M:%S")}</div>
        <div><strong>Signal Quality:</strong> Good</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# Detail section
selected_key = st.session_state.selected_marker
selected_marker = biomarkers[selected_key]
selected_status = get_status(selected_marker)

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown(f'<div class="section-title">{selected_key} Details</div>', unsafe_allow_html=True)
st.markdown(details_html(selected_key, selected_marker), unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Trend", "History", "Interpretation"])

with tab1:
    fig = build_chart(selected_key, selected_marker)
    st.pyplot(fig, use_container_width=True)

    if selected_marker["type"] == "upper_only":
        st.markdown(
            """
            <div class="small-note">
            The green dashed threshold marks the maximum healthy limit.
            The solid current ISF line turns <strong>red</strong> when the current biomarker level exceeds that limit
            and <strong>green</strong> when it remains below it.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="small-note">
            The healthy ISF band is shaded in green.
            The solid current ISF line turns <strong>green</strong> when the current value remains within the acceptable range
            and <strong>red</strong> if it falls below the lower limit or exceeds the upper limit.
            </div>
            """,
            unsafe_allow_html=True,
        )

with tab2:
    df = pd.DataFrame(
        {
            "Time": st.session_state.time_labels,
            "Concentration": [format_value(v, selected_marker["unit"]) for v in selected_marker["history"]],
        }
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab3:
    if selected_marker["type"] == "upper_only":
        st.markdown(
            f"""
            **Healthy threshold**  
            0 – {selected_marker['high']} {selected_marker['unit']}

            **Current ISF reading**  
            {format_value(selected_marker['current'], selected_marker['unit'])}

            **Status**  
            {selected_status}
            """
        )
    else:
        st.markdown(
            f"""
            **Healthy ISF range**  
            {selected_marker['low']} – {selected_marker['high']} {selected_marker['unit']}

            **Current ISF reading**  
            {format_value(selected_marker['current'], selected_marker['unit'])}

            **Status**  
            {selected_status}
            """
        )

st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="footer-note">Wearable biosensor interface concept for continuous ISF-based cardiovascular monitoring</div>',
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)
