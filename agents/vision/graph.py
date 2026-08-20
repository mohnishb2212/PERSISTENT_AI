from langgraph.graph import StateGraph, START, END

from .state import VisionState
from .nodes import (
    validate_input,
    load_image,
    extract_assembly_and_callouts,
    map_callouts_to_bom,
    validate_output,
    save_output,
)


def build_graph():
    graph = StateGraph(VisionState)

    graph.add_node("validate_input", validate_input)
    graph.add_node("load_image", load_image)
    graph.add_node("extract_assembly_and_callouts", extract_assembly_and_callouts)
    graph.add_node("map_callouts_to_bom", map_callouts_to_bom)
    graph.add_node("validate_output", validate_output)
    graph.add_node("save_output", save_output)

    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "load_image")
    graph.add_edge("load_image", "extract_assembly_and_callouts")
    graph.add_edge("extract_assembly_and_callouts", "map_callouts_to_bom")
    graph.add_edge("map_callouts_to_bom", "validate_output")
    graph.add_edge("validate_output", "save_output")
    graph.add_edge("save_output", END)

    return graph.compile()