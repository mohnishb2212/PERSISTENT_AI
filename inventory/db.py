import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "central_inventory.db"


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
        (str(part_number).strip(),),
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


def get_assembly_part(connection, catalogue_name, assembly_name, callout_number):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT
            catalogue_name,
            assembly_name,
            callout_number,
            part_number,
            required_quantity
        FROM assembly_parts
        WHERE catalogue_name = ?
          AND assembly_name = ?
          AND callout_number = ?
        """,
        (
            str(catalogue_name).strip(),
            str(assembly_name).strip(),
            int(callout_number),
        ),
    )
    row = cursor.fetchone()
    if row is None:
        return None

    return {
        "catalogue_name": row[0],
        "assembly_name": row[1],
        "callout_number": row[2],
        "part_number": row[3],
        "required_quantity": row[4],
    }


def get_assembly_parts(connection, catalogue_name, assembly_name):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT
            callout_number,
            part_number,
            required_quantity
        FROM assembly_parts
        WHERE catalogue_name = ?
          AND assembly_name = ?
        ORDER BY callout_number
        """,
        (
            str(catalogue_name).strip(),
            str(assembly_name).strip(),
        ),
    )

    return [
        {
            "callout_number": row[0],
            "part_number": row[1],
            "required_quantity": row[2],
        }
        for row in cursor.fetchall()
    ]


def close_database(connection):
    connection.close()
