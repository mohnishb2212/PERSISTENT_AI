import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()


def get_llm():

    api_key = os.getenv("NVDIA_API_KEY_GLM")

    if not api_key:
        raise ValueError(
            "NVDIA_API_KEY_GLM not found in PERSISTENT_AI/.env"
        )

    return ChatOpenAI(
        model="openai/gpt-oss-20b",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        temperature=0,
    )