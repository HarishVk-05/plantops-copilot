from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model = "llama-3.3-70b-versatile",
    api_key=groq_api_key,
    temperature=0
)
