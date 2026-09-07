"""LangChain + Ollama setup with tool binding."""
from langchain_ollama import ChatOllama
from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from .tools import get_route_stats, query_shipments, predict_delay

# Initialize Ollama chat model
llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=LLM_TEMPERATURE,
    num_predict=LLM_MAX_TOKENS,
)

# Bind tools to model
llm_with_tools = llm.bind_tools([get_route_stats, query_shipments, predict_delay])
