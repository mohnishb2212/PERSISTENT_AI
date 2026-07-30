import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "inventory"
    / "inventory.db"
)


def connect_database():
    return sqlite3.connect(DB_PATH)


def get_part(connection, part_number):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            part_number,
            description,
            available_qty,
            min_threshold,
            rack_location,
            supplier
        FROM inventory
        WHERE part_number = ?
        """,
        (part_number,)
    )

    row = cursor.fetchone()

    if row is None:
        return None

    return {
        "part_number": row[0],
        "description": row[1],
        "available_qty": row[2],
        "min_threshold": row[3],
        "rack_location": row[4],
        "supplier": row[5],
    }


def close_database(connection):
    connection.close()