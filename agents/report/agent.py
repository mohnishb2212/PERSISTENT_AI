from .graph import build_report_graph


class ReportAgent:

    def __init__(self):
        self.graph = build_report_graph()

    def invoke(self, decision: dict):

        state = {

            "decision": decision,

            "report": "",

            "output_file": "",

            "status": "",

            "error": "",

        }

        return self.graph.invoke(state)