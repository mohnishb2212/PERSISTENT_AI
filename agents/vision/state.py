from typing import Optional, Any

from typing_extensions import TypedDict

from .schemas import VisionOutputSchema


class VisionState(TypedDict):

    # -------------------------------------------------
    # Input
    # -------------------------------------------------

    image_path: str

    # -------------------------------------------------
    # Image
    # -------------------------------------------------

    image_base64: Optional[str]

    # -------------------------------------------------
    # Parallel LLM outputs
    # -------------------------------------------------

    component_analysis: Optional[Any]

    quantity_analysis: Optional[Any]

    # -------------------------------------------------
    # Final integrated output
    # -------------------------------------------------

    vision_result: Optional[VisionOutputSchema]

    # -------------------------------------------------
    # Output file
    # -------------------------------------------------

    output_file: Optional[str]