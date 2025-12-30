"""Conditional edge routing logic for the workflow graph."""

from typing import Literal
from graph.state import CommandState
import logging

logger = logging.getLogger(__name__)


def route_after_confirmation(
    state: CommandState
) -> Literal["execute_command", "retry_node", "end"]:
    """
    Route based on user confirmation.

    Logic:
    - If confirmed: proceed to execution
    - If rejected with feedback: retry generation
    - If rejected without feedback or blocked: end
    """

    if state.get("user_confirmed"):
        logger.debug("Routing to execute_command (user confirmed)")
        return "execute_command"
    elif state.get("user_feedback"):
        logger.debug("Routing to retry_node (user provided feedback)")
        return "retry_node"
    else:
        logger.debug("Routing to end (user rejected without feedback)")
        return "end"


def route_after_execution(
    state: CommandState
) -> Literal["validate_result", "present_result", "try_alternative_shell", "intelligent_retry"]:
    """
    Route based on execution status.

    Logic:
    - next_step is "intelligent_retry": analyze failure and retry with corrected command
    - next_step is "try_alternative": try alternative shell
    - Success or Failed: validate results
    - Error: skip validation and go to presentation
    """

    # Check next_step for explicit routing
    next_step = state.get("next_step")

    if next_step == "intelligent_retry":
        logger.debug("Routing to intelligent_retry (will analyze and fix failure)")
        return "intelligent_retry"

    if next_step == "try_alternative":
        logger.debug("Routing to try_alternative_shell (execution failed)")
        return "try_alternative_shell"

    # Check execution status
    status = state.get("execution_status")

    if status in ["success", "failed"]:
        logger.debug(f"Routing to validate_result (status: {status})")
        return "validate_result"
    else:
        logger.debug(f"Routing to present_result (status: {status}, skipping validation)")
        return "present_result"


def route_after_retry(
    state: CommandState
) -> Literal["generate_command", "end"]:
    """
    Route based on retry count.

    Logic:
    - If retries remaining: regenerate command
    - If max retries exceeded: end
    """

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count < max_retries:
        logger.debug(f"Routing to generate_command (retry {retry_count}/{max_retries})")
        return "generate_command"
    else:
        logger.debug(f"Routing to end (max retries {max_retries} exceeded)")
        return "end"
