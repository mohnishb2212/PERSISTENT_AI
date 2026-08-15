import base64
import io
import json
from pathlib import Path

from PIL import Image
from langchain_core.messages import HumanMessage

from .llm import get_llm
from .prompts import (
    COMPONENT_PROMPT,
    QUANTITY_PROMPT,
    INTEGRATION_PROMPT,
)
from .state import VisionState
from .schemas import VisionOutputSchema


# ==========================================================
# Helper: Parse JSON
# ==========================================================

def parse_json_response(response):

    # LangChain AIMessage
    if hasattr(response, "content"):
        content = response.content
    else:
        content = response

    # Already a dictionary
    if isinstance(content, dict):
        return content

    # Sometimes content can be a list
    if isinstance(content, list):

        text_parts = []

        for item in content:

            if isinstance(item, dict) and "text" in item:
                text_parts.append(item["text"])

            else:
                text_parts.append(str(item))

        content = "".join(text_parts)

    content = str(content).strip()

    # Remove markdown code fences
    if content.startswith("```"):

        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

    # Find JSON object if model adds extra text
    start = content.find("{")
    end = content.rfind("}")

    if start != -1 and end != -1:

        content = content[start:end + 1]

    return json.loads(content)


# ==========================================================
# Node 1 : Validate Input
# ==========================================================

def validate_input(state: VisionState):

    image_path = Path(state["image_path"])

    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found:\n{image_path}"
        )

    return {
        "image_path": str(image_path)
    }


# ==========================================================
# Node 2 : Load Image
# ==========================================================

def load_image(state: VisionState):

    image_path = Path(state["image_path"])

    image = Image.open(image_path)

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG"
    )

    image_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    return {
        "image_base64": image_base64
    }


# ==========================================================
# Helper : Send image + prompt to LLM
# ==========================================================

def call_vision_llm(prompt, image_base64):

    llm = get_llm()

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": (
                        f"data:image/png;base64,"
                        f"{image_base64}"
                    )
                }
            }
        ]
    )

    return llm.invoke([message])


# ==========================================================
# Node 3A : Component + Callout Analysis
# ==========================================================

def analyze_components(state: VisionState):

    print(
        "\n[LLM 1] "
        "Identifying components and callouts..."
    )

    response = call_vision_llm(
        COMPONENT_PROMPT,
        state["image_base64"]
    )

    result = parse_json_response(response)

    print(
        "[LLM 1] Component analysis completed."
    )

    # IMPORTANT:
    # Return ONLY the field produced by this node.
    #
    # Do NOT return the complete state here because
    # this node runs in parallel with analyze_quantities().

    return {
        "component_analysis": result
    }


# ==========================================================
# Node 3B : Quantity + Symmetry Analysis
# ==========================================================

def analyze_quantities(state: VisionState):

    print(
        "\n[LLM 2] "
        "Analyzing quantity and symmetry..."
    )

    response = call_vision_llm(
        QUANTITY_PROMPT,
        state["image_base64"]
    )

    result = parse_json_response(response)

    print(
        "[LLM 2] Quantity analysis completed."
    )

    # IMPORTANT:
    # Return ONLY the field produced by this node.
    #
    # This prevents a concurrent update conflict
    # with analyze_components().

    return {
        "quantity_analysis": result
    }


# ==========================================================
# Node 4 : Final Integration
# ==========================================================

def integrate_results(state: VisionState):

    print(
        "\n[LLM 3] Integrating analyses..."
    )

    component_analysis = json.dumps(
        state["component_analysis"],
        indent=2
    )

    quantity_analysis = json.dumps(
        state["quantity_analysis"],
        indent=2
    )

    prompt = INTEGRATION_PROMPT.format(
        component_analysis=component_analysis,
        quantity_analysis=quantity_analysis
    )

    response = call_vision_llm(
        prompt,
        state["image_base64"]
    )

    result = parse_json_response(response)

    # ------------------------------------------------------
    # Validate final output using Pydantic
    # ------------------------------------------------------

    validated = VisionOutputSchema.model_validate(
        result
    )

    print(
        "[LLM 3] Final integration completed."
    )

    # Return ONLY the field generated by this node.

    return {
        "vision_result": validated
    }


# ==========================================================
# Node 5 : Validate Output
# ==========================================================

def validate_output(state: VisionState):

    VisionOutputSchema.model_validate(
        state["vision_result"]
    )

    print(
        "\n✓ Final Vision output validated.\n"
    )

    return {}


# ==========================================================
# Node 6 : Save Output
# ==========================================================

def save_output(state: VisionState):

    output_dir = Path(
        "agents/vision/output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    image_name = Path(
        state["image_path"]
    ).stem

    output_file = (
        output_dir /
        f"{image_name}_vision.json"
    )

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

    print(
        f"\n✓ Vision JSON saved to\n"
        f"{output_file}"
    )

    return {
        "output_file": str(output_file)
    }