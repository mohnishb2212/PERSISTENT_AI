from langgraph.graph import StateGraph, START, END

from .state import VisionState

from .nodes import (
    validate_input,
    load_image,
    analyze_image,
    validate_output,
    save_output,
)


def build_graph():

    graph = StateGraph(VisionState)

    graph.add_node("validate_input", validate_input)

    graph.add_node("load_image", load_image)

    graph.add_node("analyze_image", analyze_image)

    graph.add_node("validate_output", validate_output)

    graph.add_node("save_output", save_output)

    graph.add_edge(START, "validate_input")

    graph.add_edge("validate_input", "load_image")

    graph.add_edge("load_image", "analyze_image")

    graph.add_edge("analyze_image", "validate_output")

    graph.add_edge("validate_output", "save_output")

    graph.add_edge("save_output", END)

    return graph.compile()