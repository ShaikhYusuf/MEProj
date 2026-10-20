# llm.py
import instructor
from functools import lru_cache
from openai import AsyncOpenAI

OLLAMA_BASE = "http://localhost:11434/v1"
MODEL_DESIGN_FULL = "qwen2.5:7b-instruct"
MODEL_CODE_FULL   = "qwen2.5-coder:7b-instruct"

MODEL_DESIGN = "qwen2.5:7b-instruct-q4_K_M"
MODEL_CODE   = "qwen2.5-coder:7b-instruct"

@lru_cache
def get_instructor() -> instructor.AsyncInstructor:
    client = AsyncOpenAI(base_url=OLLAMA_BASE, api_key="ollama", timeout=600.0)
    return instructor.from_openai(client, mode=instructor.Mode.JSON_SCHEMA)