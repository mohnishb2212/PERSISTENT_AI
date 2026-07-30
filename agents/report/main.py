import json

from .agent import ReportAgent


def main():

    # Load Decision Agent output
    with open(
        "output/Parts_Manual_WHEEL_DRIVE_decision.json",
        "r",
    ) as f:

        decision = json.load(f)

    # Create Report Agent
    agent = ReportAgent()

    # Run Report Agent
    result = agent.invoke(decision)

    print("\nReport Agent Executed Successfully!\n")

    print("Status :", result["status"])

    print("Output :", result["output_file"])

    # Save Graph Visualization
    png = agent.graph.get_graph().draw_mermaid_png()

    with open("report_graph.png", "wb") as f:
        f.write(png)

    print("Report graph saved as report_graph.png")


if __name__ == "__main__":
    main()