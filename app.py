from pathlib import Path
import base64
import json
import sqlite3
import time

import pandas as pd
import streamlit as st
from PIL import Image

from agents.document import DocumentAgent
from agents.inventory import InventoryAgent
from agents.decision import DecisionAgent
from agents.report import ReportAgent
from agents.diagnostic import DiagnosticAgent
from agents.vision import VisionAgent

import re
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CATALOGUES = {
    "Apollo Tractors": BASE_DIR / "CATALOGUES" / "APOLLO_TRACTORS.pdf",
    "Mahindra Scorpio": BASE_DIR / "CATALOGUES" / "MAHINDRA_SCORPIO.pdf",
    "Mahindra Thar": BASE_DIR / "CATALOGUES" / "MAHINDRA_THAR.pdf",
    "Tata Indica": BASE_DIR / "CATALOGUES" / "TATA_INDICA.pdf",
}

UPLOAD_DIR = BASE_DIR / "CATALOGUES" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

VISION_UPLOAD_DIR = BASE_DIR / "assets" / "vision_uploads"
VISION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

INVENTORY_DB = BASE_DIR / "inventory" / "central_inventory.db"

ASSETS_DIR = BASE_DIR / "assets"
LOGO_ICON_PATH = ASSETS_DIR / "persistent_icon.png"
ROBOT_ICON_PATH = ASSETS_DIR / "robot_image.jpeg"


# ============================================================
# BRAND ASSETS
# ============================================================

def _load_image_base64(path):
    """Load an image file as a base64 data-URI for inline HTML/CSS use."""

    if not path.exists():
        return None

    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"

    encoded = base64.b64encode(
        path.read_bytes()
    ).decode("utf-8")

    return f"data:{mime};base64,{encoded}"


LOGO_DATA_URI = _load_image_base64(LOGO_ICON_PATH)
ROBOT_DATA_URI = _load_image_base64(ROBOT_ICON_PATH)

_page_icon = "⚙️"

if LOGO_ICON_PATH.exists():

    try:
        _page_icon = Image.open(LOGO_ICON_PATH)
    except Exception:
        _page_icon = "⚙️"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="PERSISTENT AI",
    page_icon=_page_icon,
    layout="wide",
)


