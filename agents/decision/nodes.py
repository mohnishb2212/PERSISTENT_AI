import json
from pathlib import Path

from .schemas import InventorySchema
from .state import DecisionState

def validate_input(state: DecisionState):

    try:
        InventorySchema(**state["inventory"])

        state["status"] = "SUCCESS"

    except Exception as e:

        state["status"] = "FAILED"
        state["error"] = str(e)

        raise

    return state


def analyze_inventory(state: DecisionState):

    inventory = state["inventory"]

    decision_parts = []

    for part in inventory["parts"]:

        required = part["required_quantity"]
        available = part["available_quantity"]
        threshold = part["minimum_threshold"]

        remaining = max(0, available - required)

        procurement = max(0, required - available)

        # -----------------------------
        # Decide status
        # -----------------------------

        if available == 0:

            status = "OUT_OF_STOCK"

        elif available < required:

            status = "SHORTAGE"

        elif remaining < threshold:

            status = "LOW_STOCK_AFTER_ASSEMBLY"

        else:

            status = "AVAILABLE"

        decision_parts.append({

            "item": part["item"],

            "part_number": part["part_number"],

            "description": part["description"],

            "required_quantity": required,

            "available_quantity": available,

            "remaining_quantity": remaining,

            "minimum_threshold": threshold,

            "status": status,

            "procurement_required": procurement,

            "rack_location": part["rack_location"],

            "supplier": part["supplier"]

        })

    state["decision"] = {

        "assembly": inventory["assembly"],

        "catalogue": inventory["catalogue"],

        "total_parts": inventory["total_parts"],

        "parts": decision_parts

    }

    return state


def generate_summary(state: DecisionState):

    decision = state["decision"]

    available = 0
    low_stock = 0
    shortage = 0
    out_of_stock = 0

    procurement = 0

    for part in decision["parts"]:

        procurement += part["procurement_required"]

        if part["status"] == "AVAILABLE":
            available += 1

        elif part["status"] == "LOW_STOCK_AFTER_ASSEMBLY":
            low_stock += 1

        elif part["status"] == "SHORTAGE":
            shortage += 1

        elif part["status"] == "OUT_OF_STOCK":
            out_of_stock += 1

    if shortage == 0 and out_of_stock == 0:
        assembly_status = "ASSEMBLY READY"
    else:
        assembly_status = "ASSEMBLY NOT READY"

    decision["assembly_status"] = assembly_status

    decision["summary"] = {

        "total_parts": decision["total_parts"],

        "available": available,

        "low_stock": low_stock,

        "shortage": shortage,

        "out_of_stock": out_of_stock,

        "total_procurement_required": procurement

    }

    return state



def save_decision(state: DecisionState):

    output_dir = Path("output")

    output_dir.mkdir(exist_ok=True)

    filename = (

        state["decision"]["assembly"]

        .replace(" ", "_")

        + "_decision.json"

    )

    output_path = output_dir / filename

    with open(output_path, "w") as f:

        json.dump(

            state["decision"],

            f,

            indent=4

        )

    state["output_file"] = str(output_path)

    print("Decision saved")

    print(output_path)

    return state