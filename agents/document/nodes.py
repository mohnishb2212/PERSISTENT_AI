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

from agents.document import state


def validate_input(state: DocumentState) -> DocumentState:
    """
    Validate the user inputs before processing the catalogue.
    """
    pdf_path = state["pdf_path"]
    query = state["user_query"]

    # -----------------------------
    # Validate PDF path
    # -----------------------------
    if not Path(pdf_path).exists():
        state["status"] = "failed"
        state["error"] = f"PDF not found: {pdf_path}"
        return state

    # -----------------------------
    # Validate file extension
    # -----------------------------
    if not pdf_path.lower().endswith(".pdf"):
        state["status"] = "failed"
        state["error"] = "Input file must be a PDF."
        return state

    # -----------------------------
    # Validate query
    # -----------------------------
    if not query.strip():
        state["status"] = "failed"
        state["error"] = "User query cannot be empty."
        return state

    # -----------------------------
    # Validation successful
    # -----------------------------
    state["status"] = "validated"
    state["error"] = ""
    return state



def load_pdf(state: DocumentState) -> DocumentState:
    """
    Load the catalogue into memory.
    """
    try:
        pdf = fitz.open(state["pdf_path"])
        state["pdf_document"] = pdf
        state["status"] = "pdf_loaded"
        return state

    except Exception as e:
        state["status"] = "failed"
        state["error"] = str(e)
        return state



def build_page_index(state: DocumentState) -> DocumentState:
    """
    Extract text from every page and build an in-memory index.
    """
    pdf = state["pdf_document"]

    page_index = {}

    for page_number in range(len(pdf)):
        page = pdf.load_page(page_number)
        text = page.get_text()
        page_index[page_number + 1] = text

    state["page_index"] = page_index
    state["status"] = "page_index_created"

    return state

from PIL import ImageOps, ImageEnhance, Image
import re
from difflib import get_close_matches



def remove_index_page_with_llm(
    state: DocumentState,
    candidate_pages: list[int]
) -> list[int]:
    """
    Use the LLM to identify and remove the index/contents page
    from the retrieved candidate pages.

    The LLM decides which page is actually an index page.
    All other candidate pages are retained.
    """

    if not candidate_pages:
        return candidate_pages

    page_index = state["page_index"]

    page_blocks = []

    for page_number in candidate_pages:

        text = page_index.get(page_number, "").strip()

        # Prevent an unnecessarily large LLM prompt
        if len(text) > 4000:
            text = text[:4000]

        page_blocks.append(
            f"""
PAGE {page_number}
----------------
{text}
"""
        )

    pages_text = "\n".join(page_blocks)

    prompt = f"""
You are analyzing pages from a mechanical parts catalogue.

The user is looking for this assembly:

"{state["user_query"]}"

Your task is to identify which of the candidate pages is the
INDEX / CONTENTS page, if one exists.

An INDEX / CONTENTS page usually:
- lists multiple assembly names, sections, or components
- contains page numbers or references to other pages
- acts as a navigation page
- does not contain the actual detailed BOM/parts table for the assembly

An ACTUAL ASSEMBLY/BOM page usually:
- contains the assembly name or title
- contains an exploded-view diagram and/or parts table
- contains part numbers, descriptions, quantities, item numbers, etc.
- contains the actual information needed to construct the BOM

IMPORTANT RULES:

1. Do NOT assume that the first or smallest page number is the index.
2. Decide based on the actual content of the page.
3. If a page contains the actual BOM/parts information, DO NOT classify it
   as the index just because the assembly name also appears elsewhere.
4. There can be only one index page among these candidates.
5. If none of the candidate pages is an index/contents page, return null.
6. We want to REMOVE ONLY the actual index page.
7. KEEP EVERY OTHER CANDIDATE PAGE.

Candidate pages:

{pages_text}

Return ONLY valid JSON in exactly this format:

{{
    "index_page": null
}}

or:

{{
    "index_page": 12
}}

where 12 must be the actual page number of the INDEX / CONTENTS page.
"""

    try:
        response = llm.invoke(prompt)

        content = response.content.strip()

        # Handle accidental markdown code fences
        if content.startswith("```"):
            content = content.replace("```json", "")
            content = content.replace("```", "")
            content = content.strip()

        result = json.loads(content)

        index_page = result.get("index_page")

        if index_page is not None:
            try:
                index_page = int(index_page)
            except (ValueError, TypeError):
                index_page = None

        # Remove the page only if the LLM selected
        # a page that actually exists in the candidate list.
        if index_page in candidate_pages:

            candidate_pages = [
                page
                for page in candidate_pages
                if page != index_page
            ]

            print(
                f"LLM identified page {index_page} as the index page."
            )

        else:
            print(
                "LLM found no index page among candidate pages."
            )

        return candidate_pages

    except Exception as e:

        print(
            f"Warning: Index-page detection failed: {e}"
        )

        # Important:
        # If the LLM fails, keep all pages.
        # This is safer than accidentally deleting a real BOM page.
        return candidate_pages

TOP_K = 7


