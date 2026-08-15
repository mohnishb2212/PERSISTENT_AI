import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA


# -------------------------------------------------
# Load .env from project root
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


# -------------------------------------------------
# Get NVIDIA Vision LLM
# -------------------------------------------------

def get_llm():

    api_key = os.getenv("NVDIA_API_KEY_VISION_30B")

    if not api_key:
        raise ValueError(
            "NVDIA_API_KEY_VISION_30B not found in PERSISTENT_AI/.env"
        )

    return ChatNVIDIA(
        model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        api_key=api_key,

        # NVIDIA's recommended settings
        temperature=0.6,
        top_p=0.95,

        # Maximum output tokens
        max_completion_tokens=65536,
        timeout=180,
    )