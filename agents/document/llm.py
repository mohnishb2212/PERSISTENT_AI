import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
load_dotenv()
def get_llm():
    return ChatOpenAI(
        model="openai/gpt-oss-20b:free",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        temperature=0
    )