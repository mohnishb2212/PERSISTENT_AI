import base64
import io
import json
from pathlib import Path

from PIL import Image
from pydantic import ValidationError
from langchain_core.messages import HumanMessage

from .llm import get_llm
from .prompts import VISION_PROMPT
from .schemas import VisionOutputSchema


# ==========================================================
# Configuration
# ==========================================================

IMAGE_PATH = Path(
    "agents/vision/input/medium/mahindra_scorpio_CAMSHAFT.png"
)

OUTPUT_DIR = Path("agents/vision/output")


# ==========================================================
# Validate Input
# ==========================================================

def validate_input():

    if not IMAGE_PATH.exists():

        raise FileNotFoundError(
            f"Image not found:\n{IMAGE_PATH}"
        )


# ==========================================================
# Load Image
# ==========================================================

def load_image():

    return Image.open(IMAGE_PATH)


# ==========================================================
# Convert Image → Base64
# ==========================================================

def image_to_base64(image):

    buffer = io.BytesIO()

    image.save(buffer, format="PNG")

    return base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")


# ==========================================================
# Invoke Vision LLM
# ==========================================================

def invoke_llm(image_base64):

    llm = get_llm()

    message = HumanMessage(

        content=[

            {
                "type": "text",
                "text": VISION_PROMPT
            },

            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                }
            }

        ]

    )

    return llm.invoke([message])


# ==========================================================
# Validate Output
# ==========================================================

def validate_output(result):

    try:

        VisionOutputSchema.model_validate(result)

        print("✓ Schema validation successful.\n")

    except ValidationError as e:

        print(e)

        raise


# ==========================================================
# Pretty Print
# ==========================================================

def print_summary(result):

    print("=" * 70)

    print("VISION AGENT OUTPUT")

    print("=" * 70)

    print()

    print(f"Assembly : {result.assembly_name}")

    print()

    print("-" * 70)

    print()

    for component in result.components:

        print(f"Callout             : {component.callout}")

        print(f"Predicted Category  : {component.predicted_category}")

        print(f"Confidence          : {component.confidence:.2f}")

        print(f"Description         : {component.visual_description}")

        print()

        print("-" * 70)

        print()


# ==========================================================
# Save JSON
# ==========================================================

def save_json(result):

    OUTPUT_DIR.mkdir(

        parents=True,

        exist_ok=True

    )

    filename = IMAGE_PATH.stem + "_vision.json"

    output_file = OUTPUT_DIR / filename

    with open(

        output_file,

        "w",

        encoding="utf-8"

    ) as f:

        json.dump(

            result.model_dump(),

            f,

            indent=4

        )

    print(f"✓ JSON saved to\n{output_file}")


# ==========================================================
# Main
# ==========================================================

def main():

    print()

    print("=" * 70)

    print("VISION AGENT TEST")

    print("=" * 70)

    print()

    validate_input()

    image = load_image()

    image_base64 = image_to_base64(image)

    result = invoke_llm(image_base64)

    validate_output(result)

    print_summary(result)

    save_json(result)

    print()

    print("✓ Vision pipeline completed successfully.")


if __name__ == "__main__":

    main()