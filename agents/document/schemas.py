from typing import List
from pydantic import BaseModel, Field

class BOMItem(BaseModel):
    """
    Represents one row of a Bill of Materials.
    """
    item: str = Field(
        ...,
        description="Item number shown in catalogue"
    )
    part_number: str = Field(
        ...,
        description="Manufacturer part number"
    )
    description: str = Field(
        ...,
        description="Part description"
    )
    quantity: int = Field(
        default=0,
        description="Quantity required"
    )
    remarks: str = Field(
        default="",
        description="Additional notes if available"
    )

class BOM(BaseModel):
    """
    Final structured BOM returned by the Document Agent.
    """
    assembly: str
    catalogue: str
    total_parts: int
    parts: List[BOMItem]