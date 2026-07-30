import time

from agents.document import DocumentAgent
from agents.inventory import InventoryAgent
from agents.decision import DecisionAgent
from agents.report import ReportAgent

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

    pdf_path = input("Enter PDF path: ").strip()

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

    print("✓ BOM extracted successfully.")

    # --------------------------------------------------
    # Inventory Agent
    # --------------------------------------------------

    print_step(2, "Running Inventory Agent")

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