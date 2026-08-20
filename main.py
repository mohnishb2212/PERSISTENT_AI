import time
from pathlib import Path

from agents.document import DocumentAgent
from agents.inventory import InventoryAgent
from agents.decision import DecisionAgent
from agents.report import ReportAgent
from agents.vision import VisionAgent
from agents.document.human_review import human_review


# ============================================================
# CONFIGURATION
# ============================================================

# Built-in catalogues used by the current prototype.
#
# The canonical names are used for the Vision Agent because
# they match the names stored in the central SQLite database.
#
# The display names are used for user-friendly terminal output.
CATALOGUES = {
    "1": {
        "display_name": "Apollo Tractors",
        "catalogue_name": "APOLLO_TRACTORS",
        "pdf_path": "CATALOGUES/APOLLO_TRACTORS.pdf",
    },
    "2": {
        "display_name": "Mahindra Scorpio",
        "catalogue_name": "MAHINDRA_SCORPIO",
        "pdf_path": "CATALOGUES/MAHINDRA_SCORPIO.pdf",
    },
    "3": {
        "display_name": "Mahindra Thar",
        "catalogue_name": "MAHINDRA_THAR",
        "pdf_path": "CATALOGUES/MAHINDRA_THAR.pdf",
    },
    "4": {
        "display_name": "Tata Indica",
        "catalogue_name": "TATA_INDICA",
        "pdf_path": "CATALOGUES/TATA_INDICA.pdf",
    },
}


# ============================================================
# HELPERS
# ============================================================

def print_step(step, message):
    print(f"\n{'=' * 60}")
    print(f"[STEP {step}] {message}")
    print(f"{'=' * 60}")


def select_input_type():
    """
    Ask whether the user wants to process a PDF or an image.
    """

    print("\nInput Type:")
    print("1. PDF Catalogue")
    print("2. Assembly Image")

    while True:

        choice = input("\nSelect input type (1-2): ").strip()

        if choice == "1":
            return "pdf"

        if choice == "2":
            return "image"

        print("Invalid choice. Please select 1 or 2.")


def select_catalogue():
    """
    Display the available catalogues and return the selected
    catalogue metadata.
    """

    print("\nAvailable Catalogues:")

    for number, catalogue in CATALOGUES.items():

        print(
            f"{number}. "
            f"{catalogue['display_name']}"
        )

    while True:

        choice = input(
            "\nSelect catalogue (1-4): "
        ).strip()

        if choice in CATALOGUES:

            return CATALOGUES[choice]

        print(
            "Invalid choice. "
            "Please select 1, 2, 3, or 4."
        )


