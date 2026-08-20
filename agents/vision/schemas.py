from typing import List

from pydantic import BaseModel, Field


class VisionExtraction(BaseModel):
    assembly_name: str = Field(min_length=1)
    callouts: List[int] = Field(min_length=1)


class VisionPart(BaseModel):
    item: str
    part_number: str
    description: str
    quantity: int = Field(ge=1)
    remarks: str = ""


class VisionBOM(BaseModel):
    assembly: str = Field(min_length=1)
    catalogue: str = Field(min_length=1)
    total_parts: int = Field(ge=1)
    parts: List[VisionPart] = Field(min_length=1)