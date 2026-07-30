from .graph import build_inventory_graph


class InventoryAgent:

    def __init__(self):
        self.graph = build_inventory_graph()


    def invoke(self, bom: dict):

        state = {
            "bom": bom,

            "connection": None,

            "inventory": {},

            "output_file": "",

            "status": "",

            "error": "",
        }

        return self.graph.invoke(state)