def retrieve_relevant_pages(state: DocumentState) -> DocumentState:
    """
    Retrieve the pages most relevant to the user's query.

    Strategy:
    1. Exact phrase match
    2. Keyword scoring
    3. Fuzzy matching (fallback)

    After retrieval, an LLM identifies the actual
    index/contents page and removes only that page.
    """

    query = state["user_query"].strip().lower()
    query_words = re.findall(r"\w+", query)

    page_index = state["page_index"]

    # -------------------------------------------------
    # Stage 1 : Exact phrase match
    # -------------------------------------------------

    exact_pages = []

    for page_number, text in page_index.items():

        page_text = text.lower()

        if len(page_text) < 100:
            continue

        if query in page_text:
            exact_pages.append(page_number)

    if exact_pages:

        # Let the LLM decide which page is the index.
        # Do NOT assume the smallest page number is the index.
        exact_pages = remove_index_page_with_llm(
            state,
            exact_pages
        )

        state["relevant_pages"] = exact_pages
        state["status"] = "pages_retrieved"

        print("Exact Match:", exact_pages)

        return state

    # -------------------------------------------------
    # Stage 2 : Keyword scoring
    # -------------------------------------------------

    scored_pages = []

    for page_number, text in page_index.items():

        page_text = text.lower()

        if len(page_text) < 100:
            continue

        score = 0

        # Give a bonus if multiple keywords occur together
        if query in page_text:
            score += 20

        for word in query_words:

            occurrences = page_text.count(word)

            if occurrences:
                score += occurrences * 5

        if score > 0:
            scored_pages.append(
                (page_number, score)
            )

    if scored_pages:

        scored_pages.sort(
            key=lambda x: x[1],
            reverse=True
        )

        candidate_pages = [
            page
            for page, _ in scored_pages[:TOP_K]
        ]

        # Let the LLM identify the index page.
        candidate_pages = remove_index_page_with_llm(
            state,
            candidate_pages
        )

        state["relevant_pages"] = candidate_pages
        state["status"] = "pages_retrieved"

        print(
            "Keyword Match:",
            state["relevant_pages"]
        )

        return state

    # -------------------------------------------------
    # Stage 3 : Fuzzy Matching
    # -------------------------------------------------

    fuzzy_pages = []

    for page_number, text in page_index.items():

        page_text = text.lower()

        if len(page_text) < 100:
            continue

        words = set(
            re.findall(r"\w+", page_text)
        )

        score = 0

        for query_word in query_words:

            match = get_close_matches(
                query_word,
                words,
                n=1,
                cutoff=0.80
            )

            if match:
                score += 1

        if score > 0:
            fuzzy_pages.append(
                (page_number, score)
            )

    if fuzzy_pages:

        fuzzy_pages.sort(
            key=lambda x: x[1],
            reverse=True
        )

        candidate_pages = [
            page
            for page, _ in fuzzy_pages[:TOP_K]
        ]

        # Let the LLM identify the index page.
        candidate_pages = remove_index_page_with_llm(
            state,
            candidate_pages
        )

        state["relevant_pages"] = candidate_pages
        state["status"] = "pages_retrieved"

        print(
            "Fuzzy Match:",
            state["relevant_pages"]
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

    return state
...
import pdfplumber

def extract_relevant_content(state):

    extracted_text = []
    extracted_tables = []

    with pdfplumber.open(state["pdf_path"]) as pdf:

        for page_number in state["relevant_pages"]:

            page = pdf.pages[page_number - 1]

            text = page.extract_text()

            if text:
                extracted_text.append(text)

            tables = page.extract_tables()

            if tables:
                extracted_tables.extend(tables)

    state["extracted_text"] = "\n\n".join(extracted_text)
    state["extracted_tables"] = extracted_tables
    state["status"] = "content_extracted"

    return state



from .llm import get_llm
llm = get_llm()



import re

def clean_text(text: str) -> str:
    text = re.sub(r"[|]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("(", "")
    text = text.replace(")", "")
    text = text.replace("*", "")
    text = text.replace("**", "")

    replacements = {
        "ASSY": "ASSEMBLY",
        "COLUM": "COLUMN",
        "TIE RODEND": "TIE ROD END",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()




def generate_bom(state: DocumentState) -> DocumentState:
    """
    Convert extracted catalogue information into a structured BOM.
    """

    cleaned_text = clean_text(state["extracted_text"])

    prompt = f"""
{DOCUMENT_BOM_PROMPT}

User Query:
{state["user_query"]}

Catalogue Content:
{cleaned_text}

Tables:
{state["extracted_tables"]}
"""

    response = llm.invoke(prompt)

    #print("=" * 80)
    #print(response.content)
    #print("=" * 80)
    bom = json.loads(response.content)

    state["bom"] = bom
    state["status"] = "bom_generated"

    return state


def validate_bom(state: DocumentState) -> DocumentState:
    """
    Validate the generated BOM against the schema.
    """

    bom = state["bom"]

    # Convert item numbers to strings
    for part in bom.get("parts", []):
        part["item"] = str(part.get("item", ""))

    validated = BOM.model_validate(bom)

    state["bom"] = validated.model_dump()
    state["status"] = "completed"

    return state


from pathlib import Path
import json

def save_bom(state: DocumentState) -> DocumentState:
    """
    Save the validated BOM as a JSON file.
    """

    # Create output folder if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Get catalogue name from PDF
    catalogue = Path(state["pdf_path"]).stem

    # Clean query for filename
    query = (
        state["user_query"]
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
    )

    # Final filename
    filepath = output_dir / f"{catalogue}_{query}.json"

    # Save JSON
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            state["bom"],
            f,
            indent=4,
            ensure_ascii=False
        )

    state["output_file"] = str(filepath)
    state["status"] = "saved"

    print(f"BOM saved to: {filepath}")

    return state