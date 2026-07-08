from agents.document.llm import get_llm

llm = get_llm()

response = llm.invoke("What is LangGraph? Explain in short about 40 words")

print(response.content)