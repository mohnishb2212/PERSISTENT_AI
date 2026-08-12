from copy import deepcopy
from tabulate import tabulate
from .schemas import BOM


def display_bom(bom):
    """Display the BOM as a readable table."""

    rows = []

    for i, part in enumerate(bom.get("parts", []), start=1):
        rows.append([
            i,
            part.get("item", ""),
            part.get("part_number", ""),
            part.get("description", ""),
            part.get("quantity", 0),
            part.get("remarks", "")
        ])

    print()
    print("=" * 100)
    print("                         BOM FOR HUMAN REVIEW")
    print("=" * 100)

    print(f"\nAssembly : {bom.get('assembly', '')}")
    print(f"Catalogue: {bom.get('catalogue', '')}")
    print(f"Parts    : {len(rows)}\n")

    print(
        tabulate(
            rows,
            headers=[
                "Row",
                "Item",
                "Part Number",
                "Description",
                "Quantity",
                "Remarks"
            ],
            tablefmt="grid"
        )
    )

    print()


def edit_part(bom):
    """Edit an existing BOM row."""

    parts = bom["parts"]

    if not parts:
        print("\nNo parts available to edit.")
        return

    try:
        row = int(input("Enter row number to edit: "))

        if row < 1 or row > len(parts):
            print("Invalid row number.")
            return

        part = parts[row - 1]

        print("\nCurrent values:")
        print(f"1. Item        : {part['item']}")
        print(f"2. Part Number : {part['part_number']}")
        print(f"3. Description : {part['description']}")
        print(f"4. Quantity    : {part['quantity']}")
        print(f"5. Remarks     : {part['remarks']}")

        print("\nEnter the field you want to edit.")
        print("1. Item")
        print("2. Part Number")
        print("3. Description")
        print("4. Quantity")
        print("5. Remarks")

        field = input("Choice: ").strip()

        if field == "1":
            part["item"] = input("New item: ").strip()

        elif field == "2":
            part["part_number"] = input("New part number: ").strip()

        elif field == "3":
            part["description"] = input("New description: ").strip()

        elif field == "4":
            try:
                quantity = int(input("New quantity: "))

                if quantity < 0:
                    print("Quantity cannot be negative.")
                    return

                part["quantity"] = quantity

            except ValueError:
                print("Quantity must be an integer.")
                return

        elif field == "5":
            part["remarks"] = input("New remarks: ").strip()

        else:
            print("Invalid choice.")
            return

        print("\n✓ Part updated successfully.")

    except ValueError:
        print("Invalid input.")


def add_part(bom):
    """Add a completely new part to the BOM."""

    print("\n" + "-" * 50)
    print("ADD NEW PART")
    print("-" * 50)

    item = input("Item number: ").strip()
    part_number = input("Part number: ").strip()
    description = input("Description: ").strip()

    try:
        quantity = int(input("Quantity: "))

        if quantity < 0:
            print("Quantity cannot be negative.")
            return

    except ValueError:
        print("Quantity must be an integer.")
        return

    remarks = input("Remarks: ").strip()

    new_part = {
        "item": item,
        "part_number": part_number,
        "description": description,
        "quantity": quantity,
        "remarks": remarks
    }

    bom["parts"].append(new_part)

    # Update total number of part rows
    bom["total_parts"] = len(bom["parts"])

    print("\n✓ New part added successfully.")


def delete_part(bom):
    """Delete a part from the BOM."""

    parts = bom["parts"]

    if not parts:
        print("\nNo parts available to delete.")
        return

    try:
        row = int(input("Enter row number to delete: "))

        if row < 1 or row > len(parts):
            print("Invalid row number.")
            return

        removed = parts.pop(row - 1)

        bom["total_parts"] = len(parts)

        print(
            f"\n✓ Removed part: "
            f"{removed.get('part_number', '')}"
        )

    except ValueError:
        print("Invalid row number.")


def validate_reviewed_bom(bom):
    """
    Validate the BOM after human editing.

    Returns:
        (True, "")
        or
        (False, error_message)
    """

    try:
        validated = BOM.model_validate(bom)

        # Additional human-review checks
        for index, part in enumerate(validated.parts, start=1):

            if not part.part_number.strip():
                return False, f"Row {index}: Part number cannot be empty."

            if not part.description.strip():
                return False, f"Row {index}: Description cannot be empty."

            if part.quantity < 0:
                return False, f"Row {index}: Quantity cannot be negative."

        return True, ""

    except Exception as e:
        return False, str(e)


def human_review(bom):
    """
    Human-in-the-loop review of the Document Agent BOM.

    The human can:
    - Approve the BOM
    - Edit any field
    - Add a new part
    - Delete a part
    - Reject the BOM

    Returns:
        {
            "status": "approved" / "rejected",
            "bom": reviewed_bom,
            "original_bom": original_bom
        }
    """

    # Keep original AI output untouched
    original_bom = deepcopy(bom)

    # Work on a separate copy
    reviewed_bom = deepcopy(bom)

    while True:

        display_bom(reviewed_bom)

        print("=" * 100)
        print("HUMAN REVIEW OPTIONS")
        print("=" * 100)

        print("1. Approve BOM")
        print("2. Edit Part")
        print("3. Add Part")
        print("4. Delete Part")
        print("5. Reject BOM")

        choice = input("\nEnter choice: ").strip()

        # -----------------------------------------
        # APPROVE
        # -----------------------------------------

        if choice == "1":

            valid, error = validate_reviewed_bom(reviewed_bom)

            if not valid:
                print("\n✗ BOM validation failed:")
                print(error)
                print("\nPlease correct the BOM before approval.")
                continue

            print("\n✓ BOM approved by human reviewer.")

            return {
                "status": "approved",
                "bom": reviewed_bom,
                "original_bom": original_bom
            }

        # -----------------------------------------
        # EDIT
        # -----------------------------------------

        elif choice == "2":

            edit_part(reviewed_bom)

        # -----------------------------------------
        # ADD
        # -----------------------------------------

        elif choice == "3":

            add_part(reviewed_bom)

        # -----------------------------------------
        # DELETE
        # -----------------------------------------

        elif choice == "4":

            delete_part(reviewed_bom)

        # -----------------------------------------
        # REJECT
        # -----------------------------------------

        elif choice == "5":

            print("\n✗ BOM rejected by human reviewer.")

            return {
                "status": "rejected",
                "bom": reviewed_bom,
                "original_bom": original_bom
            }

        else:

            print("\nInvalid choice. Please select 1-5.")