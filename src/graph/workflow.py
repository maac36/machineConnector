"""LangGraph workflow construction and compilation."""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import CommandState
from graph.nodes import (
    generate_command_node,
    await_confirmation_node,
    execute_command_node,
    validate_result_node,
    present_result_node,
    retry_node,
    try_alternative_shell_node,
    analyze_content_node,
    intelligent_retry_node
)
from graph.edges import (
    route_after_confirmation,
    route_after_execution,
    route_after_retry
)
import logging

logger = logging.getLogger(__name__)


def create_workflow():
    """
    Construct the LangGraph workflow.

    Graph structure:
    START → generate → confirm → execute → validate → present → END
               ↑          ↓
               └── retry ←┘

    Returns:
        Compiled LangGraph application
    """

    logger.info("Creating LangGraph workflow")

    # Initialize graph with state schema
    workflow = StateGraph(CommandState)

    # Add nodes
    workflow.add_node("generate_command", generate_command_node)
    workflow.add_node("await_confirmation", await_confirmation_node)
    workflow.add_node("execute_command", execute_command_node)
    workflow.add_node("validate_result", validate_result_node)
    workflow.add_node("present_result", present_result_node)
    workflow.add_node("retry_node", retry_node)
    workflow.add_node("intelligent_retry", intelligent_retry_node)
    workflow.add_node("try_alternative_shell", try_alternative_shell_node)
    workflow.add_node("analyze_content", analyze_content_node)

    # Add edges
    # Start with generation
    workflow.add_edge(START, "generate_command")

    # After generation, go to confirmation
    workflow.add_edge("generate_command", "await_confirmation")

    # Conditional edge after confirmation
    workflow.add_conditional_edges(
        "await_confirmation",
        route_after_confirmation,
        {
            "execute_command": "execute_command",
            "retry_node": "retry_node",
            "end": END
        }
    )

    # Conditional edge after execution
    workflow.add_conditional_edges(
        "execute_command",
        route_after_execution,
        {
            "validate_result": "validate_result",
            "present_result": "present_result",
            "intelligent_retry": "intelligent_retry",
            "try_alternative_shell": "try_alternative_shell"
        }
    )

    # After intelligent retry, go back to execute with corrected command
    workflow.add_edge("intelligent_retry", "execute_command")

    # After validation, check if analysis is needed
    def route_after_validation(state: CommandState):
        """Route to analysis if needed, otherwise present."""
        if state.get("requires_analysis"):
            logger.debug("Routing to analyze_content (analysis required)")
            return "analyze_content"
        else:
            logger.debug("Routing to present_result (no analysis needed)")
            return "present_result"

    workflow.add_conditional_edges(
        "validate_result",
        route_after_validation,
        {
            "analyze_content": "analyze_content",
            "present_result": "present_result"
        }
    )

    # After analysis, go to presentation
    workflow.add_edge("analyze_content", "present_result")

    # After presentation, end
    workflow.add_edge("present_result", END)

    # Conditional edge after retry
    workflow.add_conditional_edges(
        "retry_node",
        route_after_retry,
        {
            "generate_command": "generate_command",
            "end": END
        }
    )

    # After trying alternative shell, go back to execute
    workflow.add_edge("try_alternative_shell", "execute_command")

    # Add checkpointer for persistence
    memory = MemorySaver()

    # Compile graph
    app = workflow.compile(checkpointer=memory)

    logger.info("LangGraph workflow compiled successfully")

    return app
