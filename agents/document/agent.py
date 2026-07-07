from .graph import build_document_graph

class DocumentAgent:

    def __init__(self):
        self.graph = build_document_graph()

    def invoke(self, pdf_path: str, query: str):

        state = {
            "pdf_path": pdf_path,
            "user_query": query,

            "assembly_name": "",

            "page_index": {},
            "relevant_pages": [],

            "extracted_text": "",
            "extracted_tables": [],

            "bom": {},

            "status": "",
            "error": ""
        }
        return self.graph.invoke(state)