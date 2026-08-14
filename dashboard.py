from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="SentinelTwin",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

CONTEXT_PATH = DATA / "processed" / "context_sessions.csv"
INFERENCE_PATH = DATA / "processed" / "inference_sessions.csv"
TRUST_PATH = DATA / "processed" / "trusted_sessions.csv"
ONLINE_PATH = DATA / "processed" / "online_sessions.csv"
SYSTEM_TEST_PATH = DATA / "results" / "system_test_results.csv"


# ============================================================
# PALETTE
# ============================================================

PETAL_FROST = "#FFD6FF"
MAUVE_LIGHT = "#E7C6FF"
MAUVE = "#C8B6FF"
PERIWINKLE = "#BBD0FF"
DIM_GREY = "#66676E"

BACKGROUND = "#202126"
SIDEBAR = "#292A30"
CARD = "#303137"
CARD_HOVER = "#36373E"

TEXT = "#F7F5FA"
MUTED = "#B8B8C2"
BORDER = "#45464E"

SUCCESS = "#9EE6B8"
WARNING = "#F3D38A"
DANGER = "#FF9FAF"

# Semantic colors are intentionally separate from the brand palette.
CRITICAL_COLOR = "#FF6B78"
HIGH_COLOR = "#F39A72"
MEDIUM_COLOR = "#E6C46A"
GUARDED_COLOR = PERIWINKLE
LOW_COLOR = DIM_GREY


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    f"""
    <style>

    /* --------------------------------------------------------
       GLOBAL
    -------------------------------------------------------- */

    .stApp {{
        background:
            radial-gradient(
                circle at 80% 0%,
                rgba(200, 182, 255, 0.08),
                transparent 25%
            ),
            {BACKGROUND};
        color: {TEXT};
    }}

    .block-container {{
        padding-top: 1.7rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }}

    #MainMenu {{
        visibility: hidden;
    }}

    footer {{
        visibility: hidden;
    }}

    header {{
        background: transparent !important;
    }}


    /* --------------------------------------------------------
       SIDEBAR
    -------------------------------------------------------- */

    section[data-testid="stSidebar"] {{
        background:
            linear-gradient(
                180deg,
                #27282E 0%,
                #202126 100%
            );

        border-right: 1px solid {BORDER};
    }}

    section[data-testid="stSidebar"] > div {{
        padding-top: 1.3rem;
    }}

    section[data-testid="stSidebar"] * {{
        color: {TEXT};
    }}

    .sidebar-brand {{
        padding: 8px 8px 24px 8px;
    }}

    .brand-title {{
        font-size: 24px;
        font-weight: 750;
        letter-spacing: -0.6px;
        color: {TEXT};
    }}

    .brand-subtitle {{
        color: {MUTED};
        font-size: 12px;
        margin-top: 4px;
    }}

    .system-status {{
        margin-top: 35px;
        padding: 16px;
        border-radius: 14px;
        border: 1px solid {BORDER};
        background: rgba(255,255,255,0.025);
    }}

    .status-dot {{
        height: 8px;
        width: 8px;
        background: {SUCCESS};
        border-radius: 50%;
        display: inline-block;
        margin-right: 7px;
    }}


    /* --------------------------------------------------------
       TITLES
    -------------------------------------------------------- */

    .page-title {{
        font-size: 29px;
        font-weight: 750;
        letter-spacing: -0.7px;
        color: {TEXT};
        margin-bottom: 2px;
    }}

    .page-subtitle {{
        color: {MUTED};
        font-size: 14px;
        margin-bottom: 24px;
    }}

    .section-title {{
        font-size: 17px;
        font-weight: 650;
        margin-bottom: 13px;
        color: {TEXT};
    }}


    /* --------------------------------------------------------
       KPI CARDS
    -------------------------------------------------------- */

    .metric-card {{
        min-height: 142px;
        padding: 19px 20px;
        border-radius: 15px;
        border: 1px solid {BORDER};
        background: {CARD};
        transition: 0.18s ease;
    }}

    .metric-card:hover {{
        transform: translateY(-2px);
        background: {CARD_HOVER};
        border-color: {MAUVE};
    }}

    .metric-label {{
        color: {MUTED};
        font-size: 12px;
        font-weight: 550;
        margin-bottom: 10px;
    }}

    .metric-value {{
        font-size: 30px;
        font-weight: 750;
        color: {TEXT};
        line-height: 1;
        margin-bottom: 13px;
    }}

    .metric-note {{
        font-size: 11px;
        color: {MUTED};
    }}

    .metric-pink {{
        border-top: 3px solid {PETAL_FROST};
    }}

    .metric-purple {{
        border-top: 3px solid {MAUVE};
    }}

    .metric-blue {{
        border-top: 3px solid {PERIWINKLE};
    }}

    .metric-grey {{
        border-top: 3px solid {DIM_GREY};
    }}


    /* --------------------------------------------------------
       PANEL
    -------------------------------------------------------- */

    .panel-heading {{
        padding-top: 4px;
        font-size: 16px;
        font-weight: 650;
        color: {TEXT};
    }}


    /* --------------------------------------------------------
       ALERT TABLE
    -------------------------------------------------------- */

    .alert-row {{
        display: grid;
        grid-template-columns: 1.1fr 0.65fr 1.6fr 0.9fr;
        gap: 10px;

        align-items: center;

        padding: 11px 8px;

        border-bottom: 1px solid {BORDER};

        font-size: 12px;
    }}

    .alert-header {{
        color: {MUTED};
        font-weight: 600;
    }}

    .risk-high {{
        color: {DANGER};
        font-weight: 700;
    }}

    .risk-medium {{
        color: {WARNING};
        font-weight: 700;
    }}

    .risk-low {{
        color: {PERIWINKLE};
        font-weight: 700;
    }}

    .badge {{
        display: inline-block;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 10px;
        font-weight: 650;
    }}

    .badge-reject {{
        background: rgba(255, 159, 175, 0.12);
        color: {DANGER};
        border: 1px solid rgba(255,159,175,0.35);
    }}

    .badge-quarantine {{
        background: rgba(243, 211, 138, 0.10);
        color: {WARNING};
        border: 1px solid rgba(243,211,138,0.35);
    }}

    .badge-trust {{
        background: rgba(158, 230, 184, 0.10);
        color: {SUCCESS};
        border: 1px solid rgba(158,230,184,0.30);
    }}


    /* --------------------------------------------------------
       STREAMLIT ELEMENTS
    -------------------------------------------------------- */

    div[data-testid="stDataFrame"] {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        overflow: hidden;
    }}

    div[data-testid="stSelectbox"] > div {{
        background: {CARD};
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}

    .stTabs [data-baseweb="tab"] {{
        background: {CARD};
        border-radius: 8px;
        padding: 7px 15px;
    }}

    /* --------------------------------------------------------
       STREAMLIT NATIVE CONTROL OVERRIDES
       Keep Streamlit's default red out of the brand UI.
    -------------------------------------------------------- */

    div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child {{
        border-color: {DIM_GREY} !important;
    }}

    div[role="radiogroup"] label[data-baseweb="radio"] input:checked + div {{
        background-color: {MAUVE} !important;
        border-color: {MAUVE} !important;
    }}

    div[data-baseweb="tag"] {{
        background-color: rgba(200, 182, 255, 0.16) !important;
        border: 1px solid rgba(200, 182, 255, 0.42) !important;
        color: {TEXT} !important;
    }}

    div[data-baseweb="tag"] span {{
        color: {TEXT} !important;
    }}

    div[data-baseweb="select"] > div {{
        background-color: {CARD} !important;
        border-color: {BORDER} !important;
        color: {TEXT} !important;
    }}

    div[data-baseweb="popover"] {{
        background-color: {CARD} !important;
    }}

    div[data-baseweb="menu"] {{
        background-color: {CARD} !important;
    }}

    div[data-baseweb="option"] {{
        color: {TEXT} !important;
    }}

    div[data-baseweb="option"]:hover {{
        background-color: rgba(200, 182, 255, 0.12) !important;
    }}

    div[data-testid="stDataFrame"] {{
        background: {CARD};
    }}

    /* Plotly containers should sit on the page rather than create
       a second large block of competing background colour. */
    div[data-testid="stPlotlyChart"] {{
        border: 1px solid {BORDER};
        border-radius: 14px;
        overflow: hidden;
        background: {CARD};
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADING
# ============================================================


@st.cache_data
def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None

    df = pd.read_csv(path)

    for column in [
        "timestamp",
        "start_time",
        "end_time",
        "session_start",
        "session_end",
    ]:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
            )

    return df


def first_available(*frames: pd.DataFrame | None):
    for frame in frames:
        if frame is not None and not frame.empty:
            return frame.copy()

    return pd.DataFrame()


context_df = load_csv(CONTEXT_PATH)
inference_df = load_csv(INFERENCE_PATH)
trust_df = load_csv(TRUST_PATH)
online_df = load_csv(ONLINE_PATH)
system_test_df = load_csv(SYSTEM_TEST_PATH)

df = first_available(
    inference_df,
    context_df,
    online_df,
)


# ============================================================
# HELPERS
# ============================================================


def safe_count(
    dataframe: pd.DataFrame,
    column: str,
    value,
) -> int:

    if column not in dataframe.columns:
        return 0

    return int((dataframe[column] == value).sum())


def metric_card(
    label: str,
    value: str,
    note: str,
    style: str,
):

    st.markdown(
        f"""
        <div class="metric-card {style}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def find_time_column(dataframe: pd.DataFrame):

    possibilities = [
        "start_time",
        "timestamp",
        "session_start",
        "end_time",
    ]

    for column in possibilities:
        if column in dataframe.columns:
            return column

    return None


