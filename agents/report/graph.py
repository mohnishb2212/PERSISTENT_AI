from langgraph.graph import StateGraph, START, END

from .state import ReportState

from .nodes import (
    validate_input,
    generate_report,
    save_report,
)


def build_report_graph():

    builder = StateGraph(ReportState)

    # Nodes
    builder.add_node("validate_input", validate_input)
    builder.add_node("generate_report", generate_report)
    builder.add_node("save_report", save_report)

    # Edges
    builder.add_edge(START, "validate_input")

    builder.add_edge("validate_input", "generate_report")

    builder.add_edge("generate_report", "save_report")

    builder.add_edge("save_report", END)

    return builder.compile()