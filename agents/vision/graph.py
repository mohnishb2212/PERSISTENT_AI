from langgraph.graph import StateGraph, START, END

from .state import VisionState

from .nodes import (
    validate_input,
    load_image,
    analyze_components,
    analyze_quantities,
    integrate_results,
    validate_output,
    save_output,
)


def build_graph():

    graph = StateGraph(VisionState)

    # --------------------------------------------------
    # Nodes
    # --------------------------------------------------

    graph.add_node(
        "validate_input",
        validate_input
    )

    graph.add_node(
        "load_image",
        load_image
    )

    graph.add_node(
        "analyze_components",
        analyze_components
    )

    graph.add_node(
        "analyze_quantities",
        analyze_quantities
    )

    graph.add_node(
        "integrate_results",
        integrate_results
    )

    graph.add_node(
        "validate_output",
        validate_output
    )

    graph.add_node(
        "save_output",
        save_output
    )

    # --------------------------------------------------
    # Edges
    # --------------------------------------------------

    graph.add_edge(
        START,
        "validate_input"
    )

    graph.add_edge(
        "validate_input",
        "load_image"
    )

    # Parallel branches
    graph.add_edge(
        "load_image",
        "analyze_components"
    )

    graph.add_edge(
        "load_image",
        "analyze_quantities"
    )

    # Merge
    graph.add_edge(
        "analyze_components",
        "integrate_results"
    )

    graph.add_edge(
        "analyze_quantities",
        "integrate_results"
    )

    # Final flow
    graph.add_edge(
        "integrate_results",
        "validate_output"
    )

    graph.add_edge(
        "validate_output",
        "save_output"
    )

    graph.add_edge(
        "save_output",
        END
    )

    return graph.compile()