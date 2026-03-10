import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool

from greennode_agentbase import (
    GreenNodeAgentBaseApp,
    RequestContext,
    PingStatus,
)

load_dotenv()

app = GreenNodeAgentBaseApp()

# --- LLM Configuration ---
# Uses GreenNode AI Platform (OpenAI-compatible)
# Create an API key with: /aip api-keys create
# Browse available models with: /aip models list
# Production: use /agentbase-auth to store API key, inject via @requires_api_key
llm = ChatOpenAI(
    model=os.environ.get("LLM_MODEL", ""),
    base_url=os.environ.get("AIP_BASE_URL", "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"),
    api_key=os.environ.get("AIP_API_KEY", ""),
)


# --- Define Tools ---
@tool
def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --- Create Agent ---
# create_agent builds a compiled LangGraph StateGraph with tool-calling support.
# Parameters:
#   model: LLM instance or model identifier string
#   tools: list of @tool functions, callables, or dicts
#   system_prompt: optional system message for the LLM
# See: https://python.langchain.com/api_reference/langchain/agents/create_agent
agent = create_agent(llm, tools=[get_current_time])


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    message = payload.get("message", "Hello")

    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]}
    )
    ai_message = result["messages"][-1]
    return {
        "status": "success",
        "response": ai_message.content,
        "timestamp": datetime.now().isoformat(),
    }


@app.ping
def health_check() -> PingStatus:
    return PingStatus.HEALTHY


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
