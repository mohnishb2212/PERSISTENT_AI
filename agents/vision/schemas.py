from typing import List

from pydantic import BaseModel, Field


class VisionComponent(BaseModel):

    callout: int = Field(
        description="Callout number visible in the exploded-view drawing."
    )

    predicted_category: str = Field(
        description="Predicted category of the detected component."
    )

    visual_description: str = Field(
        description="Visual description of the component."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1."
    )


class VisionOutputSchema(BaseModel):

    assembly_name: str = Field(
        description="Detected assembly name."
    )

    components: List[VisionComponent]