def severity_from_risk(risk):

    if risk >= 80:
        return "CRITICAL"

    if risk >= 65:
        return "HIGH"

    if risk >= 45:
        return "MEDIUM"

    if risk >= 25:
        return "GUARDED"

    return "LOW"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-brand">'
        '<div class="brand-title">◇ SentinelTwin</div>'
        '<div class="brand-subtitle">Adaptive Behavioral Digital Twin</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Twin Explorer",
            "Alerts",
            "Drift Timeline",
            "Trust Ledger",
            "Evaluation",
        ],
        label_visibility="collapsed",
    )

    st.markdown(
        '<div style="margin-top:10px;">'
        '<span class="status-dot"></span>'
        " Operational"
        "</div>"
        '<div style="color:#B8B8C2;font-size:11px;margin-top:8px;">'
        "Behavioral twin active"
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# EMPTY DATA CHECK
# ============================================================

if df.empty:

    st.error(
        "No SentinelTwin processed dataset was found. "
        "Run the pipeline before launching the dashboard."
    )

    st.stop()


# ============================================================
# OVERVIEW
# ============================================================

if page == "Overview":

    st.markdown(
        '<div class="page-title">Security Overview</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        "System-wide behavioral security posture at a glance"
        "</div>",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    entity_count = df["user_id"].nunique() if "user_id" in df.columns else 0

    if "final_risk" in df.columns:
        alerts = int((df["final_risk"] >= 45).sum())
    else:
        alerts = 0

    if "severity" in df.columns:
        critical = safe_count(
            df,
            "severity",
            "CRITICAL",
        )
    elif "final_risk" in df.columns:
        critical = int((df["final_risk"] >= 80).sum())
    else:
        critical = 0

    # Held-out system evaluation gave 2.235%.
    false_positive_rate = 2.235

    contamination = 0.0

    if (
        online_df is not None
        and "is_attack" in online_df.columns
        and "trust_decision" in online_df.columns
    ):

        learned_attacks = online_df[
            (online_df["is_attack"] == 1) & (online_df["trust_decision"] == "TRUST")
        ]

        trusted = online_df[online_df["trust_decision"] == "TRUST"]

        if len(trusted):
            contamination = len(learned_attacks) / len(trusted) * 100

    columns = st.columns(5)

    with columns[0]:
        metric_card(
            "MONITORED ENTITIES",
            f"{entity_count:,}",
            "Behavioral identities",
            "metric-pink",
        )

    with columns[1]:
        metric_card(
            "ACTIVE ALERTS",
            f"{alerts:,}",
            "Risk score ≥ 45",
            "metric-purple",
        )

    with columns[2]:
        metric_card(
            "CRITICAL",
            f"{critical:,}",
            "Highest severity",
            "metric-purple",
        )

    with columns[3]:
        metric_card(
            "FALSE POSITIVE RATE",
            f"{false_positive_rate:.2f}%",
            "Held-out test set",
            "metric-blue",
        )

    with columns[4]:
        metric_card(
            "BASELINE CONTAMINATION",
            f"{contamination:.2f}%",
            "Malicious sessions learned",
            "metric-grey",
        )

    st.write("")

    # --------------------------------------------------------
    # CHART ROW
    # --------------------------------------------------------

    chart_left, chart_right = st.columns([1.8, 1])

    # ---------------- RISK ACTIVITY ----------------

    with chart_left:

        st.markdown(
            '<div class="section-title">' "Risk Activity Over Time" "</div>",
            unsafe_allow_html=True,
        )

        time_column = find_time_column(df)

        if time_column is not None and "final_risk" in df.columns:

            timeline = df[[time_column, "final_risk"]].dropna().copy()

            timeline["date"] = timeline[time_column].dt.date

            daily = (
                timeline.groupby("date")
                .agg(
                    average_risk=(
                        "final_risk",
                        "mean",
                    ),
                    high_risk=(
                        "final_risk",
                        lambda x: (x >= 65).sum(),
                    ),
                    medium_risk=(
                        "final_risk",
                        lambda x: ((x >= 45) & (x < 65)).sum(),
                    ),
                )
                .reset_index()
            )

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=daily["date"],
                    y=daily["average_risk"],
                    mode="lines",
                    name="Average Risk",
                    line=dict(
                        color=MAUVE,
                        width=3,
                    ),
                    fill="tozeroy",
                    fillcolor="rgba(200,182,255,0.08)",
                )
            )

            fig.update_layout(
                height=330,
                margin=dict(
                    l=15,
                    r=15,
                    t=10,
                    b=10,
                ),
                paper_bgcolor=CARD,
                plot_bgcolor="#292A30",
                font=dict(color=MUTED),
                xaxis=dict(
                    gridcolor=BORDER,
                    showgrid=False,
                ),
                yaxis=dict(
                    gridcolor=BORDER,
                    range=[0, 100],
                    title="Risk",
                ),
                legend=dict(
                    orientation="h",
                ),
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        else:
            st.info("Risk timeline unavailable.")

    # ---------------- SEVERITY ----------------

    with chart_right:

        st.markdown(
            '<div class="section-title">' "Alerts by Severity" "</div>",
            unsafe_allow_html=True,
        )

        if "severity" in df.columns:

            severity_counts = (
                df["severity"]
                .value_counts()
                .reindex(
                    [
                        "CRITICAL",
                        "HIGH",
                        "MEDIUM",
                        "GUARDED",
                        "LOW",
                    ],
                    fill_value=0,
                )
            )

        elif "final_risk" in df.columns:

            severity_counts = df["final_risk"].apply(severity_from_risk).value_counts()

        else:
            severity_counts = pd.Series()

        if not severity_counts.empty:

            severity_counts = severity_counts[severity_counts > 0]

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=severity_counts.index,
                        values=severity_counts.values,
                        hole=0.65,
                        marker=dict(
                            colors=[
                                CRITICAL_COLOR,
                                HIGH_COLOR,
                                MEDIUM_COLOR,
                                GUARDED_COLOR,
                                LOW_COLOR,
                            ]
                        ),
                    )
                ]
            )

            fig.update_layout(
                height=330,
                margin=dict(
                    l=10,
                    r=10,
                    t=10,
                    b=10,
                ),
                paper_bgcolor=CARD,
                font=dict(color=MUTED),
                legend=dict(
                    orientation="v",
                ),
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    # --------------------------------------------------------
    # BOTTOM ROW
    # --------------------------------------------------------

    left, right = st.columns([1.8, 1])

    # ---------------- RECENT ALERTS ----------------

    with left:

        st.markdown(
            '<div class="section-title">' "Highest-Risk Activity" "</div>",
            unsafe_allow_html=True,
        )

        if "final_risk" in df.columns:

            alerts_df = (
                df[df["final_risk"] >= 45]
                .sort_values(
                    "final_risk",
                    ascending=False,
                )
                .head(7)
            )

            display_columns = []

            for column in [
                "user_id",
                "final_risk",
                "predicted_attack_type",
                "attack_type",
                "severity",
            ]:
                if column in alerts_df.columns:
                    display_columns.append(column)

            st.dataframe(
                alerts_df[display_columns],
                use_container_width=True,
                hide_index=True,
            )

    # ---------------- ATTACK TYPES ----------------

    with right:

        st.markdown(
            '<div class="section-title">' "Top Attack Types" "</div>",
            unsafe_allow_html=True,
        )

        attack_column = None

        if "predicted_attack_type" in df.columns:
            attack_column = "predicted_attack_type"

        elif "attack_type" in df.columns:
            attack_column = "attack_type"

        if attack_column:

            attack_data = df.copy()

            if "final_risk" in attack_data.columns:
                attack_data = attack_data[attack_data["final_risk"] >= 45]

            attack_counts = (
                attack_data[attack_column]
                .value_counts()
                .drop(
                    labels=["normal"],
                    errors="ignore",
                )
                .head(6)
                .sort_values()
            )

            fig = px.bar(
                x=attack_counts.values,
                y=attack_counts.index,
                orientation="h",
            )

            fig.update_traces(
                marker_color=MAUVE,
            )

            fig.update_layout(
                height=300,
                margin=dict(
                    l=5,
                    r=10,
                    t=5,
                    b=5,
                ),
                paper_bgcolor=CARD,
                plot_bgcolor="#292A30",
                font=dict(color=MUTED),
                xaxis=dict(
                    visible=False,
                ),
                yaxis=dict(
                    title=None,
                ),
                showlegend=False,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )


# ============================================================
# TWIN EXPLORER
# ============================================================

elif page == "Twin Explorer":

    st.markdown(
        '<div class="page-title">Twin Explorer</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        "Inspect the behavioral digital twin of an individual entity"
        "</div>",
        unsafe_allow_html=True,
    )

    if "user_id" not in df.columns:
        st.error("user_id unavailable.")
        st.stop()

    users = sorted(df["user_id"].dropna().unique())

    selected_user = st.selectbox(
        "Select entity",
        users,
    )

    user_df = df[df["user_id"] == selected_user].copy()

    time_column = find_time_column(user_df)

    if time_column:
        user_df = user_df.sort_values(time_column)

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        sessions = len(user_df)

        metric_card(
            "SESSIONS",
            str(sessions),
            selected_user,
            "metric-pink",
        )

    with c2:

        avg_risk = (
            user_df["final_risk"].mean() if "final_risk" in user_df.columns else 0
        )

        metric_card(
            "AVERAGE RISK",
            f"{avg_risk:.1f}",
            "Across observed sessions",
            "metric-purple",
        )

    with c3:

        max_risk = user_df["final_risk"].max() if "final_risk" in user_df.columns else 0

        metric_card(
            "PEAK RISK",
            f"{max_risk:.1f}",
            "Maximum observed risk",
            "metric-blue",
        )

    with c4:

        baseline = (
            user_df["baseline_source"].iloc[-1]
            if "baseline_source" in user_df.columns
            else "Unknown"
        )

        metric_card(
            "TWIN BASELINE",
            str(baseline).upper(),
            "Current baseline source",
            "metric-grey",
        )

    st.write("")

    if time_column and "final_risk" in user_df.columns:

        st.markdown(
            '<div class="section-title">' "Behavioral Risk Timeline" "</div>",
            unsafe_allow_html=True,
        )

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=user_df[time_column],
                y=user_df["final_risk"],
                mode="lines+markers",
                name="Risk",
                line=dict(
                    color=MAUVE,
                    width=2.5,
                ),
                marker=dict(
                    color=PETAL_FROST,
                    size=6,
                ),
            )
        )

        fig.add_hline(
            y=45,
            line_dash="dash",
            line_color=PERIWINKLE,
            annotation_text="Alert threshold",
        )

        fig.update_layout(
            height=360,
            paper_bgcolor=CARD,
            plot_bgcolor="#292A30",
            font=dict(color=MUTED),
            xaxis=dict(
                showgrid=False,
            ),
            yaxis=dict(
                gridcolor=BORDER,
                range=[0, 100],
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # DEVIATION PROFILE
    # --------------------------------------------------------

    deviation_columns = [
        column for column in user_df.columns if column.endswith("_deviation")
    ]

    if deviation_columns:

        st.markdown(
            '<div class="section-title">' "Current Behavioral Deviation" "</div>",
            unsafe_allow_html=True,
        )

        latest = user_df.iloc[-1]

        deviation = pd.DataFrame(
            {
                "feature": [
                    c.replace(
                        "_deviation",
                        "",
                    )
                    .replace("_", " ")
                    .title()
                    for c in deviation_columns
                ],
                "deviation": [latest[c] for c in deviation_columns],
            }
        )

        deviation = deviation.sort_values(
            "deviation",
            ascending=True,
        )

        fig = px.bar(
            deviation,
            x="deviation",
            y="feature",
            orientation="h",
        )

        fig.update_traces(
            marker_color=PERIWINKLE,
        )

        fig.update_layout(
            height=380,
            paper_bgcolor=CARD,
            plot_bgcolor="#292A30",
            font=dict(color=MUTED),
            xaxis=dict(
                gridcolor=BORDER,
                title="Deviation from learned baseline",
            ),
            yaxis=dict(
                title=None,
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )


# ============================================================
# ALERTS
# ============================================================

elif page == "Alerts":

    st.markdown(
        '<div class="page-title">Alert Queue</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        "Risk-ranked sessions requiring analyst attention"
        "</div>",
        unsafe_allow_html=True,
    )

    if "final_risk" not in df.columns:
        st.warning("final_risk unavailable.")
        st.stop()

    alerts = df[df["final_risk"] >= 45].copy()

    severity_filter = st.multiselect(
        "Severity",
        [
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "GUARDED",
            "LOW",
        ],
        default=[
            "CRITICAL",
            "HIGH",
            "MEDIUM",
        ],
    )

    if "severity" in alerts.columns:
        alerts = alerts[alerts["severity"].isin(severity_filter)]

    alerts = alerts.sort_values(
        "final_risk",
        ascending=False,
    )

    wanted = [
        "user_id",
        "final_risk",
        "severity",
        "predicted_attack_type",
        "classification_confidence",
        "multi_horizon_risk",
        "context_risk",
    ]

    available = [c for c in wanted if c in alerts.columns]

    st.dataframe(
        alerts[available],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# DRIFT TIMELINE
# ============================================================

elif page == "Drift Timeline":

    st.markdown(
        '<div class="page-title">Behavioral Drift</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        "Track gradual behavioral change across multiple time horizons"
        "</div>",
        unsafe_allow_html=True,
    )

    if "user_id" not in df.columns:
        st.stop()

    user = st.selectbox(
        "Entity",
        sorted(df["user_id"].dropna().unique()),
    )

    entity = df[df["user_id"] == user].copy()

    time_column = find_time_column(entity)

    horizons = [
        "immediate_risk",
        "short_term_risk",
        "medium_term_risk",
        "long_term_risk",
        "multi_horizon_risk",
    ]

    available = [h for h in horizons if h in entity.columns]

    if time_column and available:

        entity = entity.sort_values(time_column)

        fig = go.Figure()

        palette = [
            PETAL_FROST,
            MAUVE_LIGHT,
            MAUVE,
            PERIWINKLE,
            DIM_GREY,
        ]

        for column, colour in zip(
            available,
            palette,
        ):

            fig.add_trace(
                go.Scatter(
                    x=entity[time_column],
                    y=entity[column],
                    mode="lines",
                    name=column.replace("_", " ").title(),
                    line=dict(
                        color=colour,
                        width=2,
                    ),
                )
            )

        fig.update_layout(
            height=480,
            paper_bgcolor=CARD,
            plot_bgcolor="#292A30",
            font=dict(color=MUTED),
            xaxis=dict(
                showgrid=False,
            ),
            yaxis=dict(
                gridcolor=BORDER,
                range=[0, 100],
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )


# ============================================================
# TRUST LEDGER
# ============================================================

elif page == "Trust Ledger":

    st.markdown(
        '<div class="page-title">Trust Ledger</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        "Audit which sessions are allowed to modify the behavioral twin"
        "</div>",
        unsafe_allow_html=True,
    )

    ledger = first_available(
        online_df,
        trust_df,
    )

    if ledger.empty:
        st.warning("Run the trust-gated or online pipeline first.")
        st.stop()

    if "trust_decision" in ledger.columns:

        counts = ledger["trust_decision"].value_counts()

        c1, c2, c3 = st.columns(3)

        with c1:
            metric_card(
                "TRUSTED",
                str(
                    counts.get(
                        "TRUST",
                        0,
                    )
                ),
                "Allowed to update twin",
                "metric-blue",
            )

        with c2:
            metric_card(
                "QUARANTINED",
                str(
                    counts.get(
                        "QUARANTINE",
                        0,
                    )
                ),
                "Held for additional evidence",
                "metric-purple",
            )

        with c3:
            metric_card(
                "REJECTED",
                str(
                    counts.get(
                        "REJECT",
                        0,
                    )
                ),
                "Blocked from adaptation",
                "metric-pink",
            )

    st.write("")

    columns = [
        "user_id",
        "session_id",
        "final_risk",
        "trust_decision",
        "attack_type",
        "is_attack",
    ]

    available = [c for c in columns if c in ledger.columns]

    st.dataframe(
        ledger[available],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# EVALUATION
# ============================================================

elif page == "Evaluation":

    st.markdown(
        '<div class="page-title">Model Evaluation</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        "Performance on the chronologically held-out test set"
        "</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card(
            "PRECISION",
            "0.874",
            "Held-out detection",
            "metric-pink",
        )

    with c2:
        metric_card(
            "RECALL",
            "0.988",
            "Held-out detection",
            "metric-purple",
        )

    with c3:
        metric_card(
            "F1",
            "0.927",
            "Binary detection",
            "metric-blue",
        )

    with c4:
        metric_card(
            "MACRO-F1",
            "0.971",
            "Attack identification",
            "metric-grey",
        )

    st.write("")

    st.markdown(
        '<div class="section-title">' "Held-Out Confusion Matrix" "</div>",
        unsafe_allow_html=True,
    )

    confusion = pd.DataFrame(
        [
            [525, 12],
            [1, 83],
        ],
        index=[
            "Actual Normal",
            "Actual Attack",
        ],
        columns=[
            "Predicted Normal",
            "Predicted Attack",
        ],
    )

    fig = px.imshow(
        confusion,
        text_auto=True,
        aspect="auto",
        color_continuous_scale=[
            [0, DIM_GREY],
            [0.5, PERIWINKLE],
            [1, MAUVE],
        ],
    )

    fig.update_layout(
        height=350,
        paper_bgcolor=CARD,
        plot_bgcolor="#292A30",
        font=dict(color=TEXT),
        coloraxis_showscale=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.markdown("""
        **Evaluation protocol**

        SentinelTwin uses a chronological **70% train /
        10% validation / 20% test split**. The held-out
        test period is never used for classifier training
        or hyperparameter selection.
        """)


# ============================================================
# FOOTER
# ============================================================
st.markdown(
    f'<div style="'
    f"margin-top:40px;"
    f"padding-top:15px;"
    f"border-top:1px solid {BORDER};"
    f"color:{MUTED};"
    f"font-size:11px;"
    f"display:flex;"
    f"justify-content:space-between;"
    f'">'
    f"<span>SentinelTwin · Adaptive Behavioral Digital Twin</span>"
    f"<span>Behavioral Risk Intelligence</span>"
    f"</div>",
    unsafe_allow_html=True,
)
