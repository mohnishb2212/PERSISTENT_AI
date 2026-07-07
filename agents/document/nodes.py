from pathlib import Path
from difflib import get_close_matches
from typing import Any
import re
import json

import fitz
import pdfplumber
from langchain_google_genai import ChatGoogleGenerativeAI

from .state import DocumentState
from .prompts import DOCUMENT_BOM_PROMPT
from .schemas import BOM


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


def normalize_query(state: DocumentState) -> DocumentState:
    """
    Convert user query into a standard assembly name.
    """
    query = state.get("normalized_query", state["user_query"]).lower()

    catalogue_sections = [
        "engine",
        "transmission",
        "clutch",
        "steering",
        "front axle",
        "rear axle",
        "suspension",
        "brake",
        "electrical",
        "cooling",
        "fuel system",
        "body",
        "air conditioning",
        "dashboard",
        "radiator",
    ]

    matches = get_close_matches(
        query,
        catalogue_sections,
        n=1,
        cutoff=0.35,
    )

    if matches:
        state["normalized_query"] = matches[0]
    else:
        state["normalized_query"] = query

    state["status"] = "query_normalized"
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


pdf_document: Any


def locate_relevant_pages(state: DocumentState) -> DocumentState:
    """
    Find pages relevant to the user's query.
    """
    pdf = state["pdf_document"]
    query = state["user_query"].lower()

    pages = []

    for page_number in range(len(pdf)):
        page = pdf.load_page(page_number)
        text = page.get_text().lower()

        if query in text:
            pages.append(page_number + 1)

    state["relevant_pages"] = pages
    state["status"] = "pages_located"

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


def retrieve_relevant_pages(state: DocumentState) -> DocumentState:
    """
    Rank pages according to how well they match the query.
    """
    query = state["user_query"].lower()
    query_words = re.findall(r"\w+", query)

    scores = []

    for page_number, text in state["page_index"].items():
        page_text = text.lower()
        score = 0

        for word in query_words:
            score += page_text.count(word)

        if score > 0:
            scores.append((page_number, score))

    scores.sort(key=lambda x: x[1], reverse=True)

    state["relevant_pages"] = [page for page, _ in scores[:5]]

    # -----------------------------
    # Check if any relevant pages were found
    # -----------------------------
    if not state["relevant_pages"]:
        state["status"] = "failed"
        state["error"] = "No relevant pages found for the given query."
        return state

    state["status"] = "pages_retrieved"

    return state


...
import pdfplumber

def extract_relevant_content(state: DocumentState) -> DocumentState:
    """
    Extract text and tables from the retrieved pages.
    """
    pdf_path = state["pdf_path"]
    pages = state["relevant_pages"]

    extracted_text = []
    extracted_tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number in pages:
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
    text = text.replace("*", "")
    text = text.replace(")", "")
    text = re.sub(r"\s+", " ", text)

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
    bom = json.loads(response.content)

    state["bom"] = bom
    state["status"] = "bom_generated"

    return state


def validate_bom(state: DocumentState) -> DocumentState:
    """
    Validate the generated BOM against the schema.
    """
    validated = BOM.model_validate(state["bom"])

    state["bom"] = validated.model_dump()
    state["status"] = "completed"

    return state