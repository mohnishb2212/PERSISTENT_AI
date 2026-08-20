from .graph import build_graph


class VisionAgent:
    """Vision Agent: image -> assembly/callouts -> database -> unified BOM."""

    def __init__(self):
        self.graph = build_graph()

    def invoke(self, image_path, catalogue_name):
        state = {
            "image_path": str(image_path),
            "catalogue_name": str(catalogue_name),
            "image_base64": None,
            "vision_extraction": None,
            "resolved_assembly": None,
            "bom": None,
            "output_file": None,
            "status": "",
            "error": "",
        }

        return self.graph.invoke(state)