def prepare_bom_metadata(
    bom,
    assembly_name,
    catalogue_name,
):
    """
    Ensure both Document Agent and Vision Agent outputs
    have the same metadata structure before entering
    Human Review.
    """

    bom["assembly"] = assembly_name

    bom["catalogue"] = catalogue_name

    bom["total_parts"] = len(
        bom.get("parts", [])
    )

    return bom


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    start_time = time.time()

    # --------------------------------------------------------
    # STEP 0 — INPUT TYPE
    # --------------------------------------------------------

    input_type = select_input_type()

    # --------------------------------------------------------
    # STEP 0.5 — CATALOGUE
    # --------------------------------------------------------

    catalogue = select_catalogue()

    display_catalogue_name = (
        catalogue["display_name"]
    )

    canonical_catalogue_name = (
        catalogue["catalogue_name"]
    )

    pdf_path = catalogue["pdf_path"]

    print(
        f"\nSelected Catalogue: "
        f"{display_catalogue_name}"
    )

    # --------------------------------------------------------
    # INPUT-SPECIFIC INFORMATION
    # --------------------------------------------------------

    query = None
    image_path = None

    # ========================================================
    # PDF INPUT
    # ========================================================

    if input_type == "pdf":

        print(
            f"PDF: {pdf_path}"
        )

        # Assembly is the only additional value required
        # from the user for the Document Agent.
        query = input(
            "\nEnter Assembly Name: "
        ).strip()

        if not query:

            print(
                "\nError: Assembly name cannot be empty."
            )

            return

    # ========================================================
    # IMAGE INPUT
    # ========================================================

    elif input_type == "image":

        # The user only needs to provide the image path.
        image_path = input(
            "\nEnter image path: "
        ).strip()

        if not image_path:

            print(
                "\nError: Image path cannot be empty."
            )

            return

        # Basic path validation before initializing agents.
        image_file = Path(image_path)

        if not image_file.exists():

            print(
                f"\nError: Image not found:\n"
                f"{image_file}"
            )

            return

        if image_file.suffix.lower() not in {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        }:

            print(
                "\nError: Vision Agent supports "
                "PNG, JPG, JPEG, and WEBP images."
            )

            return

    # --------------------------------------------------------
    # INITIALIZE AGENTS
    # --------------------------------------------------------

    print_step(
        0,
        "Initializing Agents"
    )

    document_agent = None
    vision_agent = None

    # Only initialize the extraction agent that is actually
    # needed for this run.
    if input_type == "pdf":

        document_agent = DocumentAgent()

    else:

        vision_agent = VisionAgent()

    inventory_agent = InventoryAgent()

    decision_agent = DecisionAgent()

    report_agent = ReportAgent()

    print("✓ Agents initialized.")

    # ========================================================
    # STEP 1 — DOCUMENT / VISION AGENT
    # ========================================================

    if input_type == "pdf":

        print_step(
            1,
            "Running Document Agent"
        )

        try:

            document_result = (
                document_agent.invoke(
                    pdf_path,
                    query,
                )
            )

        except Exception as exc:

            print(
                "\n✗ Document Agent failed."
            )

            print(
                f"Error: {exc}"
            )

            return

        if (
            not isinstance(
                document_result,
                dict,
            )
            or document_result.get("bom") is None
        ):

            print(
                "\n✗ Document Agent did not "
                "return a valid BOM."
            )

            if isinstance(
                document_result,
                dict,
            ):

                print(
                    f"Status: "
                    f"{document_result.get('status')}"
                )

                print(
                    f"Error: "
                    f"{document_result.get('error')}"
                )

            return

        bom = document_result["bom"]

        # The Document Agent output is normalized into
        # the common BOM structure.
        bom = prepare_bom_metadata(
            bom=bom,
            assembly_name=query,
            catalogue_name=(
                Path(pdf_path).stem
            ),
        )

        print(
            "\n✓ BOM extracted successfully."
        )

    else:

        print_step(
            1,
            "Running Vision Agent"
        )

        try:

            vision_result = (
                vision_agent.invoke(
                    image_path,
                    canonical_catalogue_name,
                )
            )

        except Exception as exc:

            print(
                "\n✗ Vision Agent failed."
            )

            print(
                f"Error: {exc}"
            )

            return

        if (
            not isinstance(
                vision_result,
                dict,
            )
            or vision_result.get("bom") is None
        ):

            print(
                "\n✗ Vision Agent did not "
                "return a valid BOM."
            )

            if isinstance(
                vision_result,
                dict,
            ):

                print(
                    f"Status: "
                    f"{vision_result.get('status')}"
                )

                print(
                    f"Error: "
                    f"{vision_result.get('error')}"
                )

            return

        vision_bom = (
            vision_result["bom"]
        )

        # Vision Agent already returns a unified BOM.
        #
        # We still normalize the fields here so that both
        # extraction paths produce exactly the same object
        # before Human Review.
        if hasattr(
            vision_bom,
            "model_dump",
        ):

            bom = (
                vision_bom.model_dump()
            )

        else:

            bom = dict(
                vision_bom
            )

        bom = prepare_bom_metadata(
            bom=bom,
            assembly_name=bom.get(
                "assembly",
                "",
            ),
            catalogue_name=canonical_catalogue_name,
        )

        print(
            "\n✓ Vision BOM extracted "
            "and mapped successfully."
        )

    # ========================================================
    # DISPLAY EXTRACTED BOM SUMMARY
    # ========================================================

    print(
        f"\nAssembly : "
        f"{bom.get('assembly', '')}"
    )

    print(
        f"Catalogue: "
        f"{bom.get('catalogue', '')}"
    )

    print(
        f"Parts    : "
        f"{len(bom.get('parts', []))}"
    )

    # ========================================================
    # STEP 2 — HUMAN-IN-THE-LOOP
    # ========================================================

    print_step(
        2,
        "Human BOM Review"
    )

    try:

        review_result = (
            human_review(bom)
        )

    except Exception as exc:

        print(
            "\n✗ Human Review failed."
        )

        print(
            f"Error: {exc}"
        )

        return

    # --------------------------------------------------------
    # REJECTION
    # --------------------------------------------------------

    if (
        review_result.get("status")
        == "rejected"
    ):

        print(
            "\n✗ BOM rejected "
            "by human reviewer."
        )

        print(
            "Pipeline stopped."
        )

        return

    # --------------------------------------------------------
    # APPROVAL
    # --------------------------------------------------------

    bom = review_result["bom"]

    print(
        "\n✓ BOM approved "
        "by human reviewer."
    )

    # ========================================================
    # STEP 3 — INVENTORY AGENT
    # ========================================================

    print_step(
        3,
        "Running Inventory Agent"
    )

    try:

        inventory_result = (
            inventory_agent.invoke(
                bom
            )
        )

    except Exception as exc:

        print(
            "\n✗ Inventory Agent failed."
        )

        print(
            f"Error: {exc}"
        )

        return

    if (
        not isinstance(
            inventory_result,
            dict,
        )
        or inventory_result.get(
            "inventory"
        ) is None
    ):

        print(
            "\n✗ Inventory Agent did not "
            "return valid inventory data."
        )

        if isinstance(
            inventory_result,
            dict,
        ):

            print(
                f"Status: "
                f"{inventory_result.get('status')}"
            )

            print(
                f"Error: "
                f"{inventory_result.get('error')}"
            )

        return

    inventory = (
        inventory_result["inventory"]
    )

    print(
        "\n✓ Inventory checked."
    )

    # ========================================================
    # STEP 4 — DECISION AGENT
    # ========================================================

    print_step(
        4,
        "Running Decision Agent"
    )

    try:

        decision_result = (
            decision_agent.invoke(
                inventory
            )
        )

    except Exception as exc:

        print(
            "\n✗ Decision Agent failed."
        )

        print(
            f"Error: {exc}"
        )

        return

    if (
        not isinstance(
            decision_result,
            dict,
        )
        or decision_result.get(
            "decision"
        ) is None
    ):

        print(
            "\n✗ Decision Agent did not "
            "return a valid decision."
        )

        if isinstance(
            decision_result,
            dict,
        ):

            print(
                f"Status: "
                f"{decision_result.get('status')}"
            )

            print(
                f"Error: "
                f"{decision_result.get('error')}"
            )

        return

    decision = (
        decision_result["decision"]
    )

    # Always use the final human-approved BOM
    # as the authoritative assembly/catalogue.
    decision["assembly"] = (
        bom.get(
            "assembly",
            "",
        )
    )

    decision["catalogue"] = (
        bom.get(
            "catalogue",
            canonical_catalogue_name,
        )
    )

    print(
        "\n✓ Inventory analysis completed."
    )

    # ========================================================
    # STEP 5 — REPORT AGENT
    # ========================================================

    print_step(
        5,
        "Generating Report"
    )

    try:

        report_result = (
            report_agent.invoke(
                decision
            )
        )

    except Exception as exc:

        print(
            "\n✗ Report Agent failed."
        )

        print(
            f"Error: {exc}"
        )

        return

    if (
        not isinstance(
            report_result,
            dict,
        )
        or not report_result.get(
            "output_file"
        )
    ):

        print(
            "\n✗ Report Agent did not "
            "return a valid output file."
        )

        if isinstance(
            report_result,
            dict,
        ):

            print(
                f"Status: "
                f"{report_result.get('status')}"
            )

            print(
                f"Error: "
                f"{report_result.get('error')}"
            )

        return

    print(
        "\n✓ Report generated."
    )

    # ========================================================
    # FINISH
    # ========================================================

    elapsed = (
        time.time()
        - start_time
    )

    print_step(
        6,
        "Pipeline Completed"
    )

    print(
        f"Input Type   : "
        f"{'PDF' if input_type == 'pdf' else 'Image'}"
    )

    print(
        f"Catalogue    : "
        f"{display_catalogue_name}"
    )

    print(
        f"Assembly     : "
        f"{bom.get('assembly', '')}"
    )

    print(
        f"Output File  : "
        f"{report_result['output_file']}"
    )

    print(
        f"Execution Time : "
        f"{elapsed:.2f} seconds"
    )

    print(
        "\n✓ Pipeline executed successfully."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()