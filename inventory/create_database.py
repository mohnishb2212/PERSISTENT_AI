from pathlib import Path
import json
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
EXCEL_FILE = BASE_DIR / "inventory.xlsx"
SEED_FILE = BASE_DIR / "assembly_parts_seed.json"
DATABASE_FILE = BASE_DIR / "central_inventory.db"


def create_database():
    if DATABASE_FILE.exists():
        DATABASE_FILE.unlink()

    inventory_df = pd.read_excel(EXCEL_FILE)
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        assembly_parts = json.load(f)

    required_columns = {
        "Part Number",
        "Description",
        "Available Qty",
        "Min Threshold",
        "Rack Location",
        "Supplier",
    }
    missing = required_columns - set(inventory_df.columns)
    if missing:
        raise ValueError(f"Inventory Excel is missing columns: {sorted(missing)}")

    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE inventory (
            part_number TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            available_qty INTEGER NOT NULL DEFAULT 0,
            min_threshold INTEGER NOT NULL DEFAULT 0,
            rack_location TEXT,
            supplier TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE assembly_parts (
            catalogue_name TEXT NOT NULL,
            assembly_name TEXT NOT NULL,
            callout_number INTEGER NOT NULL,
            part_number TEXT NOT NULL,
            required_quantity INTEGER NOT NULL,
            PRIMARY KEY (catalogue_name, assembly_name, callout_number),
            FOREIGN KEY (part_number) REFERENCES inventory(part_number)
        )
    """)

    # Load the complete central inventory table.
    for _, row in inventory_df.iterrows():
        cursor.execute(
            """
            INSERT INTO inventory (
                part_number,
                description,
                available_qty,
                min_threshold,
                rack_location,
                supplier
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(row["Part Number"]).strip(),
                str(row["Description"]).strip(),
                int(row["Available Qty"]),
                int(row["Min Threshold"]),
                str(row["Rack Location"]).strip(),
                str(row["Supplier"]).strip(),
            ),
        )

    # Load Vision Agent assembly/callout mappings.
    for row in assembly_parts:
        cursor.execute(
            """
            INSERT INTO assembly_parts (
                catalogue_name,
                assembly_name,
                callout_number,
                part_number,
                required_quantity
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                row["catalogue_name"],
                row["assembly_name"],
                int(row["callout_number"]),
                row["part_number"],
                int(row["required_quantity"]),
            ),
        )

    connection.commit()

    inventory_count = cursor.execute(
        "SELECT COUNT(*) FROM inventory"
    ).fetchone()[0]

    mapping_count = cursor.execute(
        "SELECT COUNT(*) FROM assembly_parts"
    ).fetchone()[0]

    catalogue_count = cursor.execute(
        "SELECT COUNT(DISTINCT catalogue_name) FROM assembly_parts"
    ).fetchone()[0]

    connection.close()

    print("Central inventory database created successfully.")
    print(f"Inventory rows       : {inventory_count}")
    print(f"Assembly-part rows   : {mapping_count}")
    print(f"Catalogues covered   : {catalogue_count}")
    print(f"Database             : {DATABASE_FILE}")


if __name__ == "__main__":
    create_database()
