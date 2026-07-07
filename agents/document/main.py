from agents.document import DocumentAgent
import json
from tabulate import tabulate

agent = DocumentAgent()

result = agent.invoke(
    pdf_path="CATALOGUES/MS_NEXA_CIAZ.pdf",
    query="steering assembly"
)



rows = []

for part in result["bom"]["parts"]:
    rows.append([
        part["item"],
        part["part_number"],
        part["description"],
        part["quantity"],
        part["remarks"]
    ])

print("\nAssembly :", result["bom"]["assembly"])
print("Catalogue:", result["bom"]["catalogue"])
print("Total Parts:", result["bom"]["total_parts"])
print()

print(tabulate(
    rows,
    headers=[
        "Item",
        "Part Number",
        "Description",
        "Qty",
        "Remarks"
    ],
    tablefmt="grid"
))


from agents.document import DocumentAgent

agent = DocumentAgent()

# Save graph as PNG
png = agent.graph.get_graph().draw_mermaid_png()

with open("document_graph.png", "wb") as f:
    f.write(png)

result = agent.invoke(
    pdf_path="CATALOGUES/MS_NEXA_CIAZ.pdf",
    query="Steering Assembly"
)