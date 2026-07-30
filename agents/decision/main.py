import json

from .agent import DecisionAgent


def main():

    # Load Inventory Agent output
    with open(
        "output/Parts_Manual_WHEEL_DRIVE_inventory.json",
        "r",
    ) as f:

        inventory = json.load(f)

    # Create Decision Agent
    agent = DecisionAgent()

    # Run Decision Agent
    result = agent.invoke(inventory)

    print("\nDecision Agent Executed Successfully!\n")

    print("Status :", result["status"])

    print("Output :", result["output_file"])

    # -----------------------------
    # Save Graph Visualization
    # -----------------------------

    png = agent.graph.get_graph().draw_mermaid_png()

    with open("decision_graph.png", "wb") as f:
        f.write(png)

    print("Decision graph saved as decision_graph.png")


if __name__ == "__main__":
    main()