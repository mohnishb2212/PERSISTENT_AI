from langgraph.graph import StateGraph, END
from .state import DocumentState
from .nodes import (
    validate_input,
    normalize_query,
    load_pdf,
    check_pdf_type,
    build_page_index,
    ocr_pdf,
    retrieve_relevant_pages,
    extract_relevant_content,
    generate_bom,
    validate_bom,
    route_pdf
)

def build_document_graph():
    workflow = StateGraph(DocumentState)
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("normalize_query", normalize_query)
    workflow.add_node("load_pdf", load_pdf)
    workflow.add_node("check_pdf_type", check_pdf_type)
    workflow.add_node("build_page_index", build_page_index)
    workflow.add_node("ocr_pdf", ocr_pdf)
    workflow.add_node("retrieve_pages", retrieve_relevant_pages)
    workflow.add_node("extract_content", extract_relevant_content)
    workflow.add_node("generate_bom", generate_bom)
    workflow.add_node("validate_bom", validate_bom)

    workflow.set_entry_point("validate_input")

    workflow.add_edge(
        "validate_input",
        "normalize_query"
    )
    workflow.add_edge(
        "normalize_query",
        "load_pdf"
    )
    workflow.add_edge(
    "load_pdf",
    "check_pdf_type"
    )
    workflow.add_conditional_edges(
    "check_pdf_type",
    route_pdf,
    {
        "searchable": "build_page_index",
        "scanned": "ocr_pdf",
    }
    )
    workflow.add_edge(
    "ocr_pdf",
    "retrieve_pages"
    )
    workflow.add_edge(
        "build_page_index",
        "retrieve_pages"
    )
    workflow.add_edge(
        "retrieve_pages",
        "extract_content"
    )
    workflow.add_edge(
        "extract_content",
        "generate_bom"
    )
    workflow.add_edge(
        "generate_bom",
        "validate_bom"
    )
    workflow.add_edge(
        "validate_bom",
        END
    )
    return workflow.compile()