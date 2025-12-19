"""
LangGraph multi-agent orchestration with parallel execution.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END

from .state import MultiAgentState, create_initial_state
from .rag_agent import rag_agent
from .temporal_agent import temporal_agent
from .supervisor_agent import supervisor_agent
from ..config import settings


def create_multi_agent_graph():
    """
    Create multi-agent graph with parallel execution.

    Returns:
        Compiled LangGraph workflow
    """
    # Create state graph
    workflow = StateGraph(MultiAgentState)

    # Add a dispatcher node to fan out to all agents
    def dispatcher(state: MultiAgentState) -> MultiAgentState:
        """Pass-through dispatcher that initiates parallel execution."""
        return state

    # Add nodes
    workflow.add_node("dispatcher", dispatcher)
    workflow.add_node("rag", rag_agent.execute)
    workflow.add_node("temporal", temporal_agent.execute)
    workflow.add_node("supervisor", supervisor_agent.execute)

    # Set single entry point (dispatcher)
    workflow.set_entry_point("dispatcher")

    # Fan out from dispatcher to all agents (PARALLEL EXECUTION)
    # All agents run concurrently from the dispatcher
    if settings.ENABLE_RAG_AGENT:
        workflow.add_edge("dispatcher", "rag")
    if settings.ENABLE_TEMPORAL_AGENT:
        workflow.add_edge("dispatcher", "temporal")

    # All agents converge to supervisor
    # Supervisor waits for all agents to complete
    if settings.ENABLE_RAG_AGENT:
        workflow.add_edge("rag", "supervisor")
    if settings.ENABLE_TEMPORAL_AGENT:
        workflow.add_edge("temporal", "supervisor")

    # Supervisor is the exit point
    workflow.add_edge("supervisor", END)

    # Compile graph
    compiled = workflow.compile()

    return compiled


async def run_multi_agent_query(query: str) -> Dict[str, Any]:
    """
    Run multi-agent query asynchronously.

    Args:
        query: User query

    Returns:
        dict: Result with answer, confidence, sources, primary_source
    """
    # Create initial state
    initial_state = create_initial_state(query)

    # Get compiled graph
    graph = create_multi_agent_graph()

    # Run graph (agents execute in parallel)
    result = await graph.ainvoke(initial_state)

    # Extract relevant results
    return {
        "answer": result.get("final_answer", ""),
        "confidence": result.get("confidence_score", 0.0),
        "sources": result.get("citations", []),
        "primary_source": result.get("primary_source", ""),
        "rag_confidence": result.get("rag_confidence", 0.0),
        "temporal_confidence": result.get("temporal_confidence", 0.0),
        "rag_source_metadata": result.get("rag_source_metadata", None),
    }


def run_multi_agent_query_sync(query: str) -> Dict[str, Any]:
    """
    Run multi-agent query synchronously (for CLI).

    Args:
        query: User query

    Returns:
        dict: Result with answer, confidence, sources, primary_source
    """
    import asyncio

    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(run_multi_agent_query(query))
    return result
