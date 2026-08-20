from typing import Any, Optional
from typing_extensions import TypedDict

from .schemas import VisionBOM, VisionExtraction


class VisionState(TypedDict):
    # Input
    image_path: str
    catalogue_name: str

    # Image
    image_base64: Optional[str]

    # LLM output
    vision_extraction: Optional[VisionExtraction]

    # Database resolution
    resolved_assembly: Optional[str]

    # Unified BOM
    bom: Optional[VisionBOM]

    # Output / status
    output_file: Optional[str]
    status: str
    error: str