import os
from datetime import datetime
from typing import Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

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


# Define graph state
class State(TypedDict):
    messages: Annotated[list, add_messages]


# Define graph nodes
def chatbot(state: State) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


# Build the graph
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    """Main agent entrypoint with LangGraph support.

    Args:
        payload: JSON body with "message"
        context: Request metadata (session_id, user_id, request_headers)
    """
    message = payload.get("message", "Hello")

    result = graph.invoke({"messages": [("user", message)]})
    ai_message = result["messages"][-1]

    return {
        "status": "success",
        "response": ai_message.content,
        "timestamp": datetime.now().isoformat(),
    }


@app.ping
def health_check() -> PingStatus:
    """Custom health check for GET /health endpoint."""
    return PingStatus.HEALTHY


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
