from langgraph.graph import StateGraph, END

from .state import InventoryState
from .nodes import (
    validate_input,
    connect_inventory,
    lookup_inventory,
    validate_inventory,
    save_inventory,
)


def build_inventory_graph():
    
    graph = StateGraph(InventoryState)

    graph.add_node("validate_input", validate_input)
    graph.add_node("connect_inventory", connect_inventory)
    graph.add_node("lookup_inventory", lookup_inventory)
    graph.add_node("validate_inventory", validate_inventory)
    graph.add_node("save_inventory", save_inventory)

    graph.set_entry_point("validate_input")

    graph.add_edge("validate_input", "connect_inventory")
    graph.add_edge("connect_inventory", "lookup_inventory")
    graph.add_edge("lookup_inventory", "validate_inventory")
    graph.add_edge("validate_inventory", "save_inventory")
    graph.add_edge("save_inventory", END)

    return graph.compile()