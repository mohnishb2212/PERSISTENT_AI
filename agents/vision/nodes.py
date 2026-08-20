import base64
import io
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image
from langchain_core.messages import HumanMessage

from .llm import get_llm
from .prompts import VISION_PROMPT
from .schemas import VisionBOM, VisionExtraction
from .state import VisionState


# The shared database created for the redesigned Inventory Agent.
DB_MODULE_PATH = Path(__file__).resolve().parents[2] / "inventory" / "db.py"

def normalize_catalogue_name(value: str) -> str:
    return str(value).strip().upper().replace(" ", "_")


def _load_database_module():
    """Load the shared inventory DB helpers without changing the project package layout."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "persistent_shared_inventory_db",
        DB_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load database module: {DB_MODULE_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_json_response(response: Any) -> dict:
    """Parse the model's JSON response robustly."""
    content = getattr(response, "content", response)

    if isinstance(content, dict):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        content = "".join(parts)

    text = str(content).strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError(f"LLM did not return a JSON object. Response: {text[:500]}")

    return json.loads(text[start : end + 1])


def validate_input(state: VisionState):
    image_path = Path(state["image_path"])

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Vision Agent input must be a PNG, JPG, JPEG, or WEBP image.")

    catalogue_name = normalize_catalogue_name(
    state["catalogue_name"]
)
    if not catalogue_name:
        raise ValueError("Catalogue name cannot be empty.")

    return {
        "image_path": str(image_path),
        "catalogue_name": catalogue_name,
        "status": "validated",
        "error": "",
    }


def load_image(state: VisionState):
    image = Image.open(state["image_path"]).convert("RGB")

    # PNG conversion makes the multimodal payload consistent across inputs.
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    return {
        "image_base64": base64.b64encode(buffer.getvalue()).decode("utf-8"),
        "status": "image_loaded",
    }


def extract_assembly_and_callouts(state: VisionState):
    """Single multimodal LLM call: assembly name + visible callout numbers only."""
    print("\n[LLM] Identifying assembly name and callout numbers...")

    llm = get_llm()

    message = HumanMessage(
        content=[
            {"type": "text", "text": VISION_PROMPT},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{state['image_base64']}"
                },
            },
        ]
    )

    response = llm.invoke([message])
    raw = parse_json_response(response)
    extraction = VisionExtraction.model_validate(raw)

    # Deduplicate while preserving the model's order.
    unique_callouts = list(dict.fromkeys(extraction.callouts))
    extraction = VisionExtraction(
        assembly_name=extraction.assembly_name.strip(),
        callouts=unique_callouts,
    )

    print(f"[LLM] Assembly detected: {extraction.assembly_name}")
    print(f"[LLM] Callouts detected : {extraction.callouts}")

    return {
        "vision_extraction": extraction,
        "status": "vision_extracted",
    }


def _normalize_name(value: str) -> str:
    value = value.upper().strip()
    value = re.sub(r"GROUP\s+[A-Z0-9-]+\s*[-:]\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^A-Z0-9 ]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _resolve_assembly(db, connection, catalogue_name: str, llm_name: str) -> str:
    """Resolve minor LLM naming differences against known assembly names."""
    requested = _normalize_name(llm_name)

    rows = connection.execute(
        """
        SELECT DISTINCT assembly_name
        FROM assembly_parts
        WHERE catalogue_name = ?
        ORDER BY assembly_name
        """,
        (catalogue_name,),
    ).fetchall()

    known = [row[0] for row in rows]
    if not known:
        raise ValueError(
            f"No Vision mappings exist for catalogue '{catalogue_name}'."
        )

    for name in known:
        normalized = _normalize_name(name)
        if requested == normalized:
            return name

    # Useful for headers such as 'GROUP M11B23 - EXHAUST MANIFOLD'.
    for name in known:
        normalized = _normalize_name(name)
        if normalized and normalized in requested:
            return name

    raise ValueError(
        f"Could not map detected assembly '{llm_name}' to a known assembly "
        f"in catalogue '{catalogue_name}'. Available assemblies: {known}"
    )


def map_callouts_to_bom(state: VisionState):
    """Resolve callouts deterministically through the central SQLite database."""
    db = _load_database_module()
    connection = db.connect_database()

    try:
        extraction: VisionExtraction = state["vision_extraction"]
        catalogue_name = state["catalogue_name"]

        resolved_assembly = _resolve_assembly(
            db,
            connection,
            catalogue_name,
            extraction.assembly_name,
        )

        mapping_rows = db.get_assembly_parts(
            connection,
            catalogue_name,
            resolved_assembly,
        )

        by_callout = {
            int(row["callout_number"]): row
            for row in mapping_rows
        }

        missing = [
            callout
            for callout in extraction.callouts
            if callout not in by_callout
        ]

        if missing:
            raise ValueError(
                f"The database has no mapping for callout(s) {missing} "
                f"in {catalogue_name} / {resolved_assembly}."
            )

        parts = []
        for callout in extraction.callouts:
            mapping = by_callout[callout]
            part_number = mapping["part_number"]
            inventory_row = db.get_part(connection, part_number)

            description = ""
            if inventory_row:
                description = inventory_row.get("description") or ""

            parts.append(
                {
                    "item": str(callout),
                    "part_number": str(part_number),
                    "description": description,
                    "quantity": int(mapping["required_quantity"]),
                    "remarks": "",
                }
            )

        bom = VisionBOM(
            assembly=resolved_assembly,
            catalogue=catalogue_name,
            total_parts=len(parts),
            parts=parts,
        )

        print(f"[DB] Assembly resolved: {resolved_assembly}")
        print(f"[DB] Callouts mapped : {len(parts)}")

        return {
            "resolved_assembly": resolved_assembly,
            "bom": bom,
            "status": "bom_mapped",
        }

    finally:
        db.close_database(connection)


def validate_output(state: VisionState):
    VisionBOM.model_validate(state["bom"])
    print("\n✓ Vision BOM validated successfully.\n")
    return {"status": "validated"}


def save_output(state: VisionState):
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "agents" / "vision" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    image_name = Path(state["image_path"]).stem
    output_file = output_dir / f"{image_name}_vision.json"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(state["bom"].model_dump(), f, indent=4, ensure_ascii=False)

    print(f"✓ Vision BOM saved to: {output_file}")

    return {
        "output_file": str(output_file),
        "status": "completed",
    }