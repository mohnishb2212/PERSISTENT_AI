from .graph import build_decision_graph


class DecisionAgent:

    def __init__(self):
        self.graph = build_decision_graph()

    def invoke(self, inventory: dict):

        state = {

            "inventory": inventory,

            "decision": {},

            "output_file": "",

            "status": "",

            "error": "",

        }

        return self.graph.invoke(state)