# ============================================================
# CSS (SUPERCHARGED FOR MODERN UI)
# ============================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

    :root {
        --persistent-orange: #EC632B;
        --persistent-orange-dark: #D6541F;
        --persistent-orange-light: #FFF0EB;
        --persistent-navy: #14213D;
        --persistent-navy-soft: #2C3B5C;
        --persistent-bg: #F8FAFC; 
        --persistent-surface: #FFFFFF;
        --persistent-border: #E2E8F0;
        --text-main: #0F172A;
        --text-muted: #64748B;
        
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -1px rgba(0, 0, 0, 0.04);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        --shadow-hover: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
    }

    /* ---------------------------------------------------- */
    /* Global Typography & Body                             */
    /* ---------------------------------------------------- */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: var(--text-main);
    }

    [data-testid="stAppViewContainer"] {
        background-color: var(--persistent-bg);
    }

    [data-testid="stHeader"] {
        background-color: rgba(248, 250, 252, 0.7);
        backdrop-filter: blur(10px);
    }

    /* ---------------------------------------------------- */
    /* Main content "page surface"                          */
    /* ---------------------------------------------------- */
    [data-testid="stMain"] .block-container {
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        max-width: 1320px;
    }

    /* ---------------------------------------------------- */
    /* Sidebar styling                                      */
    /* ---------------------------------------------------- */
    [data-testid="stSidebar"] {
        background-color: var(--persistent-surface);
        border-right: 1px solid var(--persistent-border);
        box-shadow: var(--shadow-sm);
    }

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stFileUploader label {
        color: var(--text-main);
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }

    [data-testid="stSidebar"] h2 {
        color: var(--persistent-navy);
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 1.1rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        border-left: 4px solid var(--persistent-orange);
        padding-left: 0.75rem;
        margin-top: 1rem;
        background: linear-gradient(90deg, var(--persistent-orange-light) 0%, transparent 100%);
        padding-top: 4px;
        padding-bottom: 4px;
        border-radius: 0 4px 4px 0;
    }

    /* Sidebar brand header */
    .persistent-brand {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 2rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--persistent-border);
    }

    .persistent-brand img {
        height: 35px;
        width: auto;
        filter: drop-shadow(0px 2px 4px rgba(236, 99, 43, 0.3));
    }

    .persistent-brand span {
        font-family: 'Poppins', sans-serif;
        font-size: 1.5rem;
        font-weight: 800;
        color: var(--persistent-navy);
        letter-spacing: -0.02em;
    }

    /* ---------------------------------------------------- */
    /* Headings                                             */
    /* ---------------------------------------------------- */
    h1, h2, h3 {
        color: var(--persistent-navy);
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
    }

    .main-title {
        font-family: 'Poppins', sans-serif;
        font-size: 2.5rem;
        font-weight: 800;
        color: var(--persistent-navy);
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
        text-shadow: 0px 1px 2px rgba(0,0,0,0.05);
    }

    .main-title-underline {
        width: 80px;
        height: 6px;
        background: linear-gradient(90deg, var(--persistent-orange), #FFB885);
        border-radius: 6px;
        margin-bottom: 2rem;
        box-shadow: 0 2px 4px rgba(236, 99, 43, 0.3);
    }

    /* ---------------------------------------------------- */
    /* Buttons                                              */
    /* ---------------------------------------------------- */
    .stButton > button {
        border-radius: var(--radius-md);
        font-weight: 600;
        font-size: 0.95rem;
        border: 1px solid var(--persistent-border);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: var(--shadow-sm);
        padding: 0.5rem 1rem;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--persistent-orange) 0%, var(--persistent-orange-dark) 100%);
        border: none;
        color: #FFFFFF;
        box-shadow: 0 4px 10px rgba(236, 99, 43, 0.3);
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #F07643 0%, var(--persistent-orange) 100%);
        box-shadow: 0 6px 15px rgba(236, 99, 43, 0.4);
    }

    .stButton > button[kind="secondary"] {
        background-color: var(--persistent-surface);
        color: var(--persistent-navy);
    }

    .stButton > button[kind="secondary"]:hover {
        border-color: var(--persistent-orange);
        color: var(--persistent-orange);
    }

    .stDownloadButton > button {
        border-radius: var(--radius-md);
        font-weight: 600;
        background: linear-gradient(135deg, var(--persistent-navy) 0%, var(--persistent-navy-soft) 100%);
        color: #FFFFFF;
        border: none;
        box-shadow: 0 4px 10px rgba(20, 33, 61, 0.2);
        transition: all 0.2s ease;
    }

    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(20, 33, 61, 0.3);
    }

    /* ---------------------------------------------------- */
    /* Inputs                                               */
    /* ---------------------------------------------------- */
    .stTextInput input,
    .stSelectbox div[data-baseweb="select"] > div,
    .stFileUploader section {
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--persistent-border);
        background-color: var(--persistent-surface);
        transition: all 0.2s ease;
    }

    .stTextInput input:focus,
    .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: var(--persistent-orange) !important;
        box-shadow: 0 0 0 3px var(--persistent-orange-light) !important;
    }

    /* Radio buttons accent */
    .stRadio input[type="radio"] {
        accent-color: var(--persistent-orange);
    }
    
    .stRadio div[role="radiogroup"] > label {
        background: var(--persistent-surface);
        padding: 0.5rem 1rem;
        border-radius: var(--radius-sm);
        border: 1px solid var(--persistent-border);
        margin-bottom: 0.25rem;
        transition: all 0.2s ease;
    }
    
    .stRadio div[role="radiogroup"] > label:hover {
        border-color: var(--persistent-orange);
        background-color: var(--persistent-orange-light);
    }

    /* ---------------------------------------------------- */
    /* Status / alert boxes                                 */
    /* ---------------------------------------------------- */
    [data-testid="stAlertContentSuccess"] {
        color: #1E7A3E;
    }
    
    div[data-baseweb="notification"] {
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--persistent-border);
    }

    /* ---------------------------------------------------- */
    /* Metrics as Dashboard Cards                           */
    /* ---------------------------------------------------- */
    [data-testid="stMetric"] {
        background-color: var(--persistent-surface);
        border: 1px solid var(--persistent-border);
        border-radius: var(--radius-md);
        padding: 1.25rem;
        box-shadow: var(--shadow-md);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        text-align: center;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-hover);
        border-color: var(--persistent-orange-light);
    }

    [data-testid="stMetricValue"] {
        color: var(--persistent-orange);
        font-family: 'Poppins', sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-muted);
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ---------------------------------------------------- */
    /* Expanders                                            */
    /* ---------------------------------------------------- */
    details {
        border: 1px solid var(--persistent-border) !important;
        border-radius: var(--radius-md) !important;
        background-color: var(--persistent-surface);
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
        margin-bottom: 1rem;
    }
    
    details:hover {
        box-shadow: var(--shadow-md);
    }

    summary {
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        color: var(--persistent-navy);
        padding: 1rem !important;
        background-color: var(--persistent-surface);
        border-radius: var(--radius-md);
    }

    /* ---------------------------------------------------- */
    /* Dataframes / tables                                  */
    /* ---------------------------------------------------- */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--persistent-border);
        border-radius: var(--radius-md);
        overflow-x: auto;
        overflow-y: hidden;
        box-shadow: var(--shadow-sm);
        background: var(--persistent-surface);
        max-width: 100%;
    }

    [data-testid="stDataFrame"] > div {
        max-width: 100%;
    }

    [data-testid="stExpanderDetails"],
    details {
        overflow-x: auto;
    }

    /* ---------------------------------------------------- */
    /* Dividers                                             */
    /* ---------------------------------------------------- */
    hr {
        border-top: 1px solid var(--persistent-border);
        margin: 2.5rem 0;
    }

    /* ---------------------------------------------------- */
    /* Chat elements (Diagnostic Assistant)                 */
    /* ---------------------------------------------------- */
    [data-testid="stChatInput"] {
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-md);
        border: 1px solid var(--persistent-border);
    }

    [data-testid="stChatMessage"] {
        border-radius: var(--radius-md);
        background-color: var(--persistent-surface);
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--persistent-border);
        padding: 1rem;
        margin-bottom: 1rem;
    }

    /* ---------------------------------------------------- */
    /* AI Workflow Hub (welcome screen)                     */
    /* ---------------------------------------------------- */
    .hub-card {
        background: var(--persistent-surface);
        border: 1px solid var(--persistent-border);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-md);
        padding: 2rem 2.25rem 2.5rem 2.25rem;
        margin-bottom: 1rem;
    }

    .hub-eyebrow {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 0.78rem;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: var(--persistent-orange);
        margin-bottom: 0.4rem;
    }

    .hub-title {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 1.5rem;
        color: var(--persistent-navy);
        margin-bottom: 0.35rem;
    }

    .hub-subtitle {
        color: var(--text-muted);
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }

    .workflow-stepper {
        position: relative;
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
    }

    .workflow-track {
        position: absolute;
        top: 15px;
        left: 5%;
        right: 5%;
        height: 3px;
        background: linear-gradient(
            90deg,
            var(--persistent-orange) 0%,
            #FFD9BE 100%
        );
        border-radius: 3px;
        z-index: 0;
    }

    .workflow-step {
        position: relative;
        z-index: 1;
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: 0.6rem;
    }

    .workflow-step-badge {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background: var(--persistent-orange);
        color: #FFFFFF;
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 3px 8px rgba(236, 99, 43, 0.35);
        border: 3px solid var(--persistent-surface);
    }

    .workflow-step-icon {
        width: 56px;
        height: 56px;
        border-radius: var(--radius-md);
        background: var(--persistent-navy);
        color: #FFFFFF;
        font-size: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: var(--shadow-md);
    }

    .workflow-step-label {
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        font-size: 0.82rem;
        color: var(--persistent-navy);
        line-height: 1.25;
        max-width: 110px;
    }

    @media (max-width: 900px) {
        .workflow-stepper {
            flex-wrap: wrap;
        }
        .workflow-track {
            display: none;
        }
        .workflow-step {
            flex: 1 1 30%;
        }
    }

    /* ---------------------------------------------------- */
    /* Pipeline status stepper                               */
    /* ---------------------------------------------------- */
    .pipeline-card {
        background: var(--persistent-surface);
        border: 1px solid var(--persistent-border);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-sm);
        padding: 1.5rem 1.75rem;
        margin-bottom: 0.5rem;
    }

    .pipeline-heading {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 1.05rem;
        color: var(--persistent-navy);
        margin-bottom: 1.4rem;
    }

    .pipeline-stepper {
        position: relative;
        display: flex;
        justify-content: space-between;
    }

    .pipeline-track {
        position: absolute;
        top: 17px;
        left: 6%;
        right: 6%;
        height: 3px;
        background: var(--persistent-border);
        border-radius: 3px;
        z-index: 0;
    }

    .pipeline-track-fill {
        position: absolute;
        top: 17px;
        left: 6%;
        height: 3px;
        background: var(--persistent-orange);
        border-radius: 3px;
        z-index: 0;
        transition: width 0.3s ease;
    }

    .pipeline-step {
        position: relative;
        z-index: 1;
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: 0.5rem;
    }

    .pipeline-step-dot {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        font-weight: 700;
        border: 3px solid var(--persistent-surface);
        box-shadow: var(--shadow-sm);
    }

    .pipeline-step.done .pipeline-step-dot {
        background: var(--persistent-orange);
        color: #FFFFFF;
    }

    .pipeline-step.pending .pipeline-step-dot {
        background: #E2E8F0;
        color: var(--text-muted);
    }

    .pipeline-step-label {
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        font-size: 0.8rem;
        color: var(--persistent-navy);
    }

    .pipeline-step.pending .pipeline-step-label {
        color: var(--text-muted);
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CSS - FLOATING DIAGNOSTIC ASSISTANT + INVENTORY MODAL
# ============================================================
# Kept as a separate injection (rather than folded into the main
# CSS block above) purely so the embedded base64 image data below
# never has to sit inside an f-string alongside the large amount of
# literal `{ }` CSS syntax in the main stylesheet.
# ============================================================

_robot_bg_rule = (
    f"background-image: url('{ROBOT_DATA_URI}');"
    if ROBOT_DATA_URI
    else "background: linear-gradient(135deg, var(--persistent-orange), var(--persistent-orange-dark));"
)

st.markdown(
    f"""
    <style>

    /* ---------------------------------------------------- */
    /* Floating robot launcher (bottom-right)                */
    /* ---------------------------------------------------- */

    .st-key-robot_fab_container {{
        position: fixed;
        bottom: 26px;
        right: 26px;
        z-index: 10001;
        width: 76px !important;
    }}

    .st-key-robot_fab_container [data-testid="stElementContainer"] {{
        width: 76px !important;
    }}

    .st-key-robot_fab_container button {{
        width: 76px;
        height: 76px;
        min-width: 76px;
        border-radius: 50%;
        padding: 0;
        font-size: 0;
        color: transparent;
        {_robot_bg_rule}
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        border: 3px solid #FFFFFF;
        box-shadow: 0 10px 24px rgba(20, 33, 61, 0.35);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        animation: robot-float 3.2s ease-in-out infinite;
    }}

    .st-key-robot_fab_container button:hover {{
        transform: translateY(-4px) scale(1.05);
        box-shadow: 0 14px 30px rgba(236, 99, 43, 0.45);
    }}

    @keyframes robot-float {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-6px); }}
    }}

    /* ---------------------------------------------------- */
    /* Floating diagnostic assistant panel                   */
    /* ---------------------------------------------------- */

    .st-key-diagnostic_panel_container {{
        position: fixed;
        bottom: 116px;
        right: 26px;
        width: 400px;
        max-width: 92vw;
        max-height: 68vh;
        overflow-y: auto;
        background: var(--persistent-surface);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-hover);
        border: 1px solid var(--persistent-border);
        padding: 1.1rem 1.25rem 1.4rem 1.25rem;
        z-index: 10000;
        animation: panel-pop 0.18s ease-out;
    }}

    @keyframes panel-pop {{
        0% {{ opacity: 0; transform: translateY(12px) scale(0.98); }}
        100% {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}

    .diagnostic-panel-header {{
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.15rem;
    }}

    .diagnostic-panel-header img {{
        width: 34px;
        height: 34px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid var(--persistent-orange-light);
    }}

    .diagnostic-panel-header span {{
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 1.05rem;
        color: var(--persistent-navy);
    }}

    .st-key-diagnostic_panel_close button {{
        border: none;
        box-shadow: none;
        background: transparent;
        color: var(--text-muted);
        font-weight: 700;
        padding: 0.2rem 0.5rem;
    }}

    .st-key-diagnostic_panel_close button:hover {{
        color: var(--persistent-orange);
        background: var(--persistent-orange-light);
        transform: none;
    }}

    /* ---------------------------------------------------- */
    /* Inventory modal (overlay)                             */
    /* ---------------------------------------------------- */

    .st-key-inventory_modal_backdrop {{
        position: fixed;
        inset: 0;
        z-index: 10050;
        background: rgba(15, 23, 42, 0.55);
        backdrop-filter: blur(6px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2.5rem 1.5rem;
    }}

    .st-key-inventory_modal_card {{
        background: var(--persistent-surface);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-hover);
        padding: 1.5rem 2rem 2rem 2rem;
        width: min(880px, 94vw);
        max-height: 85vh;
        overflow-y: auto;
    }}

    .st-key-inventory_close_btn button {{
        background: var(--persistent-orange-light);
        color: var(--persistent-orange-dark);
        border: 1px solid var(--persistent-orange-light);
        font-weight: 700;
    }}

    .st-key-inventory_close_btn button:hover {{
        background: var(--persistent-orange);
        color: #FFFFFF;
    }}

    /* ---------------------------------------------------- */
    /* View Inventory sidebar button                         */
    /* ---------------------------------------------------- */

    .st-key-view_inventory_btn button {{
        background: linear-gradient(135deg, #FFF4EE 0%, #FFE8DB 100%);
        color: var(--persistent-navy);
        border: 1px solid #FBD8C4;
        font-weight: 700;
    }}

    .st-key-view_inventory_btn button:hover {{
        border-color: var(--persistent-orange);
        color: var(--persistent-orange-dark);
    }}

    @media (max-width: 640px) {{
        .st-key-diagnostic_panel_container {{
            right: 4vw;
            width: 92vw;
            bottom: 108px;
        }}
        .st-key-robot_fab_container {{
            right: 18px;
            bottom: 18px;
        }}
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "document_result": None,
    "bom": None,
    "analysis_mode": None,
    "inventory_result": None,
    "decision_result": None,
    "report_result": None,
    "approved": False,
    "rejected": False,
    "pipeline_running": False,
    "show_inventory": False,
    "uploaded_catalogue": None,
    "uploaded_catalogue_name": None,
    "diagnostic_result": None,
    "diagnostic_symptom": None,
    "assembly_query": "",
    "show_diagnostic_panel": False,
    "catalogue_pdf_path": None,
    "input_type": "PDF Catalogue",
    "uploaded_image": None,
    "uploaded_image_name": None,
    "vision_result": None,
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# RESET RESULTS
# ============================================================


def markdown_to_pdf(markdown_text):
    """
    Convert the existing Markdown report into a professionally formatted PDF.

    IMPORTANT:
    - Does not generate new report content.
    - Does not add new sections.
    - Does not modify the report's information.
    - Only changes the visual formatting.
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Final Report",
    )

    styles = getSampleStyleSheet()

    # ---------------------------------------------------------
    # Styles
    # ---------------------------------------------------------

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        alignment=TA_LEFT,
        spaceAfter=16,
    )

    h2_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        spaceBefore=14,
        spaceAfter=9,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "ReportBullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=5,
    )

    bold_body_style = ParagraphStyle(
        "BoldBody",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def escape_xml(text):
        """Escape characters that have special meaning in ReportLab XML."""
        text = str(text)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def inline_markdown(text):
        """
        Convert basic Markdown formatting to ReportLab-compatible
        formatting without changing the actual information.
        """

        text = escape_xml(text)

        # Bold: **text**
        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"<b>\1</b>",
            text
        )

        # Italic: *text*
        text = re.sub(
            r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)",
            r"<i>\1</i>",
            text
        )

        # Inline code: `text`
        text = re.sub(
            r"`(.*?)`",
            r"<font name='Courier'>\1</font>",
            text
        )

        return text

    def split_markdown_row(line):
        """
        Split a Markdown table row while preserving cell contents.
        """

        line = line.strip()

        if line.startswith("|"):
            line = line[1:]

        if line.endswith("|"):
            line = line[:-1]

        return [cell.strip() for cell in line.split("|")]

    def is_table_separator(line):
        """
        Detect Markdown table separator:
        |------|------|
        """

        cells = split_markdown_row(line)

        if not cells:
            return False

        for cell in cells:
            cell = cell.strip()

            if not re.fullmatch(r":?-+:?", cell):
                return False

        return True

    def make_table(rows):
        """
        Convert Markdown table rows into a ReportLab table.
        """

        if not rows:
            return None

        processed_rows = []

        for row_index, row in enumerate(rows):

            processed_row = []

            for cell in row:

                cell_text = inline_markdown(cell)

                if row_index == 0:
                    cell_text = f"<b>{cell_text}</b>"

                processed_row.append(
                    Paragraph(
                        cell_text,
                        body_style
                    )
                )

            processed_rows.append(processed_row)

        # Calculate number of columns
        num_columns = max(
            len(row)
            for row in processed_rows
        )

        # Make rows equal length
        for row in processed_rows:

            while len(row) < num_columns:
                row.append(
                    Paragraph("", body_style)
                )

        # Available page width
        available_width = (
            A4[0]
            - 16 * mm
            - 16 * mm
        )

        # Equal column widths initially
        col_width = available_width / num_columns

        table = Table(
            processed_rows,
            colWidths=[col_width] * num_columns,
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle(
                [
                    # Header
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#F1F3F5"),
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#202124"),
                    ),

                    # Borders
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#DADCE0"),
                    ),

                    # Padding
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),

                    # Alignment
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                ]
            )
        )

        return table

    # ---------------------------------------------------------
    # Parse Markdown
    # ---------------------------------------------------------

    lines = markdown_text.splitlines()

    story = []

    i = 0

    while i < len(lines):

        line = lines[i].strip()

        # -----------------------------------------------------
        # Empty line
        # -----------------------------------------------------

        if not line:
            story.append(Spacer(1, 4))
            i += 1
            continue

        # -----------------------------------------------------
        # H1
        # -----------------------------------------------------

        if line.startswith("# "):

            text = line[2:].strip()

            story.append(
                Paragraph(
                    inline_markdown(text),
                    title_style
                )
            )

            i += 1
            continue

        # -----------------------------------------------------
        # H2
        # -----------------------------------------------------

        if line.startswith("## "):

            text = line[3:].strip()

            story.append(
                Paragraph(
                    inline_markdown(text),
                    h2_style
                )
            )

            i += 1
            continue

        # -----------------------------------------------------
        # Horizontal rule
        # -----------------------------------------------------

        if line in ["---", "***", "___"]:

            from reportlab.platypus import HRFlowable

            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.7,
                    color=colors.HexColor("#DADCE0"),
                    spaceBefore=5,
                    spaceAfter=10,
                )
            )

            i += 1
            continue

        # -----------------------------------------------------
        # Markdown table
        # -----------------------------------------------------

        if line.startswith("|"):

            table_rows = []

            while i < len(lines):

                current_line = lines[i].strip()

                if not current_line.startswith("|"):
                    break

                # Skip Markdown separator row
                if not is_table_separator(current_line):
                    table_rows.append(
                        split_markdown_row(current_line)
                    )

                i += 1

            table = make_table(table_rows)

            if table:
                story.append(
                    KeepTogether(
                        [
                            table,
                            Spacer(1, 10),
                        ]
                    )
                )

            continue

        # -----------------------------------------------------
        # Bullet list
        # -----------------------------------------------------

        if line.startswith("- "):

            text = line[2:].strip()

            story.append(
                Paragraph(
                    f"• {inline_markdown(text)}",
                    bullet_style
                )
            )

            i += 1
            continue

        # -----------------------------------------------------
        # Numbered list
        # -----------------------------------------------------

        numbered_match = re.match(
            r"^(\d+)\.\s+(.*)$",
            line
        )

        if numbered_match:

            number = numbered_match.group(1)
            text = numbered_match.group(2)

            story.append(
                Paragraph(
                    f"{number}. {inline_markdown(text)}",
                    body_style
                )
            )

            i += 1
            continue

        # -----------------------------------------------------
        # Bold-only / normal paragraphs
        # -----------------------------------------------------

        story.append(
            Paragraph(
                inline_markdown(line),
                body_style
            )
        )

        i += 1

    # ---------------------------------------------------------
    # Build PDF
    # ---------------------------------------------------------

    doc.build(story)

    buffer.seek(0)

    return buffer.getvalue()

