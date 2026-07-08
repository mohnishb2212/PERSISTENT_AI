from agents.document import DocumentAgent
from tabulate import tabulate

# Create agent
agent = DocumentAgent()

# -----------------------------
# Save workflow graph as PNG
# -----------------------------
png = agent.graph.get_graph().draw_mermaid_png()

with open("document_graph_2.png", "wb") as f:
    f.write(png)

print("Workflow graph saved as document_graph_2.png")

# -----------------------------
# Run the agent
# -----------------------------
result = agent.invoke(
    pdf_path="CATALOGUES/APOLLO_TRACTORS.pdf",
    query= "WHEEL DRIVE"
)

# -----------------------------
# Display BOM
# -----------------------------
rows = []

for part in result["bom"]["parts"]:
    rows.append([
        part["item"],
        part["part_number"],
        part["description"],
        part["quantity"],
        part["remarks"],
    ])

print("\nAssembly :", result["bom"]["assembly"])
print("Catalogue:", result["bom"]["catalogue"])
print("Total Parts:", result["bom"]["total_parts"])
print()

print(
    tabulate(
        rows,
        headers=[
            "Item",
            "Part Number",
            "Description",
            "Qty",
            "Remarks",
        ],
        tablefmt="grid",
    )
)