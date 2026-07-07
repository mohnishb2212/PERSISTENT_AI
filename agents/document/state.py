from typing import TypedDict, List, Dict, Any


class DocumentState(TypedDict):
    # -------- Input --------
    pdf_path: str
    user_query: str

    # -------- Query Processing --------
    assembly_name: str

    # -------- Retrieval --------
    page_index: Dict[int, str]
    relevant_pages: List[int]

    # -------- Extraction --------
    extracted_text: str
    extracted_tables: List[Dict[str, Any]]

    # -------- Final Output --------
    bom: Dict[str, Any]

    # -------- Status --------
    status: str
    error: str

    normalized_query: str

    pdf_document: Any