def reset_results():

    st.session_state.document_result = None
    st.session_state.bom = None

    st.session_state.inventory_result = None
    st.session_state.decision_result = None
    st.session_state.report_result = None

    st.session_state.approved = False
    st.session_state.rejected = False
    st.session_state.pipeline_running = False
    st.session_state.diagnostic_result = None
    st.session_state.diagnostic_symptom = None

    st.session_state.catalogue_pdf_path = None
    st.session_state.vision_result = None


# ============================================================
# BOM → DATAFRAME
# ============================================================

def bom_to_dataframe(bom):

    rows = []

    for part in bom.get("parts", []):

        rows.append(
            {
                "Item": part.get("item", ""),
                "Part Number": part.get(
                    "part_number",
                    "",
                ),
                "Description": part.get(
                    "description",
                    "",
                ),
                "Quantity": part.get(
                    "quantity",
                    "",
                ),
                "Remarks": part.get(
                    "remarks",
                    "",
                ),
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "Item",
            "Part Number",
            "Description",
            "Quantity",
            "Remarks",
        ],
    )


# ============================================================
# CLEAN CELL
# ============================================================

def clean_cell(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


# ============================================================
# DATAFRAME → BOM
# ============================================================

def dataframe_to_bom(df, original_bom):

    parts = []

    for _, row in df.iterrows():

        quantity_value = row["Quantity"]

        if (
            pd.isna(quantity_value)
            or str(quantity_value).strip() == ""
        ):

            quantity = None

        else:

            try:
                quantity = int(
                    float(quantity_value)
                )
            except Exception:
                quantity = quantity_value

        parts.append(
            {
                "item": clean_cell(
                    row["Item"]
                ),
                "part_number": clean_cell(
                    row["Part Number"]
                ),
                "description": clean_cell(
                    row["Description"]
                ),
                "quantity": quantity,
                "remarks": clean_cell(
                    row["Remarks"]
                ),
            }
        )

    bom = dict(original_bom)

    bom["parts"] = parts
    bom["total_parts"] = len(parts)

    return bom


# ============================================================
# GET INVENTORY DATABASE
# ============================================================

def inventory_database_dataframe():

    if not INVENTORY_DB.exists():

        return pd.DataFrame()

    try:

        connection = sqlite3.connect(
            INVENTORY_DB
        )

        df = pd.read_sql_query(
            """
            SELECT
                part_number,
                description,
                available_qty,
                min_threshold,
                rack_location,
                supplier
            FROM inventory
            ORDER BY part_number
            """,
            connection,
        )

        connection.close()

        df = df.rename(
            columns={
                "part_number": "Part Number",
                "description": "Description",
                "available_qty": "Available",
                "min_threshold": "Minimum",
                "rack_location": "Rack",
                "supplier": "Supplier",
            }
        )

        return df

    except Exception:

        return pd.DataFrame()


# ============================================================
# INVENTORY RESULT → DATAFRAME
# ============================================================

def flatten_inventory(inventory):

    if inventory is None:
        return pd.DataFrame()

    if isinstance(inventory, dict):

        if isinstance(
            inventory.get("parts"),
            list,
        ):

            data = inventory["parts"]

        elif isinstance(
            inventory.get("inventory"),
            list,
        ):

            data = inventory["inventory"]

        elif any(
            key in inventory
            for key in [
                "part_number",
                "available_quantity",
                "available_qty",
            ]
        ):

            data = [inventory]

        else:

            data = []

    elif isinstance(inventory, list):

        data = inventory

    else:

        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data)


