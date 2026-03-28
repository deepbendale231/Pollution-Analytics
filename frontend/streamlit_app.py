from __future__ import annotations

import streamlit as st

from frontend.api_client import get_health_check
from frontend.pages import city_deep_dive, compare_cities, forecast, health_risk, overview, predict_aqi

st.set_page_config(
    page_title="Pollution Analytics Dashboard",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide the default Streamlit multipage navigation in sidebar.
st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {display: none;}

        /* Fix invisible text in sidebar selectboxes */
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] div {
            color: black !important;
        }
        [data-testid="stSidebar"] .stSelectbox span {
            color: black !important;
        }
        [data-testid="stSidebar"] select {
            color: black !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

CITIES = [
    "Delhi",
    "Mumbai",
    "Chennai",
    "Kolkata",
    "Bangalore",
    "Hyderabad",
    "Pune",
    "Ahmedabad",
]

PAGES = [
        ("🏠 Overview", "Overview"),
        ("🔮 Predict AQI", "Predict AQI"),
        ("🏙️ City Deep Dive", "City Deep Dive"),
        ("📊 Compare Cities", "Compare Cities"),
        ("📈 Forecast", "Forecast"),
        ("❤️ Health Risk", "Health Risk"),
]


def _apply_designer_theme() -> None:
        st.markdown(
                """
                <style>
                @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Space+Grotesk:wght@400;500;700&display=swap');

                :root {
                    --paper: #fff8ee;
                    --ink: #11212d;
                    --accent: #e0582d;
                    --accent-soft: #f98f53;
                    --teal: #0f8b8d;
                    --gold: #f3b61f;
                    --mist: #ffefe0;
                }

                .stApp {
                    font-family: 'Space Grotesk', sans-serif;
                    color: var(--ink);
                    background:
                        radial-gradient(circle at 8% 10%, rgba(243, 182, 31, 0.22), transparent 28%),
                        radial-gradient(circle at 92% 24%, rgba(224, 88, 45, 0.24), transparent 30%),
                        radial-gradient(circle at 65% 84%, rgba(15, 139, 141, 0.20), transparent 34%),
                        linear-gradient(135deg, #fff8ee 0%, #fff1df 45%, #ffe7cf 100%);
                }

                .block-container {
                    padding-top: 1.2rem !important;
                    padding-bottom: 2rem !important;
                }

                h1, h2, h3 {
                    font-family: 'Bebas Neue', sans-serif !important;
                    letter-spacing: 0.8px;
                }

                section[data-testid="stSidebar"] {
                    background:
                        linear-gradient(168deg, rgba(17, 33, 45, 0.95) 0%, rgba(11, 27, 37, 0.94) 52%, rgba(15, 139, 141, 0.92) 100%);
                    border-right: 2px solid rgba(249, 143, 83, 0.45);
                }

                section[data-testid="stSidebar"] h1,
                section[data-testid="stSidebar"] h2,
                section[data-testid="stSidebar"] h3,
                section[data-testid="stSidebar"] label,
                section[data-testid="stSidebar"] p,
                section[data-testid="stSidebar"] span,
                section[data-testid="stSidebar"] div {
                    color: #fffaf2 !important;
                }

                .hero-shell {
                    margin: 0 0 1rem 0;
                    padding: 1rem 1.15rem 0.85rem 1.15rem;
                    border-radius: 20px;
                    background:
                        linear-gradient(120deg, rgba(17, 33, 45, 0.92) 0%, rgba(15, 139, 141, 0.90) 42%, rgba(224, 88, 45, 0.90) 100%);
                    border: 2px solid rgba(255, 255, 255, 0.38);
                    box-shadow: 0 18px 42px rgba(17, 33, 45, 0.26);
                    animation: liftIn 0.62s ease-out;
                }

                .hero-kicker {
                    color: #ffeacc;
                    font-size: 0.8rem;
                    text-transform: uppercase;
                    letter-spacing: 0.2em;
                    font-weight: 700;
                }

                .hero-title {
                    margin-top: 0.32rem;
                    color: #ffffff;
                    font-family: 'Bebas Neue', sans-serif;
                    font-size: 2.2rem;
                    line-height: 1.0;
                    letter-spacing: 1px;
                }

                .hero-sub {
                    margin-top: 0.36rem;
                    color: #fff6ea;
                    font-size: 0.94rem;
                }

                .sidebar-active-page {
                    margin-top: 0.35rem;
                    margin-bottom: 0.75rem;
                    padding: 0.45rem 0.65rem;
                    border-radius: 999px;
                    background: linear-gradient(90deg, rgba(243, 182, 31, 0.95), rgba(249, 143, 83, 0.95));
                    color: #0d1b24 !important;
                    font-weight: 700;
                    text-align: center;
                    letter-spacing: 0.02em;
                    box-shadow: 0 8px 20px rgba(243, 182, 31, 0.25);
                }

                section[data-testid="stSidebar"] .stButton > button {
                    border-radius: 14px;
                    border: 1.5px solid rgba(255, 255, 255, 0.24);
                    background: linear-gradient(110deg, rgba(255, 255, 255, 0.10), rgba(255, 255, 255, 0.04));
                    color: #fffaf2 !important;
                    font-weight: 700;
                    letter-spacing: 0.02em;
                    padding: 0.56rem 0.72rem;
                    transition: all 0.18s ease;
                    box-shadow: 0 5px 16px rgba(6, 16, 24, 0.32);
                }

                section[data-testid="stSidebar"] .stButton > button:hover {
                    border-color: rgba(243, 182, 31, 0.85);
                    transform: translateY(-1px);
                    box-shadow: 0 10px 20px rgba(8, 21, 29, 0.35);
                    background: linear-gradient(110deg, rgba(243, 182, 31, 0.24), rgba(224, 88, 45, 0.22));
                }

                div[data-testid="metric-container"] {
                    border-radius: 18px;
                    border: 1px solid rgba(15, 139, 141, 0.26);
                    background: rgba(255, 255, 255, 0.76);
                    backdrop-filter: blur(6px);
                    box-shadow: 0 10px 26px rgba(17, 33, 45, 0.12);
                    padding: 0.35rem 0.45rem;
                    animation: liftIn 0.52s ease-out;
                }

                div[data-testid="stPlotlyChart"],
                div[data-testid="stDataFrame"] {
                    border-radius: 18px;
                    border: 1px solid rgba(17, 33, 45, 0.10);
                    background: rgba(255, 255, 255, 0.70);
                    box-shadow: 0 12px 28px rgba(17, 33, 45, 0.10);
                    padding: 0.32rem;
                }

                @keyframes liftIn {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                </style>
                """,
                unsafe_allow_html=True,
        )


def _render_hero(page: str, city: str, days: int) -> None:
        st.markdown(
                f"""
                <div class="hero-shell">
                    <div class="hero-kicker">Urban Intelligence Layer</div>
                    <div class="hero-title">{page}</div>
                    <div class="hero-sub">City focus: <b>{city}</b> | Time window: <b>{days} days</b></div>
                </div>
                """,
                unsafe_allow_html=True,
        )


def _render_sidebar_nav() -> None:
        for label, page in PAGES:
                if st.sidebar.button(label, use_container_width=True):
                        st.session_state.page = page

        active_label = next((label for label, page in PAGES if page == st.session_state.page), "🏠 Overview")
        st.sidebar.markdown(
                f"<div class=\"sidebar-active-page\">Active: {active_label}</div>",
                unsafe_allow_html=True,
        )

@st.cache_data(ttl=60)
def get_api_status() -> bool:
    response = get_health_check()
    return response is not None


def _render_api_status() -> None:
    is_up = get_api_status()
    if is_up:
        st.sidebar.markdown("🟢 API Status: Online")
    else:
        st.sidebar.markdown("🔴 API Status: Offline")


def main() -> None:
    _apply_designer_theme()

    st.sidebar.title("Pollution Analytics Dashboard")

    selected_city = st.sidebar.selectbox("Select City", options=CITIES, index=0)
    selected_days = st.sidebar.selectbox("Days Range", options=[7, 14, 30, 90], index=2)

    if "page" not in st.session_state:
        st.session_state.page = "Overview"

    st.sidebar.divider()

    _render_sidebar_nav()

    st.sidebar.divider()
    _render_api_status()

    _render_hero(st.session_state.page, selected_city, selected_days)

    if st.session_state.page == "Overview":
        overview.render(selected_city, selected_days)
    elif st.session_state.page == "Predict AQI":
        predict_aqi.render(selected_city, selected_days)
    elif st.session_state.page == "City Deep Dive":
        city_deep_dive.render(selected_city, selected_days)
    elif st.session_state.page == "Compare Cities":
        compare_cities.render(selected_city, selected_days)
    elif st.session_state.page == "Forecast":
        forecast.render(selected_city, selected_days)
    elif st.session_state.page == "Health Risk":
        health_risk.render(selected_city, selected_days)


if __name__ == "__main__":
    main()
