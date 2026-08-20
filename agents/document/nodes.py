from pathlib import Path
from difflib import get_close_matches
from typing import Any
import re
import json
from urllib import response
import fitz     # pyMuPDF
from numpy import rint
import pdfplumber
from langchain_google_genai import ChatGoogleGenerativeAI
from .state import DocumentState
from .prompts import DOCUMENT_BOM_PROMPT
from .schemas import BOM
from PIL import Image, ImageEnhance
import pytesseract
import time


def _start_timer():
    """Return a high-resolution timer start point."""
    return time.perf_counter()


def _record_time(name, start_time):
    """Print elapsed time for a node/sub-operation without changing DocumentState."""
    elapsed = time.perf_counter() - start_time
    print(
        f"[PERF] {name:<35} : {elapsed:8.2f} sec"
    )
    return elapsed


def validate_input(state: DocumentState) -> DocumentState:
    """Validate the user inputs before processing the catalogue."""

    _timer = _start_timer()

    pdf_path = state["pdf_path"]
    query = state["user_query"]

    if not Path(pdf_path).exists():
        state["status"] = "failed"
        state["error"] = f"PDF not found: {pdf_path}"
        _record_time(
            "validate_input",
            _timer,
        )
        return state

    if not pdf_path.lower().endswith(".pdf"):
        state["status"] = "failed"
        state["error"] = "Input file must be a PDF."
        _record_time(
            "validate_input",
            _timer,
        )
        return state

    if not query.strip():
        state["status"] = "failed"
        state["error"] = "User query cannot be empty."
        _record_time(
            "validate_input",
            _timer,
        )
        return state

    state["status"] = "validated"
    state["error"] = ""

    _record_time(
        "validate_input",
        _timer,
    )

    return state


def load_pdf(state: DocumentState) -> DocumentState:
    """Load the catalogue into memory."""

    _timer = _start_timer()

    try:
        pdf = fitz.open(
            state["pdf_path"]
        )

        state["pdf_document"] = pdf
        state["status"] = "pdf_loaded"

        _record_time(
            "load_pdf",
            _timer,
        )

        return state

    except Exception as e:

        state["status"] = "failed"
        state["error"] = str(e)

        _record_time(
            "load_pdf",
            _timer,
        )

        return state


def build_page_index(state: DocumentState) -> DocumentState:
    """
    Extract text from every page and build an in-memory index.
    """

    _timer = _start_timer()

    pdf = state["pdf_document"]

    page_index = {}

    for page_number in range(
        len(pdf)
    ):

        page = pdf.load_page(
            page_number
        )

        text = page.get_text()

        page_index[
            page_number + 1
        ] = text

    state["page_index"] = (
        page_index
    )

    state["status"] = (
        "page_index_created"
    )

    _record_time(
        "build_page_index",
        _timer,
    )

    return state


from PIL import (
    ImageOps,
    ImageEnhance,
    Image,
)

import re

from difflib import (
    get_close_matches,
)


