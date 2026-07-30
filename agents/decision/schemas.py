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


class InventorySchema(BaseModel):
    assembly: str
    catalogue: str
    total_parts: int

    parts: List[InventoryPart]


class DecisionPart(BaseModel):
    item: str
    part_number: str
    description: str

    required_quantity: int
    available_quantity: int

    remaining_quantity: int

    minimum_threshold: int

    status: str

    procurement_required: int

    rack_location: str
    supplier: str


class DecisionSummary(BaseModel):
    total_parts: int

    available: int
    low_stock: int
    shortage: int
    out_of_stock: int

    total_procurement_required: int


class DecisionSchema(BaseModel):
    assembly: str
    catalogue: str

    assembly_status: str

    summary: DecisionSummary

    parts: List[DecisionPart]