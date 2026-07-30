from typing import Any, TypedDict
import sqlite3
from typing import TypedDict

class InventoryState(TypedDict):
    bom: dict
    connection: Any
    inventory: dict
    output_file: str
    status: str
    error: str