from pathlib import Path
import json
import sqlite3
import time

import pandas as pd
import streamlit as st

from agents.document import DocumentAgent
from agents.inventory import InventoryAgent
from agents.decision import DecisionAgent
from agents.report import ReportAgent
from agents.diagnostic import DiagnosticAgent

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

INVENTORY_DB = BASE_DIR / "inventory" / "inventory.db"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="PERSISTENT AI",
    page_icon="⚙️",
    layout="wide",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.1rem;
    }

    .subtitle {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 1rem;
    }

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
        "Running analysis...",
        expanded=True,
    ) as status:

        # ----------------------------------------------------
        # INVENTORY AGENT
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # DECISION AGENT
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # REPORT AGENT
        # ----------------------------------------------------

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

        status.update(
            label="Analysis completed successfully.",
            state="complete",
        )


# ============================================================
# PIPELINE STATUS
# ============================================================

def show_pipeline_status():

    st.subheader(
        "Pipeline Status"
    )

    cols = st.columns(4)

    with cols[0]:

        if st.session_state.bom is not None:

            st.success(
                "✓ Document Agent"
            )

        else:

            st.info(
                "○ Document Agent"
            )

    with cols[1]:

        if st.session_state.approved:

            st.success(
                "✓ Human Review"
            )

        else:

            st.info(
                "○ Human Review"
            )

    with cols[2]:

        if (
            st.session_state.inventory_result
            is not None
        ):

            st.success(
                "✓ Inventory Agent"
            )

        else:

            st.info(
                "○ Inventory Agent"
            )

    with cols[3]:

        if (
            st.session_state.report_result
            is not None
        ):

            st.success(
                "✓ Report Agent"
            )

        else:

            st.info(
                "○ Report Agent"
            )


# ============================================================
# INVENTORY PANEL
# ============================================================

def render_inventory_panel():

    st.subheader(
        "Inventory"
    )

    st.caption(
        "Current spare-parts inventory"
    )

    if st.button(
        "Close Inventory",
        use_container_width=True,
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
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
        ">
            Persistent Systems
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.header(
        "Analysis"
    )


    # ========================================================
    # CATALOGUE SELECTION
    # ========================================================

    catalogue_options = [
        "Select",
        "Apollo Tractors",
        "Mahindra Scorpio",
        "Mahindra Thar",
        "Tata Indica",
        "Upload Catalogue",
    ]

    catalogue_name = st.selectbox(
        "Select Catalogue",
        catalogue_options,
        index=0,
    )


    # ========================================================
    # UPLOAD ONLY WHEN "UPLOAD CATALOGUE" IS SELECTED
    # ========================================================

    uploaded_file = None

    if catalogue_name == "Upload Catalogue":

        uploaded_file = st.file_uploader(
            "Choose Catalogue PDF",
            type=["pdf"],
            help="Upload a spare-parts catalogue in PDF format.",
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
    # ASSEMBLY QUERY
    # ========================================================

    query = st.text_input(
        "Assembly / Query",
        placeholder=(
            "e.g. AUTO LEVELING SKI"
        ),
        key="assembly_query",
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
        "View Inventory",
        use_container_width=True,
    ):

        st.session_state.show_inventory = True

        st.rerun()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    'SPARE PARTS MANAGEMENT SYSTEM'
    '</div>',
    unsafe_allow_html=True,
)




# ============================================================
# MAIN / INVENTORY LAYOUT
# ============================================================

if st.session_state.show_inventory:

    main_col, inventory_col = (
        st.columns(
            [65, 35],
            gap="large",
        )
    )

else:

    main_col = st.container()

    inventory_col = None


# ============================================================
# MAIN APPLICATION
# ============================================================

with main_col:


    # ========================================================
    # RUN DOCUMENT AGENT
    # ========================================================

    if run_analysis:

        # ----------------------------------------------------
        # VALIDATE CATALOGUE
        # ----------------------------------------------------

        if catalogue_name == "Select":

            st.error(
                "Please select a catalogue."
            )

        # ----------------------------------------------------
        # VALIDATE UPLOAD
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # VALIDATE QUERY
        # ----------------------------------------------------

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
                    "Running Document Agent...",
                    expanded=True,
                ) as status:

                    try:

                        start = time.time()

                        document_agent = (
                            DocumentAgent()
                        )

                        st.write(
                            "Reading catalogue and "
                            "locating the requested assembly..."
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

                        st.session_state.analysis_mode = (
                            analysis_mode
                        )

                        elapsed = (
                            time.time() - start
                        )

                        st.write(
                            f"BOM extracted in "
                            f"{elapsed:.2f} seconds."
                        )

                        status.update(
                            label=(
                                "Document Agent completed."
                            ),
                            state="complete",
                        )

                    except Exception as exc:

                        status.update(
                            label=(
                                "Document Agent failed."
                            ),
                            state="error",
                        )

                        st.error(
                            f"Document Agent error: {exc}"
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
# RIGHT-SIDE INVENTORY PANEL
# ============================================================

if (
    st.session_state.show_inventory
    and inventory_col is not None
):

    with inventory_col:

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

    st.markdown(
        """
        ## Welcome to PERSISTENT AI

        Use the sidebar to:

        1. Select a catalogue.
        2. Enter the required assembly or query.
        3. Choose **BOM Only** or **Full Analysis & Report**.
        4. Run the Document Agent.
        5. Review and approve the extracted BOM.
        6. Continue with the selected analysis.
        """
    )

# ============================================================
# DIAGNOSTIC ASSISTANT
# ============================================================
# This section is intentionally at the bottom of the page.
# It does not alter the existing Document -> Human Review ->
# Inventory -> Decision -> Report pipeline.
# ============================================================

st.markdown("---")

st.subheader("🔧 Diagnostic Assistant")

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
            st.session_state.get(
                "assembly_query",
                "",
            )
            or ""
        ).strip()

        with st.spinner(
            "Diagnostic Agent is checking the catalogue..."
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