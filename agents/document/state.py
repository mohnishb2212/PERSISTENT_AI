from typing import TypedDict, List, Dict, Any


class DocumentState(TypedDict):
    # ---------- Input ----------
    pdf_path: str
    user_query: str

    # ---------- Query ----------
    assembly_name: str

    # ---------- PDF ----------
    pdf_document: Any
    
    # ---------- Retrieval ----------
    page_index: Dict[int, str]        # extracted using pymupdf(just index and content)
    relevant_pages: List[int]

    # ---------- Extraction ----------
    extracted_text: str               # extracted using pdfplumber(high level - includes tables)
    extracted_tables: List[Dict[str, Any]]

    # ---------- Output ----------
    bom: Dict[str, Any]
    output_file: str

    # ---------- Status ----------
    status: str
    error: str