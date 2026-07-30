import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent

excel_file = BASE_DIR / "inventory.xlsx"
database_file = BASE_DIR / "inventory.db"

# Read Excel
df = pd.read_excel(excel_file)

# Connect to SQLite
conn = sqlite3.connect(database_file)
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (

    part_number TEXT PRIMARY KEY,
    description TEXT,
    available_qty INTEGER,
    min_threshold INTEGER,
    rack_location TEXT,
    supplier TEXT

)
""")

# Insert rows
for _, row in df.iterrows():

    cursor.execute("""
    INSERT OR REPLACE INTO inventory
    VALUES (?, ?, ?, ?, ?, ?)
    """, (

        row["Part Number"],
        row["Description"],
        row["Available Qty"],
        row["Min Threshold"],
        row["Rack Location"],
        row["Supplier"]

    ))

conn.commit()
conn.close()

print("Inventory database created successfully!")