def inventory_display_dataframe(
    inventory
):

    df = flatten_inventory(
        inventory
    )

    if df.empty:
        return df

    rename_map = {
        "part_number": "Part Number",
        "description": "Description",
        "required_quantity": "Required",
        "required_qty": "Required",
        "quantity_required": "Required",
        "available_quantity": "Available",
        "available_qty": "Available",
        "minimum_threshold": "Minimum",
        "min_threshold": "Minimum",
        "rack_location": "Rack",
        "supplier": "Supplier",
        "remarks": "Remarks",
    }

    df = df.rename(
        columns={
            key: value
            for key, value in rename_map.items()
            if key in df.columns
        }
    )

    preferred_columns = [
        "Part Number",
        "Description",
        "Required",
        "Available",
        "Minimum",
        "Rack",
        "Supplier",
        "Remarks",
    ]

    existing_columns = [
        column
        for column in preferred_columns
        if column in df.columns
    ]

    return df[existing_columns]


# ============================================================
# RUN INVENTORY → DECISION → REPORT
# ============================================================

def run_remaining_pipeline(bom):

    with st.status(
        "🚀 Running analysis pipeline...",
        expanded=True,
    ) as status:

        # ----------------------------------------------------
        # INVENTORY AGENT
        # ----------------------------------------------------

        status.update(
            label="📦 Inventory Agent: checking stock levels..."
        )

        st.write(
            "Checking inventory..."
        )

        inventory_agent = InventoryAgent()

        inventory_result = (
            inventory_agent.invoke(bom)
        )

        st.session_state.inventory_result = (
            inventory_result
        )

        inventory = inventory_result[
            "inventory"
        ]

        st.write(
            "✅ Inventory check complete."
        )


        # ----------------------------------------------------
        # DECISION AGENT
        # ----------------------------------------------------

        status.update(
            label="🧮 Decision Agent: analysing shortages..."
        )

        st.write(
            "Analysing inventory..."
        )

        decision_agent = DecisionAgent()

        decision_result = (
            decision_agent.invoke(
                inventory
            )
        )

        decision = decision_result[
            "decision"
        ]

        decision["assembly"] = bom.get(
            "assembly",
            "",
        )

        decision["catalogue"] = bom.get(
            "catalogue",
            "",
        )

        st.session_state.decision_result = (
            decision_result
        )

        st.write(
            "✅ Decision analysis complete."
        )


        # ----------------------------------------------------
        # REPORT AGENT
        # ----------------------------------------------------

        status.update(
            label="📝 Report Agent: composing final report..."
        )

        st.write(
            "Generating final report..."
        )

        report_agent = ReportAgent()

        report_result = (
            report_agent.invoke(
                decision
            )
        )

        st.session_state.report_result = (
            report_result
        )

        st.write(
            "✅ Report generated."
        )

        status.update(
            label="✅ Analysis completed successfully.",
            state="complete",
        )


# ============================================================
# PIPELINE STATUS
# ============================================================