def select_assembly_pages_with_llm(
    state: DocumentState,
    candidate_pages: list[int],
) -> list[int]:

    """
    Classify every candidate page and keep only pages containing the
    actual requested assembly/BOM.

    A catalogue can contain multiple index pages, so this function does not
    try to remove a single index page. It also supports assemblies whose BOM
    spans multiple pages.
    """

    if not candidate_pages:
        return []

    page_index = (
        state["page_index"]
    )

    page_blocks = []

    for page_number in candidate_pages:

        text = page_index.get(
            page_number,
            "",
        ).strip()

        if len(text) > 6000:
            text = text[:6000]

        page_blocks.append(
            f"""
PAGE {page_number}
----------------
{text}
"""
        )

    pages_text = "\n".join(
        page_blocks
    )

    prompt = f"""
You are analyzing pages from a mechanical parts catalogue.

The user is looking for this assembly:
"{state['user_query']}"

Classify EACH candidate page into exactly one category:

1. ASSEMBLY
   The page contains the actual requested assembly/BOM data. Evidence may
   include the assembly/group title, exploded-view diagram, FIG. NO., ITEM NO.,
   PART NO., DESCRIPTION, QUANTITY, actual part numbers, or BOM tables.
   A continuation page of the same assembly is also ASSEMBLY.

2. INDEX
   The page is an index, system index, contents, or navigation page. It may
   list many assemblies/groups and page numbers, but does not contain the
   detailed BOM for the requested assembly.

3. OTHER
   The page is neither the requested assembly BOM page nor a relevant index.

CRITICAL RULES:
- There may be MULTIPLE index pages. Do not assume there is only one.
- Never choose the smallest or largest page number by rule.
- The assembly name appearing on a page is NOT sufficient to call it ASSEMBLY.
  Index pages often contain the same assembly name.
- A page containing the actual parts table/BOM is ASSEMBLY even if it also has
  the assembly name in a header.
- If the assembly spans multiple pages, classify ALL relevant pages as ASSEMBLY.
- Return only pages genuinely useful for constructing the requested BOM.

Candidate pages:
{pages_text}

Return ONLY valid JSON in exactly this format:
{{
  "pages": [
    {{"page": 8, "type": "ASSEMBLY"}},
    {{"page": 5, "type": "INDEX"}}
  ]
}}

Use only the supplied page numbers and only these types:
ASSEMBLY, INDEX, OTHER.
"""

    try:

        llm_timer = _start_timer()

        response = llm.invoke(
            prompt
        )

        _record_time(
            "LLM page classification",
            llm_timer,
        )

        content = (
            response.content
            .strip()
        )

        if content.startswith(
            "```"
        ):

            content = content.replace(
                "```json",
                "",
            )

            content = content.replace(
                "```",
                "",
            )

            content = content.strip()

        result = json.loads(
            content
        )

        classifications = (
            result.get(
                "pages",
                [],
            )
        )

        assembly_pages = []

        for item in classifications:

            if not isinstance(
                item,
                dict,
            ):
                continue

            try:

                page = int(
                    item.get(
                        "page"
                    )
                )

            except (
                ValueError,
                TypeError,
            ):

                continue

            page_type = str(
                item.get(
                    "type",
                    "",
                )
            ).upper().strip()

            if (
                page in candidate_pages
                and page_type
                == "ASSEMBLY"
            ):

                assembly_pages.append(
                    page
                )

        assembly_pages = sorted(
            set(
                assembly_pages
            )
        )

        if assembly_pages:

            print(
                f"Assembly page classification: "
                f"candidates={candidate_pages}, "
                f"assembly_pages={assembly_pages}"
            )

            return assembly_pages

        print(
            "LLM found no ASSEMBLY page; "
            "using deterministic fallback."
        )

    except Exception as e:

        print(
            "Warning: Assembly-page classification "
            f"failed: {e}"
        )

    # Deterministic fallback
    scored_pages = []

    for page_number in candidate_pages:

        text = page_index.get(
            page_number,
            "",
        ).lower()

        if not text:
            continue

        score = 0

        for marker in (
            "part no",
            "part number",
            "fig. no",
            "fig no",
            "quantity per vehicle",
            "qty per vehicle",
            "quantity",
        ):

            if marker in text:
                score += 4

        for marker in (
            "index sheet",
            "system index",
            "index -",
            "page no.",
            "page no",
        ):

            if marker in text:
                score -= 5

        part_number_hits = len(
            re.findall(
                r"\b\d{5,}[A-Z0-9./-]*\b",
                text,
                flags=re.I,
            )
        )

        score += min(
            part_number_hits,
            10,
        )

        if score > 0:

            scored_pages.append(
                (
                    page_number,
                    score,
                )
            )

    scored_pages.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    if scored_pages:

        best_score = (
            scored_pages[0][1]
        )

        fallback_pages = [
            page
            for page, score
            in scored_pages
            if score >= max(
                1,
                best_score - 2,
            )
        ]

        print(
            f"Fallback assembly pages: "
            f"{fallback_pages}"
        )

        return sorted(
            set(
                fallback_pages
            )
        )

    print(
        "Fallback could not classify pages; "
        "keeping candidate pages."
    )

    return sorted(
        set(
            candidate_pages
        )
    )


TOP_K = 7


