import json
from pathlib import Path

from tabulate import tabulate

from .schemas import DecisionSchema
from .state import ReportState


def validate_input(state: ReportState):

    try:
        DecisionSchema(**state["decision"])

        state["status"] = "SUCCESS"

    except Exception as e:

        state["status"] = "FAILED"
        state["error"] = str(e)

        raise

    return state


def generate_report(state: ReportState):

    decision = state["decision"]

    report = []

    # ==================================================
    # Title
    # ==================================================

    report.append("# Automotive Spare Parts Inventory Report\n")

    report.append("---\n")

    # ==================================================
    # Assembly Information
    # ==================================================

    report.append("## Assembly Information\n")

    report.append(f"**Assembly:** {decision['assembly']}\n")

    report.append(f"**Catalogue:** {decision['catalogue']}\n")

    report.append("---\n")

    # ==================================================
    # Assembly Status
    # ==================================================

    report.append("## Assembly Status\n")

    report.append(f"**{decision['assembly_status']}**\n")

    report.append("---\n")

    # ==================================================
    # Summary
    # ==================================================

    summary = decision["summary"]

    report.append("## Summary\n")

    summary_rows = [
        ["Total Parts", summary["total_parts"]],
        ["Available", summary["available"]],
        ["Low Stock", summary["low_stock"]],
        ["Shortage", summary["shortage"]],
        ["Out Of Stock", summary["out_of_stock"]],
        ["Procurement Required", summary["total_procurement_required"]],
    ]

    report.append(
        tabulate(
            summary_rows,
            headers=["Metric", "Value"],
            tablefmt="github",
        )
    )

    report.append("\n---\n")

    # ==================================================
    # Part Details
    # ==================================================

    report.append("## Part Details\n")

    rows = []

    for part in decision["parts"]:

        rows.append([
            part["item"],
            part["part_number"],
            part["required_quantity"],
            part["available_quantity"],
            part["remaining_quantity"],
            part["status"],
            part["procurement_required"],
        ])

    report.append(
        tabulate(
            rows,
            headers=[
                "Item",
                "Part Number",
                "Required",
                "Available",
                "Remaining",
                "Status",
                "Procurement",
            ],
            tablefmt="github",
        )
    )

    report.append("\n---\n")

    # ==================================================
    # Procurement List
    # ==================================================

    report.append("## Procurement List\n")

    procurement_rows = []

    for part in decision["parts"]:

        if part["procurement_required"] > 0:

            procurement_rows.append([
                part["part_number"],
                part["description"],
                part["procurement_required"],
            ])

    if not procurement_rows:

        procurement_rows.append([
            "-",
            "None",
            0,
        ])

    report.append(
        tabulate(
            procurement_rows,
            headers=[
                "Part Number",
                "Description",
                "Quantity",
            ],
            tablefmt="github",
        )
    )

    report.append("\n---\n")

    # ==================================================
    # Recommendations
    # ==================================================

    report.append("## Recommendations\n")

    if decision["assembly_status"] == "ASSEMBLY READY":

        report.append("- Assembly can proceed.")
        report.append("- Inventory levels are sufficient.")

    else:

        report.append("- Assembly cannot begin until shortages are resolved.")
        report.append("- Procure all missing components.")
        report.append("- Recheck inventory after procurement.")

    state["report"] = "\n".join(report)

    return state


def save_report(state: ReportState):

    output_dir = Path("output")

    output_dir.mkdir(exist_ok=True)

    filename = (
        state["decision"]["assembly"]
        .replace(" ", "_")
        + "_report.md"
    )

    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:

        f.write(state["report"])

    state["output_file"] = str(output_path)

    print("✓ Report saved")

    print(output_path)

    return state