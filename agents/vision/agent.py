from .graph import build_graph


class VisionAgent:

    def __init__(self):

        self.graph = build_graph()

    def invoke(self, image_path):

        state = {

            "image_path": image_path,

            "image_base64": None,

            "vision_result": None,

            "output_file": None

        }

        return self.graph.invoke(state)