def show_pipeline_status():

    extraction_label = (
        "Vision Agent"
        if st.session_state.input_type == "Assembly Image"
        else "Document Agent"
    )

    _stages = [
        (
            extraction_label,
            st.session_state.bom is not None,
        ),
        (
            "Human Review",
            st.session_state.approved,
        ),
        (
            "Inventory Agent",
            st.session_state.inventory_result is not None,
        ),
        (
            "Report Agent",
            st.session_state.report_result is not None,
        ),
    ]

    _completed_count = sum(
        1 for _, done in _stages if done
    )

    _fill_pct = (
        0
        if len(_stages) <= 1
        else round(
            (_completed_count - 1)
            / (len(_stages) - 1)
            * 88,
            1,
        )
    )

    _fill_pct = max(_fill_pct, 0)

    _steps_html = "".join(
        (
            f'<div class="pipeline-step '
            f'{"done" if done else "pending"}">'
            f'<div class="pipeline-step-dot">'
            f'{"✓" if done else index}'
            f'</div>'
            f'<div class="pipeline-step-label">'
            f'{label}'
            f'</div>'
            f'</div>'
        )
        for index, (label, done)
        in enumerate(_stages, start=1)
    )

    st.markdown(
        f"""
        <div class="pipeline-card">
            <div class="pipeline-heading">Pipeline Status</div>
            <div class="pipeline-stepper">
                <div class="pipeline-track"></div>
                <div
                    class="pipeline-track-fill"
                    style="width:{_fill_pct}%;"
                ></div>
                {_steps_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# INVENTORY PANEL
# ============================================================

def render_inventory_panel():

    header_col, close_col = st.columns(
        [5, 1],
        vertical_alignment="center",
    )

    with header_col:

        st.subheader(
            "📦 Inventory"
        )

        st.caption(
            "Current spare-parts inventory"
        )

    with close_col:

        if st.button(
            "✕ Close",
            use_container_width=True,
            key="inventory_close_btn",
        ):

            st.session_state.show_inventory = False

            st.rerun()

    inventory_df = (
        inventory_database_dataframe()
    )

    if inventory_df.empty:

        st.warning(
            "Inventory database could not be loaded."
        )

        return

    search = st.text_input(
        "Search Inventory",
        placeholder="Part number or description",
    )

    if search.strip():

        mask = (
            inventory_df[
                "Part Number"
            ]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False,
            )
            |
            inventory_df[
                "Description"
            ]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False,
            )
        )

        filtered_df = (
            inventory_df[mask]
        )

    else:

        filtered_df = inventory_df

    st.caption(
        f"{len(filtered_df)} parts"
    )

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=600,
    )


# ============================================================
# DIAGNOSTIC ASSEMBLY SELECTION CALLBACK
# ============================================================

def select_diagnostic_assembly(assembly):

    # This callback runs before Streamlit instantiates the widgets
    # again, so it is safe to update the value used by the
    # Assembly / Query text input.
    st.session_state.assembly_query = assembly
    st.session_state.diagnostic_result = None
    st.session_state.diagnostic_symptom = None


# ============================================================
# FLOATING DIAGNOSTIC PANEL CALLBACKS
# ============================================================

def toggle_diagnostic_panel():
    st.session_state.show_diagnostic_panel = (
        not st.session_state.show_diagnostic_panel
    )


def close_diagnostic_panel():
    st.session_state.show_diagnostic_panel = False


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    if LOGO_DATA_URI:

        st.markdown(
            f"""
            <div class="persistent-brand">
                <img src="{LOGO_DATA_URI}" alt="Persistent logo" />
                <span>Persistent</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
            <div class="persistent-brand">
                <span>Persistent</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.header(
        "Analysis Studio"
    )


    # ========================================================
    # INPUT TYPE
    # ========================================================

    input_type = st.radio(
        "Input Type",
        [
            "PDF Catalogue",
            "Assembly Image",
        ],
        key="input_type",
        help=(
            "Choose a PDF catalogue for the Document Agent "
            "or an exploded-view image for the Vision Agent."
        ),
    )

    st.markdown("---")


    # ========================================================
    # CATALOGUE SELECTION
    # ========================================================

    catalogue_options = [
        "Select",
        "Apollo Tractors",
        "Mahindra Scorpio",
        "Mahindra Thar",
        "Tata Indica",
    ]

    if input_type == "PDF Catalogue":

        catalogue_options.append(
            "Upload Catalogue"
        )

    catalogue_name = st.selectbox(
        "Select Catalogue",
        catalogue_options,
        index=0,
    )


    # ========================================================
    # PDF CATALOGUE UPLOAD
    # ========================================================

    uploaded_file = None

    if (
        input_type == "PDF Catalogue"
        and catalogue_name == "Upload Catalogue"
    ):

        uploaded_file = st.file_uploader(
            "Choose Catalogue PDF",
            type=["pdf"],
            help=(
                "Upload a spare-parts catalogue in PDF format."
            ),
        )

        if uploaded_file is not None:

            upload_path = (
                UPLOAD_DIR
                / uploaded_file.name
            )

            with open(
                upload_path,
                "wb",
            ) as file:

                file.write(
                    uploaded_file.getbuffer()
                )

            st.session_state.uploaded_catalogue = (
                str(upload_path)
            )

            st.session_state.uploaded_catalogue_name = (
                uploaded_file.name
            )

            st.success(
                f"Catalogue selected: "
                f"{uploaded_file.name}"
            )


    # ========================================================
    # VISION IMAGE UPLOAD
    # ========================================================

    uploaded_image = None

    if input_type == "Assembly Image":

        st.markdown(
            """
            <div style="
                margin: 0.35rem 0 0.75rem 0;
                padding: 0.8rem 0.9rem;
                border: 1px solid #FBD8C4;
                border-radius: 10px;
                background: linear-gradient(
                    135deg,
                    #FFF7F2 0%,
                    #FFFFFF 100%
                );
            ">
                <div style="
                    font-weight: 700;
                    color: #14213D;
                    margin-bottom: 0.25rem;
                ">
                    Vision Agent Input
                </div>
                <div style="
                    font-size: 0.82rem;
                    color: #64748B;
                    line-height: 1.4;
                ">
                    Upload an exploded-view image or take a
                    screenshot from the catalogue and drag it
                    into the box below.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_image = st.file_uploader(
            "Upload / Drag & Drop Assembly Image",
            type=[
                "png",
                "jpg",
                "jpeg",
                "webp",
            ],
            accept_multiple_files=False,
            key="vision_image_uploader",
            help=(
                "Take a screenshot of the assembly diagram "
                "and drag the image here."
            ),
        )

        if uploaded_image is not None:

            image_path = (
                VISION_UPLOAD_DIR
                / uploaded_image.name
            )

            with open(
                image_path,
                "wb",
            ) as file:

                file.write(
                    uploaded_image.getbuffer()
                )

            st.session_state.uploaded_image = (
                str(image_path)
            )

            st.session_state.uploaded_image_name = (
                uploaded_image.name
            )

            try:

                preview_image = Image.open(
                    image_path
                )

                st.image(
                    preview_image,
                    caption=(
                        f"Selected image: "
                        f"{uploaded_image.name}"
                    ),
                    use_container_width=True,
                )

            except Exception:

                st.success(
                    f"Image selected: "
                    f"{uploaded_image.name}"
                )


    # ========================================================
    # ASSEMBLY QUERY — PDF ONLY
    # ========================================================

    query = ""

    if input_type == "PDF Catalogue":

        query = st.text_input(
            "Assembly / Query",
            placeholder=(
                "e.g. AUTO LEVELING SKI"
            ),
            key="assembly_query",
        )

    else:

        st.caption(
            "The Vision Agent identifies the assembly name "
            "from the uploaded image."
        )


    # ========================================================
    # OUTPUT
    # ========================================================

    analysis_mode = st.radio(
        "Output",
        [
            "BOM Only",
            "Full Analysis & Report",
        ],
    )


    # ========================================================
    # RUN ANALYSIS
    # ========================================================

    run_analysis = st.button(
        "Run Analysis",
        type="primary",
        use_container_width=True,
    )


    # ========================================================
    # VIEW INVENTORY
    # ========================================================

    st.markdown("---")

    if st.button(
        "📦 View Inventory",
        use_container_width=True,
        key="view_inventory_btn",
    ):

        st.session_state.show_inventory = True

        st.rerun()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    'SPARE PARTS MANAGEMENT SYSTEM'
    '</div>'
    '<div class="main-title-underline"></div>',
    unsafe_allow_html=True,
)




# ============================================================
# MAIN LAYOUT
# ============================================================
# The inventory panel no longer occupies a side column. It is
# rendered later as a full-screen overlay modal (see
# "INVENTORY MODAL" section below), so the main content always
# takes the full page width.
# ============================================================

main_col = st.container()


# ============================================================
# MAIN APPLICATION
# ============================================================

with main_col:


    # ========================================================
    # RUN SELECTED EXTRACTION AGENT
    # ========================================================

    if run_analysis:

        # ====================================================
        # PDF / DOCUMENT AGENT
        # ====================================================

        if input_type == "PDF Catalogue":

            # ------------------------------------------------
            # VALIDATE CATALOGUE
            # ------------------------------------------------

            if catalogue_name == "Select":

                st.error(
                    "Please select a catalogue."
                )

            # ------------------------------------------------
            # VALIDATE UPLOAD
            # ------------------------------------------------

            elif (
                catalogue_name
                == "Upload Catalogue"
                and uploaded_file is None
                and st.session_state.uploaded_catalogue
                is None
            ):

                st.error(
                    "Please upload a catalogue PDF."
                )

            # ------------------------------------------------
            # VALIDATE QUERY
            # ------------------------------------------------

            elif not query.strip():

                st.error(
                    "Please enter an assembly name or query."
                )

            else:

                reset_results()

                # ------------------------------------------------
                # DETERMINE PDF PATH
                # ------------------------------------------------

                if (
                    catalogue_name
                    == "Upload Catalogue"
                ):

                    pdf_path = Path(
                        st.session_state.uploaded_catalogue
                    )

                    display_catalogue_name = (
                        st.session_state.uploaded_catalogue_name
                        or pdf_path.stem
                    )

                else:

                    pdf_path = CATALOGUES[
                        catalogue_name
                    ]

                    display_catalogue_name = (
                        catalogue_name
                    )


                # ------------------------------------------------
                # CHECK FILE
                # ------------------------------------------------

                if not pdf_path.exists():

                    st.error(
                        f"Catalogue not found: {pdf_path}"
                    )

                else:

                    with st.status(
                        "🔍 Document Agent: reading catalogue...",
                        expanded=True,
                    ) as status:

                        try:

                            start = time.time()

                            document_agent = (
                                DocumentAgent()
                            )

                            st.write(
                                "📄 Reading catalogue and "
                                "locating the requested assembly..."
                            )

                            st.write(
                                "🤖 Generating the Bill of Materials..."
                            )

                            result = (
                                document_agent.invoke(
                                    str(pdf_path),
                                    query.strip(),
                                )
                            )

                            if result.get(
                                "status"
                            ) == "failed":

                                raise RuntimeError(
                                    result.get(
                                        "error",
                                        "Document Agent failed.",
                                    )
                                )

                            bom = result["bom"]

                            bom["assembly"] = (
                                query.strip()
                            )

                            bom["catalogue"] = (
                                display_catalogue_name
                            )

                            bom["total_parts"] = len(
                                bom.get(
                                    "parts",
                                    [],
                                )
                            )

                            st.session_state.document_result = (
                                result
                            )

                            st.session_state.bom = (
                                bom
                            )

                            st.session_state.catalogue_pdf_path = (
                                str(pdf_path)
                            )

                            st.session_state.analysis_mode = (
                                analysis_mode
                            )

                            elapsed = (
                                time.time() - start
                            )

                            st.write(
                                f"✅ BOM extracted in "
                                f"{elapsed:.2f} seconds."
                            )

                            status.update(
                                label=(
                                    "✅ Document Agent completed."
                                ),
                                state="complete",
                            )

                        except Exception as exc:

                            status.update(
                                label=(
                                    "❌ Document Agent failed."
                                ),
                                state="error",
                            )

                            st.error(
                                f"Document Agent error: {exc}"
                            )


        # ====================================================
        # IMAGE / VISION AGENT
        # ====================================================

        else:

            # ------------------------------------------------
            # VALIDATE CATALOGUE
            # ------------------------------------------------

            if catalogue_name == "Select":

                st.error(
                    "Please select a catalogue."
                )

            # ------------------------------------------------
            # VALIDATE IMAGE
            # ------------------------------------------------

            elif (
                uploaded_image is None
                and st.session_state.uploaded_image
                is None
            ):

                st.error(
                    "Please upload or drag and drop an "
                    "assembly image."
                )

            else:

                reset_results()

                # ------------------------------------------------
                # DETERMINE IMAGE PATH
                # ------------------------------------------------

                if uploaded_image is not None:

                    image_path = (
                        VISION_UPLOAD_DIR
                        / uploaded_image.name
                    )

                else:

                    image_path = Path(
                        st.session_state.uploaded_image
                    )

                # ------------------------------------------------
                # CHECK IMAGE FILE
                # ------------------------------------------------

                if not image_path.exists():

                    st.error(
                        f"Assembly image not found: "
                        f"{image_path}"
                    )

                else:

                    with st.status(
                        "👁️ Vision Agent: analysing assembly image...",
                        expanded=True,
                    ) as status:

                        try:

                            start = time.time()

                            vision_agent = (
                                VisionAgent()
                            )

                            st.write(
                                "🖼️ Reading the exploded-view image..."
                            )

                            st.write(
                                "🤖 Identifying the assembly "
                                "and callout numbers..."
                            )

                            # The Vision Agent expects:
                            #   1. Image path
                            #   2. Canonical catalogue name
                            #
                            # The catalogue name is selected by the
                            # user in the sidebar and already matches
                            # the names stored in central_inventory.db.
                            canonical_catalogue_name = (
                                catalogue_name
                                .strip()
                                .upper()
                                .replace(
                                    " ",
                                    "_",
                                )
                            )

                            vision_result = (
                                vision_agent.invoke(
                                    str(image_path),
                                    canonical_catalogue_name,
                                )
                            )

                            if (
                                isinstance(
                                    vision_result,
                                    dict,
                                )
                                and vision_result.get(
                                    "status"
                                ) == "failed"
                            ):

                                raise RuntimeError(
                                    vision_result.get(
                                        "error",
                                        "Vision Agent failed.",
                                    )
                                )

                            if not isinstance(
                                vision_result,
                                dict,
                            ):

                                raise RuntimeError(
                                    "Vision Agent returned "
                                    "an invalid result."
                                )

                            vision_bom = (
                                vision_result.get(
                                    "bom"
                                )
                            )

                            if vision_bom is None:

                                raise RuntimeError(
                                    "Vision Agent did not "
                                    "return a BOM."
                                )

                            # Pydantic models are converted to
                            # dictionaries if necessary so the rest
                            # of the existing frontend pipeline can
                            # work exactly as before.
                            if hasattr(
                                vision_bom,
                                "model_dump",
                            ):

                                bom = (
                                    vision_bom.model_dump()
                                )

                            else:

                                bom = dict(
                                    vision_bom
                                )

                            bom["catalogue"] = (
                                canonical_catalogue_name
                            )

                            bom["total_parts"] = len(
                                bom.get(
                                    "parts",
                                    [],
                                )
                            )

                            st.session_state.vision_result = (
                                vision_result
                            )

                            st.session_state.bom = (
                                bom
                            )

                            st.session_state.analysis_mode = (
                                analysis_mode
                            )

                            elapsed = (
                                time.time() - start
                            )

                            st.write(
                                f"✅ Vision BOM extracted in "
                                f"{elapsed:.2f} seconds."
                            )

                            status.update(
                                label=(
                                    "✅ Vision Agent completed."
                                ),
                                state="complete",
                            )

                        except Exception as exc:

                            status.update(
                                label=(
                                    "❌ Vision Agent failed."
                                ),
                                state="error",
                            )

                            st.error(
                                f"Vision Agent error: {exc}"
                            )

    # ========================================================
    # HUMAN REVIEW
    # ========================================================

    if (
        st.session_state.bom is not None
        and not st.session_state.approved
    ):

        st.markdown("---")

        st.subheader(
            "Human Review"
        )

        st.info(
            "Review the extracted BOM before "
            "it continues through the pipeline."
        )

        bom = st.session_state.bom

        st.write(
            f"**Assembly:** "
            f"{bom.get('assembly', '')}"
        )

        st.write(
            f"**Catalogue:** "
            f"{bom.get('catalogue', '')}"
        )

        edited_df = st.data_editor(
            bom_to_dataframe(bom),
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            key="bom_editor",
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "✓ Approve BOM",
                type="primary",
                use_container_width=True,
            ):

                try:

                    st.session_state.bom = (
                        dataframe_to_bom(
                            edited_df,
                            bom,
                        )
                    )

                    st.session_state.approved = (
                        True
                    )

                    if (
                        st.session_state.analysis_mode
                        == "Full Analysis & Report"
                    ):

                        st.session_state.pipeline_running = (
                            True
                        )

                    st.rerun()

                except Exception as exc:

                    st.error(
                        f"Could not save the reviewed BOM: {exc}"
                    )

        with col2:

            if st.button(
                "✕ Reject BOM",
                use_container_width=True,
            ):

                st.session_state.rejected = True

                st.session_state.bom = None

                st.warning(
                    "BOM rejected. Pipeline stopped."
                )


    # ========================================================
    # APPROVED BOM
    # ========================================================

    if (
        st.session_state.approved
        and st.session_state.bom is not None
    ):

        bom = st.session_state.bom

        st.markdown("---")

        show_pipeline_status()

        st.markdown("---")

        st.subheader(
            "Approved Bill of Materials"
        )

        st.dataframe(
            bom_to_dataframe(bom),
            use_container_width=True,
            hide_index=True,
        )

        st.metric(
            "Total Parts",
            bom.get(
                "total_parts",
                len(
                    bom.get(
                        "parts",
                        [],
                    )
                ),
            ),
        )


        # ====================================================
        # BOM ONLY
        # ====================================================

        if (
            st.session_state.analysis_mode
            == "BOM Only"
        ):

            st.success(
                "BOM verified successfully."
            )

            filename = (
                f"{bom.get('catalogue', 'catalogue')}_"
                f"{bom.get('assembly', 'assembly').replace(' ', '_')}_"
                "BOM.json"
            )

            st.download_button(
                "Download BOM",
                data=json.dumps(
                    bom,
                    indent=4,
                ),
                file_name=filename,
                mime="application/json",
            )


        # ====================================================
        # AUTOMATIC FULL PIPELINE
        # ====================================================

        if (
            st.session_state.analysis_mode
            == "Full Analysis & Report"
            and st.session_state.inventory_result
            is None
            and st.session_state.pipeline_running
        ):

            try:

                run_remaining_pipeline(
                    bom
                )

                st.session_state.pipeline_running = (
                    False
                )

                st.rerun()

            except Exception as exc:

                st.session_state.pipeline_running = (
                    False
                )

                st.error(
                    f"Pipeline error: {exc}"
                )


        # ====================================================
        # INVENTORY ANALYSIS
        # COLLAPSED BY DEFAULT
        # ====================================================

        if (
            st.session_state.inventory_result
            is not None
        ):

            inventory = (
                st.session_state.inventory_result.get(
                    "inventory",
                    {},
                )
            )

            with st.expander(
                "Inventory Analysis",
                expanded=False,
            ):

                inventory_df = (
                    inventory_display_dataframe(
                        inventory
                    )
                )

                if not inventory_df.empty:

                    st.dataframe(
                        inventory_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                else:

                    st.info(
                        "Inventory analysis completed."
                    )


        # ====================================================
        # DECISION ANALYSIS
        # COLLAPSED BY DEFAULT
        # ====================================================

        if (
            st.session_state.decision_result
            is not None
        ):

            decision_result = (
                st.session_state.decision_result
            )

            decision = (
                decision_result.get(
                    "decision",
                    {},
                )
            )

            with st.expander(
                "Decision Analysis",
                expanded=False,
            ):

                if isinstance(
                    decision,
                    dict,
                ):

                    total_parts = (
                        decision.get(
                            "total_parts"
                        )
                    )

                    shortages = (
                        decision.get(
                            "shortage_count"
                        )
                    )

                    low_stock = (
                        decision.get(
                            "low_stock_count"
                        )
                    )

                    if any(
                        value is not None
                        for value in [
                            total_parts,
                            shortages,
                            low_stock,
                        ]
                    ):

                        metric_cols = (
                            st.columns(3)
                        )

                        with metric_cols[0]:

                            if total_parts is not None:

                                st.metric(
                                    "Total Parts",
                                    total_parts,
                                )

                        with metric_cols[1]:

                            if shortages is not None:

                                st.metric(
                                    "Shortages",
                                    shortages,
                                )

                        with metric_cols[2]:

                            if low_stock is not None:

                                st.metric(
                                    "Low Stock",
                                    low_stock,
                                )

                    decision_parts = None

                    if isinstance(
                        decision.get("parts"),
                        list,
                    ):

                        decision_parts = (
                            decision["parts"]
                        )

                    elif isinstance(
                        decision.get("items"),
                        list,
                    ):

                        decision_parts = (
                            decision["items"]
                        )

                    if decision_parts:

                        decision_df = pd.DataFrame(
                            decision_parts
                        )

                        rename_map = {
                            "part_number": "Part Number",
                            "description": "Description",
                            "required_quantity": "Required",
                            "required_qty": "Required",
                            "available_quantity": "Available",
                            "available_qty": "Available",
                            "status": "Status",
                            "action": "Action",
                            "remarks": "Remarks",
                        }

                        decision_df = (
                            decision_df.rename(
                                columns={
                                    key: value
                                    for key, value in rename_map.items()
                                    if key in decision_df.columns
                                }
                            )
                        )

                        st.dataframe(
                            decision_df,
                            use_container_width=True,
                            hide_index=True,
                        )

                    overall_decision = (
                        decision.get(
                            "overall_decision"
                        )
                        or decision.get(
                            "status"
                        )
                    )

                    if overall_decision:

                        st.info(
                            f"Overall Decision: "
                            f"{overall_decision}"
                        )


        # ====================================================
        # FINAL REPORT
        #
        # IMPORTANT:
        # expanded=True
        #
        # Therefore it opens automatically.
        # ====================================================

        if (
            st.session_state.report_result
            is not None
        ):

            report_result = (
                st.session_state.report_result
            )

            with st.expander(
                "Final Report",
                expanded=True,
            ):

                output_file = None

                if isinstance(
                    report_result,
                    dict,
                ):

                    output_file = (
                        report_result.get(
                            "output_file"
                        )
                    )

                if output_file:

                    report_path = Path(
                        output_file
                    )

                    if report_path.exists():

                        report_text = (
                            report_path.read_text(
                                encoding="utf-8"
                            )
                        )

                        st.markdown(
                            report_text
                        )

                        pdf_bytes = markdown_to_pdf(report_text)

                        st.download_button(
                            label="Download Final Report",
                            data=pdf_bytes,
                            file_name="final_report.pdf",
                            mime="application/pdf",
                        )

                    else:

                        st.info(
                            "Final report was generated."
                        )

                else:

                    # ------------------------------------------------
                    # FALLBACK:
                    # If the Report Agent returns report text directly.
                    # ------------------------------------------------

                    if isinstance(
                        report_result,
                        dict,
                    ):

                        report_text = (
                            report_result.get(
                                "report"
                            )
                        )

                        if report_text:

                            st.markdown(
                                report_text
                            )

                        else:

                            st.info(
                                "Final report was generated."
                            )

                    elif isinstance(
                        report_result,
                        str,
                    ):

                        st.markdown(
                            report_result
                        )

                    else:

                        st.info(
                            "Final report was generated."
                        )


# ============================================================
# INVENTORY MODAL (OVERLAY)
# ============================================================
# Renders the same render_inventory_panel() defined above, only
# now inside a centered, backdrop-blurred overlay instead of a
# side column.
#
# While the modal is open, the sidebar is hidden entirely (via
# CSS only - no widgets are removed or reset) so the overlay
# reads as a clean, full-page modal instead of sitting beside a
# visible sidebar. Closing the modal restores the sidebar exactly
# as it was, since none of its state is touched.
# ============================================================

if st.session_state.show_inventory:

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="inventory_modal_backdrop"):

        with st.container(key="inventory_modal_card"):

            render_inventory_panel()


# ============================================================
# INITIAL SCREEN
# ============================================================

if (
    st.session_state.bom is None
    and not st.session_state.rejected
    and not run_analysis
):

    st.markdown("---")

    _workflow_steps = [
        ("1️⃣", "Choose PDF or Image"),
        ("📖", "Select Catalogue"),
        ("🖼️", "Upload / Drag & Drop"),
        ("🤖", "Generate BOM"),
        ("👁️", "Review BOM"),
        ("🚀", "Continue Analysis"),
    ]

    _steps_html = "".join(
        (
            f'<div class="workflow-step">'
            f'<div class="workflow-step-badge">{index}</div>'
            f'<div class="workflow-step-icon">{icon}</div>'
            f'<div class="workflow-step-label">{label}</div>'
            f'</div>'
        )
        for index, (icon, label) in enumerate(
            _workflow_steps,
            start=1,
        )
    )

    st.markdown(
        f"""
        <div class="hub-card">
            <div class="hub-eyebrow">AI Workflow Hub</div>
            <div class="hub-title">Welcome to PERSISTENT AI</div>
            <div class="hub-subtitle">
                Start your analysis journey below - each step
                below is handled by a dedicated agent.
            </div>
            <div class="workflow-stepper">
                <div class="workflow-track"></div>
                {_steps_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# DIAGNOSTIC ASSISTANT (FLOATING PANEL)
# ============================================================
# The robot launcher button (always visible, bottom-right) toggles
# this panel open/closed. Everything inside this block is the exact
# same Document -> Human Review -> Inventory -> Decision -> Report
# -independent Diagnostic Assistant logic as before; only its
# on-screen container has changed - it now renders inside a
# fixed-position floating card instead of at the bottom of the page.
# ============================================================

if st.session_state.show_diagnostic_panel:

    with st.container(key="diagnostic_panel_container"):

        panel_title_col, panel_close_col = st.columns(
            [5, 1],
            vertical_alignment="center",
        )

        with panel_title_col:

            if ROBOT_DATA_URI:

                st.markdown(
                    f"""
                    <div class="diagnostic-panel-header">
                        <img src="{ROBOT_DATA_URI}" alt="Diagnostic Assistant" />
                        <span>Diagnostic Assistant</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                st.markdown(
                    """
                    <div class="diagnostic-panel-header">
                        <span>🔧 Diagnostic Assistant</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with panel_close_col:

            st.button(
                "✕",
                key="diagnostic_panel_close",
                on_click=close_diagnostic_panel,
            )

        st.caption(
            "Describe a vehicle symptom to identify other assemblies "
            "that may need to be checked."
        )

        diagnostic_symptom = st.chat_input(
            "Describe the vehicle symptom..."
        )

        if diagnostic_symptom:

            # --------------------------------------------------------
            # Determine the currently selected catalogue
            # --------------------------------------------------------

            diagnostic_catalogue_path = None
            diagnostic_catalogue_name = None

            if catalogue_name in CATALOGUES:

                diagnostic_catalogue_path = (
                    CATALOGUES[catalogue_name]
                )

                diagnostic_catalogue_name = catalogue_name

            elif (
                catalogue_name == "Upload Catalogue"
                and st.session_state.uploaded_catalogue
            ):

                diagnostic_catalogue_path = Path(
                    st.session_state.uploaded_catalogue
                )

                diagnostic_catalogue_name = (
                    st.session_state.uploaded_catalogue_name
                    or diagnostic_catalogue_path.stem
                )

            if diagnostic_catalogue_path is None:

                st.session_state.diagnostic_result = {
                    "status": "failed",
                    "error": (
                        "Please select a catalogue or upload "
                        "a catalogue before using the Diagnostic Assistant."
                    ),
                    "assemblies_to_check": [],
                }

                st.session_state.diagnostic_symptom = (
                    diagnostic_symptom
                )

            elif not diagnostic_catalogue_path.exists():

                st.session_state.diagnostic_result = {
                    "status": "failed",
                    "error": (
                        f"Catalogue not found: "
                        f"{diagnostic_catalogue_path}"
                    ),
                    "assemblies_to_check": [],
                }

                st.session_state.diagnostic_symptom = (
                    diagnostic_symptom
                )

            else:

                current_assembly = (
                    (
                        st.session_state.bom.get(
                            "assembly",
                            "",
                        )
                        if st.session_state.bom
                        else st.session_state.get(
                            "assembly_query",
                            "",
                        )
                    )
                    or ""
                ).strip()

                with st.spinner(
                    "🩺 Diagnostic Agent is checking the catalogue..."
                ):

                    diagnostic_agent = DiagnosticAgent()

                    diagnostic_result = (
                        diagnostic_agent.invoke(
                            symptom=diagnostic_symptom,
                            catalogue_path=str(
                                diagnostic_catalogue_path
                            ),
                            catalogue_name=(
                                diagnostic_catalogue_name
                            ),
                            current_assembly=(
                                current_assembly
                            ),
                        )
                    )

                st.session_state.diagnostic_result = (
                    diagnostic_result
                )

                st.session_state.diagnostic_symptom = (
                    diagnostic_symptom
                )


        # ------------------------------------------------------------
        # Diagnostic conversation/result
        # ------------------------------------------------------------

        if st.session_state.diagnostic_symptom:

            with st.chat_message("user"):

                st.write(
                    st.session_state.diagnostic_symptom
                )

            result = st.session_state.diagnostic_result

            if result is not None:

                with st.chat_message("assistant"):

                    if result.get("status") == "completed":

                        assemblies = result.get(
                            "assemblies_to_check",
                            [],
                        )

                        if assemblies:

                            st.markdown(
                                "**Assemblies to check**"
                            )

                            # Assembly names are intentionally rendered
                            # as buttons. Clicking one only fills the
                            # existing Assembly / Query field.
                            button_columns = st.columns(
                                min(3, len(assemblies))
                            )

                            for index, assembly in enumerate(
                                assemblies
                            ):

                                with button_columns[
                                    index % len(button_columns)
                                ]:

                                    st.button(
                                        assembly,
                                        key=(
                                            "diagnostic_assembly_"
                                            f"{index}_"
                                            f"{assembly}"
                                        ),
                                        use_container_width=True,
                                        on_click=select_diagnostic_assembly,
                                        args=(assembly,),
                                    )

                        else:

                            st.info(
                                "No additional catalogue assemblies "
                                "were identified for this symptom."
                            )

                    else:

                        st.error(
                            result.get(
                                "error",
                                "Diagnostic Agent failed.",
                            )
                        )


# ============================================================
# ROBOT LAUNCHER (ALWAYS VISIBLE, BOTTOM-RIGHT)
# ============================================================
# Clicking this toggles the floating Diagnostic Assistant panel
# above (open <-> closed). Rendered last so it stays on top of
# the rest of the page via fixed positioning.
# ============================================================

with st.container(key="robot_fab_container"):

    st.button(
        "🤖",
        key="robot_fab_button",
        help="Diagnostic Assistant",
        on_click=toggle_diagnostic_panel,
    )