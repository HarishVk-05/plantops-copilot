import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Add it to the .env file."
    )
llm = ChatGroq(
    model = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile"
    ),
    api_key = groq_api_key,
    temperature=0,
    timeout = 60,
    max_retries=2
)

def invoke_llm(runnable, payload, stage_name: str):
    try:
        retryable = runnable.with_retry(
            stop_after_attempt = 2,
            wait_exponential_jitter = True
        )
        return retryable.invoke(payload)
    
    except Exception as exc:
        raise RuntimeError(
            f"{stage_name} failed after retries. "
            "Check the Groq API key, internet connection, "
            "rate limits, and model availability."
        ) from exc
