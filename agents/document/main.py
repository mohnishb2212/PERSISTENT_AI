from pathlib import Path
from tabulate import tabulate

from agents.document import DocumentAgent
from agents.document.human_review import human_review


# -------------------------------------------------
# Configuration
# -------------------------------------------------

pdf_path = "CATALOGUES/APOLLO_TRACTORS.pdf"
query = "AUXILLIARY DRIVE (AP600) "


# -------------------------------------------------
# Create Document Agent
# -------------------------------------------------

agent = DocumentAgent()


# -------------------------------------------------
# Save workflow graph as PNG
# -------------------------------------------------

png = agent.graph.get_graph().draw_mermaid_png()

with open("document_graph.png", "wb") as f:
    f.write(png)

print("Workflow graph saved as document_graph.png")


# -------------------------------------------------
# Run Document Agent
# -------------------------------------------------

result = agent.invoke(
    pdf_path=pdf_path,
    query=query
)


# -------------------------------------------------
# Check Document Agent result
# -------------------------------------------------

if result.get("status") == "failed":

    print("\n✗ Document Agent failed.")
    print("Error:", result.get("error"))
    exit()


document_bom = result["bom"]


# -------------------------------------------------
# Ensure metadata is present
# -------------------------------------------------

document_bom["assembly"] = query
document_bom["catalogue"] = Path(pdf_path).stem
document_bom["total_parts"] = len(
    document_bom.get("parts", [])
)


# -------------------------------------------------
# HUMAN-IN-THE-LOOP
# -------------------------------------------------

print("\n")
print("=" * 100)
print("DOCUMENT AGENT COMPLETED")
print("=" * 100)

print("\nExtracted BOM is ready for human review.")

review_result = human_review(document_bom)


# -------------------------------------------------
# Handle Human Decision
# -------------------------------------------------

if review_result["status"] == "rejected":

    print("\n")
    print("=" * 100)
    print("PIPELINE STOPPED")
    print("=" * 100)

    print("\nHuman reviewer rejected the BOM.")
    print("Inventory Agent will NOT be called.")

    exit()


# -------------------------------------------------
# Approved BOM
# -------------------------------------------------

approved_bom = review_result["bom"]


print("\n")
print("=" * 100)
print("HUMAN REVIEW COMPLETED")
print("=" * 100)

print("\n✓ BOM approved.")
print("\nFinal approved BOM:\n")


# -------------------------------------------------
# Display final BOM
# -------------------------------------------------

rows = []

for part in approved_bom["parts"]:

    quantity = part.get("quantity")

    # Display blank instead of None
    if quantity is None:
        quantity = ""

    rows.append([
        part.get("item", ""),
        part.get("part_number", ""),
        part.get("description", ""),
        quantity,
        part.get("remarks", "")
    ])


print(
    tabulate(
        rows,
        headers=[
            "Item",
            "Part Number",
            "Description",
            "Qty",
            "Remarks"
        ],
        tablefmt="grid"
    )
)


print("\nTotal Parts:", approved_bom["total_parts"])


# -------------------------------------------------
# TEMPORARY
# -------------------------------------------------

print("\n")
print("=" * 100)
print("HITL TEST COMPLETED SUCCESSFULLY")
print("=" * 100)

print("\nThe approved BOM is now ready to be passed")
print("to the Inventory Agent.")

# Inventory Agent will be connected here later.