def retrieve_relevant_pages(
    state: DocumentState,
) -> DocumentState:

    """
    Retrieve the pages most relevant to the user's query.

    Strategy:
    1. Exact phrase match
    2. Keyword scoring
    3. Fuzzy matching (fallback)

    After retrieval, an LLM classifies every candidate and keeps only
    pages containing the actual requested assembly/BOM.
    """

    _timer = _start_timer()

    query = (
        state["user_query"]
        .strip()
        .lower()
    )

    query_words = re.findall(
        r"\w+",
        query,
    )

    page_index = (
        state["page_index"]
    )

    # -------------------------------------------------
    # Stage 1 : Exact phrase match
    # -------------------------------------------------

    exact_pages = []

    for page_number, text in (
        page_index.items()
    ):

        page_text = (
            text.lower()
        )

        if len(
            page_text
        ) < 100:
            continue

        if query in page_text:

            exact_pages.append(
                page_number
            )

    if exact_pages:

        exact_pages = (
            select_assembly_pages_with_llm(
                state,
                exact_pages,
            )
        )

        state[
            "relevant_pages"
        ] = exact_pages

        state[
            "status"
        ] = "pages_retrieved"

        print(
            "Exact Match:",
            exact_pages,
        )

        _record_time(
            "retrieve_relevant_pages",
            _timer,
        )

        return state

    # -------------------------------------------------
    # Stage 2 : Keyword scoring
    # -------------------------------------------------

    scored_pages = []

    for page_number, text in (
        page_index.items()
    ):

        page_text = (
            text.lower()
        )

        if len(
            page_text
        ) < 100:
            continue

        score = 0

        if query in page_text:
            score += 20

        for word in query_words:

            occurrences = (
                page_text.count(
                    word
                )
            )

            if occurrences:

                score += (
                    occurrences
                    * 5
                )

        if score > 0:

            scored_pages.append(
                (
                    page_number,
                    score,
                )
            )

    if scored_pages:

        scored_pages.sort(
            key=lambda x: x[1],
            reverse=True,
        )

        candidate_pages = [
            page
            for page, _ in
            scored_pages[:TOP_K]
        ]

        candidate_pages = (
            select_assembly_pages_with_llm(
                state,
                candidate_pages,
            )
        )

        state[
            "relevant_pages"
        ] = candidate_pages

        state[
            "status"
        ] = "pages_retrieved"

        print(
            "Keyword Match:",
            state[
                "relevant_pages"
            ],
        )

        _record_time(
            "retrieve_relevant_pages",
            _timer,
        )

        return state

    # -------------------------------------------------
    # Stage 3 : Fuzzy Matching
    # -------------------------------------------------

    fuzzy_pages = []

    for page_number, text in (
        page_index.items()
    ):

        page_text = (
            text.lower()
        )

        if len(
            page_text
        ) < 100:
            continue

        words = set(
            re.findall(
                r"\w+",
                page_text,
            )
        )

        score = 0

        for query_word in (
            query_words
        ):

            match = (
                get_close_matches(
                    query_word,
                    words,
                    n=1,
                    cutoff=0.80,
                )
            )

            if match:

                score += 1

        if score > 0:

            fuzzy_pages.append(
                (
                    page_number,
                    score,
                )
            )

    if fuzzy_pages:

        fuzzy_pages.sort(
            key=lambda x: x[1],
            reverse=True,
        )

        candidate_pages = [
            page
            for page, _ in
            fuzzy_pages[:TOP_K]
        ]

        candidate_pages = (
            select_assembly_pages_with_llm(
                state,
                candidate_pages,
            )
        )

        state[
            "relevant_pages"
        ] = candidate_pages

        state[
            "status"
        ] = "pages_retrieved"

        print(
            "Fuzzy Match:",
            state[
                "relevant_pages"
            ],
        )

        _record_time(
            "retrieve_relevant_pages",
            _timer,
        )

        return state

    # -------------------------------------------------
    # Nothing found
    # -------------------------------------------------

    state["status"] = "failed"

    state["error"] = (
        f"No pages found matching "
        f"'{state['user_query']}'."
    )

    _record_time(
        "retrieve_relevant_pages",
        _timer,
    )

    return state


import pdfplumber


def extract_relevant_content(
    state
):

    _timer = _start_timer()

    extracted_text = []
    extracted_tables = []

    text_total = 0.0
    table_total = 0.0

    with pdfplumber.open(
        state["pdf_path"]
    ) as pdf:

        for page_number in (
            state["relevant_pages"]
        ):

            page = pdf.pages[
                page_number - 1
            ]

            # ---------------------------------------------
            # TEXT EXTRACTION TIMING
            # ---------------------------------------------

            text_timer = (
                _start_timer()
            )

            text = (
                page.extract_text()
            )

            text_total += (
                time.perf_counter()
                - text_timer
            )

            if text:

                extracted_text.append(
                    text
                )

            # ---------------------------------------------
            # TABLE EXTRACTION TIMING
            # ---------------------------------------------

            table_timer = (
                _start_timer()
            )

            tables = (
                page.extract_tables()
            )

            table_total += (
                time.perf_counter()
                - table_timer
            )

            if tables:

                extracted_tables.extend(
                    tables
                )

    print(
        f"[PERF] {'PDF text extraction':<35} : "
        f"{text_total:8.2f} sec"
    )

    print(
        f"[PERF] {'PDF table extraction':<35} : "
        f"{table_total:8.2f} sec"
    )

    state[
        "extracted_text"
    ] = "\n\n".join(
        extracted_text
    )

    state[
        "extracted_tables"
    ] = extracted_tables

    state[
        "status"
    ] = "content_extracted"

    _record_time(
        "extract_relevant_content",
        _timer,
    )

    return state


