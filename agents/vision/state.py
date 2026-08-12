from typing import Optional

from typing_extensions import TypedDict

from .schemas import VisionOutputSchema


class VisionState(TypedDict):
    """
    State shared across the Vision Agent graph.
    """

    # Input image path
    image_path: str

    # Base64 encoded image
    image_base64: Optional[str]

    # Structured Vision Agent output
    vision_result: Optional[VisionOutputSchema]

    # Output JSON path
    output_file: Optional[str]