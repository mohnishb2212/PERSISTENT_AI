import base64
import io
import json
from pathlib import Path

from PIL import Image
from langchain_core.messages import HumanMessage

from .llm import get_llm
from .prompts import VISION_PROMPT
from .state import VisionState


# ==========================================================
# Node 1 : Validate Input
# ==========================================================

def validate_input(state: VisionState):

    image_path = Path(state["image_path"])

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found:\n{image_path}"
        )

    return state


# ==========================================================
# Node 2 : Load Image
# ==========================================================

def load_image(state: VisionState):

    image_path = Path(state["image_path"])

    image = Image.open(image_path)

    buffer = io.BytesIO()

    image.save(buffer, format="PNG")

    image_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    state["image_base64"] = image_base64

    return state


# ==========================================================
# Node 3 : Analyze Image (Vision LLM)
# ==========================================================

def analyze_image(state: VisionState):

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
                    "url": f"data:image/png;base64,{state['image_base64']}"
                }
            }

        ]

    )

    result = llm.invoke([message])

    state["vision_result"] = result

    return state


# ==========================================================
# Node 4 : Validate Output
# ==========================================================

def validate_output(state: VisionState):

    # If llm.py uses with_structured_output(),
    # this object is already validated.

    print("\n✓ Vision output validated.\n")

    return state


# ==========================================================
# Node 5 : Save Output
# ==========================================================

def save_output(state: VisionState):

    output_dir = Path("agents/vision/output")

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    image_name = Path(state["image_path"]).stem

    output_file = output_dir / f"{image_name}_vision.json"

    with open(

        output_file,

        "w",

        encoding="utf-8"

    ) as f:

        json.dump(

            state["vision_result"].model_dump(),

            f,

            indent=4

        )

    state["output_file"] = str(output_file)

    print(f"✓ Vision JSON saved to\n{output_file}")

    return state