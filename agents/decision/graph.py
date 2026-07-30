from langgraph.graph import StateGraph, START, END

from .state import DecisionState

from .nodes import (
    validate_input,
    analyze_inventory,
    generate_summary,
    save_decision,
)


def build_decision_graph():

    builder = StateGraph(DecisionState)

    # Nodes
    builder.add_node("validate_input", validate_input)
    builder.add_node("analyze_inventory", analyze_inventory)
    builder.add_node("generate_summary", generate_summary)
    builder.add_node("save_decision", save_decision)

    # Edges
    builder.add_edge(START, "validate_input")

    builder.add_edge("validate_input", "analyze_inventory")

    builder.add_edge("analyze_inventory", "generate_summary")

    builder.add_edge("generate_summary", "save_decision")

    builder.add_edge("save_decision", END)

    return builder.compile()