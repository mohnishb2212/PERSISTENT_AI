from langgraph.graph import StateGraph, END
from .state import DocumentState
from .nodes import (
    validate_input,
    load_pdf,
    build_page_index,
    retrieve_relevant_pages,
    extract_relevant_content,
    generate_bom,
    validate_bom,
    save_bom,
)

def build_document_graph():
    workflow = StateGraph(DocumentState)
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("load_pdf", load_pdf)
    workflow.add_node("build_page_index", build_page_index)
    workflow.add_node("retrieve_pages", retrieve_relevant_pages)
    workflow.add_node("extract_content", extract_relevant_content)
    workflow.add_node("generate_bom", generate_bom)
    workflow.add_node("validate_bom", validate_bom)
    workflow.add_node("save_bom", save_bom)
    workflow.set_entry_point("validate_input")

    workflow.add_edge(
        "validate_input",
        "load_pdf"
    )
    workflow.add_edge(
    "load_pdf",
    "build_page_index"
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
        "save_bom"
    )
    workflow.add_edge(
        "save_bom",
        END
    )
    return workflow.compile()