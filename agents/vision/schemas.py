from typing import List
from pydantic import BaseModel, Field


class VisionComponent(BaseModel):

    callout: int = Field(
        description="Callout number visible in the exploded-view drawing."
    )

    predicted_category: str = Field(
        description="Predicted category of the component."
    )

    visual_description: str = Field(
        description="Short visual description of the component."
    )

    quantity: int = Field(
        ge=1,
        description="Estimated number of physical instances of this component."
    )

    quantity_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the estimated physical quantity."
    )

    quantity_reason: str = Field(
        description="Brief explanation for the estimated quantity."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the component identification."
    )


class VisionOutputSchema(BaseModel):

    assembly_name: str = Field(
        description="Detected assembly name."
    )

    components: List[VisionComponent]