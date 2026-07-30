from pathlib import Path
import json

from .db import connect_database, get_part, close_database
from .schemas import Inventory


def validate_input(state):

    if not state["bom"]:
        raise ValueError("BOM is empty.")

    if "parts" not in state["bom"]:
        raise ValueError("No parts found in BOM.")

    state["status"] = "Input validated"

    return state

def connect_inventory(state):

    state["connection"] = connect_database()

    state["status"] = "Database connected"

    return state

def lookup_inventory(state):

    bom = state["bom"]

    connection = state["connection"]

    inventory_parts = []

    for part in bom["parts"]:

        result = get_part(connection, part["part_number"])

        if result:

            inventory_parts.append({

                "item": part["item"],

                "part_number": part["part_number"],

                "description": part["description"],

                "required_quantity": part["quantity"],

                "available_quantity": result["available_qty"],
                "minimum_threshold": result["min_threshold"],
                "rack_location": result["rack_location"],
                "supplier": result["supplier"],

                "remarks": part["remarks"]

            })

        else:

            inventory_parts.append({

                "item": part["item"],

                "part_number": part["part_number"],

                "description": part["description"],

                "required_quantity": part["quantity"],

                "available_quantity": 0,

                "minimum_threshold": 0,

                "rack_location": "UNKNOWN",

                "supplier": "UNKNOWN",

                "remarks": part["remarks"]

            })

    state["inventory"] = {

        "assembly": bom["assembly"],

        "catalogue": bom["catalogue"],

        "total_parts": bom["total_parts"],

        "parts": inventory_parts

    }

    state["status"] = "Inventory lookup completed"

    return state

def validate_inventory(state):

    Inventory.model_validate(state["inventory"])

    state["status"] = "Inventory validated"

    return state

def save_inventory(state):

    output_path = Path("output")

    output_path.mkdir(exist_ok=True)

    filename = (
        state["inventory"]["assembly"]
        .replace(" ", "_")
        .replace("/", "_")
    )

    file = output_path / f"{filename}_inventory.json"

    with open(file, "w") as f:

        json.dump(state["inventory"], f, indent=4)

    state["output_file"] = str(file)

    close_database(state["connection"])

    state["status"] = "Inventory saved"

    return state