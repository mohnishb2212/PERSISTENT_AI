import time

from agents.document import DocumentAgent
from agents.inventory import InventoryAgent
from agents.decision import DecisionAgent
from agents.report import ReportAgent
from agents.document.human_review import human_review

# The above code is valid for only 4 assemblies 
# 1) apollo tractors wheel drive
# 2) mahindra scorpio hand brake
# 3) mahindra thar flywheel
# 4) tata indica intake and exhause valve

def print_step(step, message):
    print(f"\n{'=' * 60}")
    print(f"[STEP {step}] {message}")
    print(f"{'=' * 60}")


def main():

    # --------------------------------------------------
    # User Input
    # --------------------------------------------------

    # Available catalogues
    pdf_options = {
        "1": ("Apollo Tractors", "CATALOGUES/APOLLO_TRACTORS.pdf"),
        "2": ("Mahindra Scorpio", "CATALOGUES/MAHINDRA_SCORPIO.pdf"),
        "3": ("Mahindra Thar", "CATALOGUES/MAHINDRA_THAR.pdf"),
        "4": ("Tata Indica", "CATALOGUES/TATA_INDICA.pdf"),
    }

    print("\nAvailable Catalogues:")
    for number, (name, path) in pdf_options.items():
        print(f"{number}. {name}")

    while True:
        choice = input("\nSelect catalogue (1-4): ").strip()

        if choice in pdf_options:
            pdf_name, pdf_path = pdf_options[choice]
            break

        print("Invalid choice. Please select 1, 2, 3, or 4.")

    print(f"\nSelected Catalogue: {pdf_name}")
    print(f"PDF: {pdf_path}")

    # Assembly name is still entered manually
    query = input("Enter Assembly Name: ").strip()

    start_time = time.time()

    # --------------------------------------------------
    # Initialize Agents
    # --------------------------------------------------

    print_step(0, "Initializing Agents")

    document_agent = DocumentAgent()

    inventory_agent = InventoryAgent()

    decision_agent = DecisionAgent()

    report_agent = ReportAgent()

    print("✓ All agents initialized.")

    # --------------------------------------------------
    # Document Agent
    # --------------------------------------------------

    print_step(1, "Running Document Agent")

    document_result = document_agent.invoke(
        pdf_path,
        query
    )

    bom = document_result["bom"]

    from pathlib import Path

    bom["assembly"] = query
    bom["catalogue"] = Path(pdf_path).stem
    bom["total_parts"] = len(bom.get("parts", []))

    print("✓ BOM extracted successfully.")

    # --------------------------------------------------
    # HUMAN-IN-THE-LOOP
    # --------------------------------------------------

    print_step(2, "Human BOM Review")

    review_result = human_review(bom)

    # If human rejects the BOM, stop the pipeline
    if review_result["status"] == "rejected":

        print("\n✗ BOM rejected by human reviewer.")
        print("Pipeline stopped.")
        return

    # Use the human-approved / edited BOM
    bom = review_result["bom"]

    print("\n✓ BOM approved by human reviewer.")


    # --------------------------------------------------
    # Inventory Agent
    # --------------------------------------------------

    print_step(3, "Running Inventory Agent")

    inventory_result = inventory_agent.invoke(bom)

    inventory = inventory_result["inventory"]

    print("✓ Inventory checked.")

    # --------------------------------------------------
    # Decision Agent
    # --------------------------------------------------

    print_step(3, "Running Decision Agent")

    decision_result = decision_agent.invoke(inventory)

    decision = decision_result["decision"]

    # Override with user inputs
    decision["assembly"] = query

    from pathlib import Path
    decision["catalogue"] = Path(pdf_path).stem.replace("_", " ")

    print("✓ Inventory analysis completed.")

    # --------------------------------------------------
    # Report Agent
    # --------------------------------------------------

    print_step(4, "Generating Report")

    report_result = report_agent.invoke(decision)

    print("✓ Report generated.")

    # --------------------------------------------------
    # Finish
    # --------------------------------------------------

    elapsed = time.time() - start_time

    print_step(5, "Completed")

    print(f"Output File : {report_result['output_file']}")

    print(f"Execution Time : {elapsed:.2f} seconds")

    print("\nPipeline executed successfully.")


if __name__ == "__main__":
    main()