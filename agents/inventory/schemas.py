from pydantic import BaseModel
from typing import List


class InventoryPart(BaseModel):
    item: str
    part_number: str
    description: str

    required_quantity: int

    available_quantity: int
    minimum_threshold: int

    rack_location: str
    supplier: str

    remarks: str


class Inventory(BaseModel):
    assembly: str
    catalogue: str
    total_parts: int

    parts: List[InventoryPart]