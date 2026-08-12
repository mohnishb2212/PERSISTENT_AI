import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from .schemas import VisionOutputSchema

load_dotenv()


def get_llm():

    llm = ChatOpenAI(

        model="meta/llama-3.2-90b-vision-instruct",

        base_url="https://integrate.api.nvidia.com/v1",

        api_key=os.getenv("NVIDIA_API_KEY_VISION"),

        temperature=0,

    )

    return llm.with_structured_output(
        VisionOutputSchema
    )