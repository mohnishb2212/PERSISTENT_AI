from agents.document.nodes import (
    validate_input,
    normalize_query,
    load_pdf,
    build_page_index,
    retrieve_relevant_pages,
    extract_relevant_content,
)

state = {
    "pdf_path": "CATALOGUES/MS_NEXA_CIAZ.pdf",
    "user_query": "Steering Assembly",

    "assembly_name": "",
    "normalized_query": "",

    "page_index": {},
    "relevant_pages": [],

    "extracted_text": "",
    "extracted_tables": [],

    "bom": {},

    "status": "",
    "error": ""
}

functions = [
    validate_input,
    normalize_query,
    load_pdf,
    build_page_index,
    retrieve_relevant_pages,
    extract_relevant_content,
]

for fn in functions:
    print(f"\nRunning: {fn.__name__}")

    state = fn(state)

    print("Status:", state["status"])

    if state["error"]:
        print("Error:", state["error"])
        break

print("\nRelevant Pages:")
print(state["relevant_pages"])

print("\nExtracted Text Length:")
print(len(state["extracted_text"]))