from .llm import get_llm

llm = get_llm()


import re


def clean_text(
    text: str
) -> str:

    text = re.sub(
        r"[|]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    text = text.replace(
        "(",
        "",
    )

    text = text.replace(
        ")",
        "",
    )

    text = text.replace(
        "*",
        "",
    )

    text = text.replace(
        "**",
        "",
    )

    replacements = {
        "ASSY":
            "ASSEMBLY",

        "COLUM":
            "COLUMN",

        "TIE RODEND":
            "TIE ROD END",
    }

    for old, new in (
        replacements.items()
    ):

        text = text.replace(
            old,
            new,
        )

    return text.strip()


def generate_bom(
    state: DocumentState,
) -> DocumentState:

    """
    Convert extracted catalogue information into
    a structured BOM.
    """

    _timer = _start_timer()

    # -------------------------------------------------------
    # CLEAN TEXT
    # -------------------------------------------------------

    clean_timer = (
        _start_timer()
    )

    cleaned_text = (
        clean_text(
            state[
                "extracted_text"
            ]
        )
    )

    _record_time(
        "clean_text",
        clean_timer,
    )

    # -------------------------------------------------------
    # BUILD PROMPT
    # -------------------------------------------------------

    prompt = f"""
{DOCUMENT_BOM_PROMPT}

User Query:
{state["user_query"]}

Catalogue Content:
{cleaned_text}

Tables:
{state["extracted_tables"]}
"""

    # -------------------------------------------------------
    # BOM LLM
    # -------------------------------------------------------

    llm_timer = (
        _start_timer()
    )

    response = llm.invoke(
        prompt
    )

    _record_time(
        "LLM BOM generation",
        llm_timer,
    )

    # -------------------------------------------------------
    # PARSE JSON
    # -------------------------------------------------------

    bom = json.loads(
        response.content
    )

    state[
        "bom"
    ] = bom

    state[
        "status"
    ] = "bom_generated"

    _record_time(
        "generate_bom",
        _timer,
    )

    return state


def validate_bom(
    state: DocumentState,
) -> DocumentState:

    """
    Validate the generated BOM against the schema.
    """

    _timer = _start_timer()

    bom = state[
        "bom"
    ]

    # Convert item numbers to strings
    for part in bom.get(
        "parts",
        [],
    ):

        part[
            "item"
        ] = str(
            part.get(
                "item",
                "",
            )
        )

    validated = (
        BOM.model_validate(
            bom
        )
    )

    state[
        "bom"
    ] = (
        validated.model_dump()
    )

    state[
        "status"
    ] = "completed"

    _record_time(
        "validate_bom",
        _timer,
    )

    return state


from pathlib import Path
import json


def save_bom(
    state: DocumentState,
) -> DocumentState:

    """
    Save the validated BOM as a JSON file.
    """

    _timer = _start_timer()

    # Create output folder if it doesn't exist
    output_dir = Path(
        "output"
    )

    output_dir.mkdir(
        exist_ok=True
    )

    # Get catalogue name from PDF
    catalogue = Path(
        state["pdf_path"]
    ).stem

    # Clean query for filename
    query = (
        state[
            "user_query"
        ]
        .lower()
        .replace(
            " ",
            "_",
        )
        .replace(
            "/",
            "_",
        )
    )

    # Final filename
    filepath = (
        output_dir
        / f"{catalogue}_{query}.json"
    )

    # Save JSON
    with open(
        filepath,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            state[
                "bom"
            ],
            f,
            indent=4,
            ensure_ascii=False,
        )

    state[
        "output_file"
    ] = str(
        filepath
    )

    state[
        "status"
    ] = "saved"

    print(
        f"BOM saved to: {filepath}"
    )

    _record_time(
        "save_bom",
        _timer,
    )

    return state