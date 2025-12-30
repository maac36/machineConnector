"""Graph node implementations for the PowerShell command workflow."""

from datetime import datetime
from typing import Dict, Any
import logging

from graph.state import CommandState
from tools.command_generator import CommandGenerator
from tools.command_executor import PowerShellExecutor
from tools.result_validator import ResultValidator
from tools.content_analyzer import ContentAnalyzer
from tools.file_reader import FileReader
from security.command_filter import CommandFilter
from config.settings import settings
from langgraph.types import interrupt
import os

logger = logging.getLogger(__name__)

# Initialize tools
command_generator = CommandGenerator(
    api_key=settings.openai_api_key,
    model=settings.openai_model,
    temperature=settings.openai_temperature
)

command_executor = PowerShellExecutor(
    timeout=settings.max_execution_timeout,
    max_output_size=settings.max_output_size
)

result_validator = ResultValidator(
    api_key=settings.openai_api_key,
    model=settings.openai_model
)

content_analyzer = ContentAnalyzer(
    api_key=settings.openai_api_key,
    model=settings.openai_model,
    temperature=settings.openai_temperature
)

file_reader = FileReader(max_file_size=10 * 1024 * 1024)  # 10MB max

command_filter = CommandFilter()


async def generate_command_node(state: CommandState) -> Dict[str, Any]:
    """
    Generate PowerShell command from user input using OpenAI.
    Also detects if user wants content analysis instead of just execution.

    Flow:
    1. Retrieve user input from state
    2. Detect if user wants analysis (e.g., "read X and explain")
    3. Call OpenAI with specialized prompt
    4. Parse response (command + explanation)
    5. Perform safety assessment on generated command
    6. Update state with results
    """

    logger.info("Node: generate_command")

    try:
        user_input = state["user_input"]

        # Detect analysis intent from user input
        analysis_keywords = [
            "explain", "analyze", "check what", "what is the purpose",
            "understand", "summarize", "review", "describe", "tell me about"
        ]

        file_operation_keywords = ["read", "checkout", "clone", "download", "cat", "type"]

        requires_analysis = False
        analysis_type = "general"

        lower_input = user_input.lower()

        # Check if user wants to read file AND analyze it
        if any(keyword in lower_input for keyword in analysis_keywords):
            if any(op in lower_input for op in file_operation_keywords):
                requires_analysis = True
                logger.info("Detected analysis request in user input")

                # Determine analysis type
                if "purpose" in lower_input or "what is" in lower_input:
                    analysis_type = "purpose"
                elif "security" in lower_input or "vulnerab" in lower_input:
                    analysis_type = "security"
                elif "explain" in lower_input or "understand" in lower_input:
                    analysis_type = "explain"

        # Prepare context for generation
        context = {}
        if state.get("user_feedback"):
            context["previous_feedback"] = state["user_feedback"]
        if state.get("retry_count", 0) > 0:
            context["retry_count"] = state["retry_count"]

        # Add conversation history if available
        if state.get("conversation_messages"):
            context["conversation_messages"] = state["conversation_messages"]
            logger.debug(f"Including {len(state['conversation_messages'])} conversation messages in context")

        # Generate command
        generation_result = await command_generator.generate(
            user_input=user_input,
            context=context
        )

        # Assess safety
        safety_assessment = command_filter.assess(generation_result["command"])

        # Combine warnings from LLM and filter
        all_warnings = (
            generation_result.get("warnings", []) +
            safety_assessment.get("warnings", [])
        )

        combined_assessment = {
            "level": safety_assessment["level"],
            "warnings": all_warnings,
            "allow": safety_assessment["allow"],
            "llm_safety": generation_result.get("safety_level"),
            "filter_patterns": safety_assessment.get("matched_patterns", [])
        }

        return {
            "generated_command": generation_result["command"],
            "command_explanation": generation_result["explanation"],
            "safety_assessment": combined_assessment,
            "requires_analysis": requires_analysis,
            "analysis_type": analysis_type if requires_analysis else None,
            "next_step": "confirm",
            "messages": state.get("messages", []) + [{
                "role": "assistant",
                "content": f"Generated command: {generation_result['command']}",
                "timestamp": datetime.now().isoformat()
            }]
        }

    except Exception as e:
        logger.error(f"Command generation failed: {e}")
        return {
            "error_message": str(e),
            "error_type": "generation_error",
            "execution_status": "error",
            "next_step": "end"
        }


async def await_confirmation_node(state: CommandState) -> Dict[str, Any]:
    """
    Present command to user and wait for confirmation.

    Uses LangGraph's interrupt() for human-in-the-loop interaction.
    """

    logger.info("Node: await_confirmation")

    # Check if we're resuming after interrupt (user already confirmed)
    if state.get("user_confirmed") is not None:
        logger.info(f"Resuming after user confirmation: {state['user_confirmed']}")
        # Already confirmed, just pass through
        # Return minimal update (LangGraph requires at least one field update)
        return {
            "confirmation_timestamp": state.get("confirmation_timestamp", datetime.now())
        }

    # Check if command was blocked by safety filter
    if not state["safety_assessment"]["allow"]:
        logger.warning("Command blocked by safety filter")
        return {
            "user_confirmed": False,
            "confirmation_timestamp": datetime.now(),
            "user_feedback": "Command blocked due to safety concerns",
            "error_message": "Command blocked: " + "; ".join(state["safety_assessment"]["warnings"]),
            "next_step": "end"
        }

    # Prepare confirmation prompt data
    confirmation_data = {
        "command": state["generated_command"],
        "explanation": state["command_explanation"],
        "safety": state["safety_assessment"]
    }

    # Interrupt execution and wait for user input
    # The user will see the command and must approve/reject
    # The interrupt will pause here, and user response will be added to state by main.py
    interrupt(confirmation_data)

    # This line won't be reached after interrupt - workflow will resume from the top of this node
    # But just in case, return a minimal update
    return {
        "confirmation_timestamp": datetime.now()
    }


async def execute_command_node(state: CommandState) -> Dict[str, Any]:
    """
    Execute command with security best practices.
    Supports PowerShell, CMD, and Bash.

    Security measures:
    - No shell=True
    - Command passed as list
    - Timeout enforcement
    - Output capture with size limits
    - Error handling
    """

    logger.info("Node: execute_command")

    # Determine which shell to use (default to PowerShell)
    shell_type = state.get("shell_type", "powershell")

    try:
        # Execute based on shell type
        if shell_type == "cmd":
            result = await command_executor.execute_cmd(
                command=state["generated_command"],
                timeout=settings.max_execution_timeout
            )
        elif shell_type == "bash":
            result = await command_executor.execute_bash(
                command=state["generated_command"],
                timeout=settings.max_execution_timeout
            )
        else:  # default to PowerShell
            result = await command_executor.execute(
                command=state["generated_command"],
                timeout=settings.max_execution_timeout
            )

        # Check if execution failed or had errors
        has_error = result.get("error") or result.get("return_code", 0) != 0
        status = "success" if result["return_code"] == 0 else "failed"

        logger.info(f"Execution {status}: return_code={result['return_code']}, shell={shell_type}")

        # If failed and haven't tried alternatives, try alternative shell
        attempted_shells = state.get("attempted_shells", [])
        if has_error and shell_type not in attempted_shells:
            logger.info(f"Execution failed with {shell_type}, will try alternative shell")
            return {
                "execution_status": status,
                "execution_result": result,
                "execution_timestamp": datetime.now(),
                "attempted_shells": [shell_type],
                "next_step": "try_alternative"
            }

        return {
            "execution_status": status,
            "execution_result": result,
            "execution_timestamp": datetime.now(),
            "attempted_shells": [shell_type],
            "next_step": "validate"
        }

    except Exception as e:
        logger.error(f"Command execution failed: {e}")

        # Try alternative shell if we haven't yet
        attempted_shells = state.get("attempted_shells", [])
        shell_type = state.get("shell_type", "powershell")

        if shell_type not in attempted_shells:
            logger.info(f"Execution error with {shell_type}, will try alternative shell")
            return {
                "execution_status": "error",
                "error_message": str(e),
                "error_type": "execution_error",
                "execution_timestamp": datetime.now(),
                "attempted_shells": [shell_type],
                "next_step": "try_alternative"
            }

        return {
            "execution_status": "error",
            "error_message": str(e),
            "error_type": "execution_error",
            "execution_timestamp": datetime.now(),
            "next_step": "present"  # Skip validation on error
        }


async def validate_result_node(state: CommandState) -> Dict[str, Any]:
    """
    Use LLM to determine if execution achieved user's intent.

    Validation criteria:
    1. Did command execute successfully?
    2. Does output match expected result?
    3. Did it achieve user's stated goal?
    """

    logger.info("Node: validate_result")

    try:
        validation = await result_validator.validate(
            user_intent=state["user_input"],
            command=state["generated_command"],
            execution_result=state["execution_result"]
        )

        logger.info(f"Validation: passed={validation['passed']}")

        return {
            "validation_passed": validation["passed"],
            "validation_reasoning": validation["reasoning"],
            "validation_suggestions": validation.get("suggestions", []),
            "next_step": "present"
        }

    except Exception as e:
        logger.error(f"Result validation failed: {e}")
        # Don't fail the whole workflow if validation fails
        return {
            "validation_passed": None,
            "validation_reasoning": f"Validation failed: {str(e)}",
            "validation_suggestions": [],
            "next_step": "present"
        }


async def present_result_node(state: CommandState) -> Dict[str, Any]:
    """
    Format and display results to user.

    This node doesn't output directly - it prepares data
    for the CLI to display.
    """

    logger.info("Node: present_result")

    # Add to execution history
    history_entry = {
        "timestamp": state["execution_timestamp"].isoformat() if state.get("execution_timestamp") else None,
        "user_input": state["user_input"],
        "command": state.get("generated_command"),
        "result": state.get("execution_result"),
        "validated": state.get("validation_passed"),
        "status": state.get("execution_status")
    }

    return {
        "next_step": "end",
        "execution_history": state.get("execution_history", []) + [history_entry]
    }


async def retry_node(state: CommandState) -> Dict[str, Any]:
    """
    Handle command rejection and retry with user feedback.
    """

    logger.info("Node: retry")

    retry_count = state.get("retry_count", 0) + 1

    if retry_count >= state.get("max_retries", settings.max_retries):
        logger.warning(f"Maximum retries ({state['max_retries']}) exceeded")
        return {
            "next_step": "end",
            "error_message": "Maximum retries exceeded",
            "retry_count": retry_count
        }

    logger.info(f"Retry attempt {retry_count}/{state.get('max_retries', settings.max_retries)}")

    # User feedback will be included in context for next generation
    return {
        "retry_count": retry_count,
        "next_step": "generate"
    }


async def analyze_content_node(state: CommandState) -> Dict[str, Any]:
    """
    Analyze content using LLM (files, code, command output).

    This node is called when user wants to understand/analyze content.

    Flow:
    1. Extract content from execution results or read files
    2. Use LLM to analyze and provide insights
    3. Present analysis to user
    """

    logger.info("Node: analyze_content")

    try:
        analysis_type = state.get("analysis_type", "general")
        user_input = state["user_input"]

        # Determine what to analyze
        content_to_analyze = None
        analysis_target = None

        # Option 1: Analyze command output
        if state.get("execution_result"):
            execution_result = state["execution_result"]
            output = execution_result.get("stdout", "")

            # Check if output contains file path that we should read
            if output and len(output) < 500:
                # Might be a file path, try to read it
                file_content_result = await file_reader.read_file_from_command_output(output)
                if file_content_result:
                    content_to_analyze = file_content_result["content"]
                    analysis_target = file_content_result["file_path"]
                    logger.info(f"Reading file from output: {analysis_target}")

            # If no file found in output, analyze the output itself
            if not content_to_analyze and output:
                # Analyze the command output
                analysis_result = await content_analyzer.analyze_command_output(
                    command=state["generated_command"],
                    output=output,
                    user_intent=user_input
                )
                return {
                    "analysis_result": analysis_result,
                    "next_step": "present"
                }

        # Option 2: Try to extract file path from user input
        if not content_to_analyze:
            import re

            # Extract potential file paths from user input
            # Windows paths
            win_paths = re.findall(r'([A-Z]:\\[^\s]+)|([a-z]:\\[^\s]+)', user_input)
            # Relative paths
            rel_paths = re.findall(r'([^\s]+\.[a-z]{2,4})', user_input)  # file.txt, script.py, etc.

            potential_paths = [p for tup in win_paths for p in tup if p] + rel_paths

            for path in potential_paths:
                if os.path.exists(path) and os.path.isfile(path):
                    file_result = await file_reader.read_file(path)
                    content_to_analyze = file_result["content"]
                    analysis_target = path
                    break

        # Option 3: Check if execution created/cloned a repository
        if not content_to_analyze and state.get("execution_result"):
            stdout = state["execution_result"].get("stdout", "")
            # Check for git clone output
            if "Cloning into" in stdout or "checkout" in state["generated_command"].lower():
                # Try to find the repo directory
                import re
                clone_match = re.search(r"Cloning into '([^']+)'", stdout)
                if clone_match:
                    repo_path = clone_match.group(1)
                    if os.path.exists(repo_path):
                        repo_info = await file_reader.get_repository_structure(repo_path)
                        analysis_result = await content_analyzer.analyze_code_repository(
                            repo_path=repo_path,
                            file_list=repo_info["file_list"],
                            readme_content=repo_info.get("readme_content")
                        )
                        return {
                            "analysis_result": analysis_result,
                            "analysis_target": repo_path,
                            "next_step": "present"
                        }

        # If we have content, analyze it
        if content_to_analyze:
            logger.info(f"Analyzing {analysis_type}: {analysis_target}")

            analysis_result = await content_analyzer.analyze_file(
                file_path=analysis_target or "content",
                content=content_to_analyze,
                analysis_type=analysis_type
            )

            return {
                "analysis_result": analysis_result,
                "analysis_target": analysis_target,
                "content_to_analyze": content_to_analyze[:1000],  # Store sample
                "next_step": "present"
            }

        # No content found to analyze
        logger.warning("No content found to analyze")
        return {
            "error_message": "Could not find content to analyze. Please ensure the file exists or command output is available.",
            "next_step": "present"
        }

    except Exception as e:
        logger.error(f"Content analysis failed: {e}")
        return {
            "error_message": f"Analysis failed: {str(e)}",
            "error_type": "analysis_error",
            "next_step": "present"
        }


async def try_alternative_shell_node(state: CommandState) -> Dict[str, Any]:
    """
    Try alternative shell when PowerShell/CMD/Bash execution fails.

    Logic:
    1. Check which shells have been attempted
    2. Pick next shell to try (PowerShell -> CMD -> Bash)
    3. Generate new command for that shell
    4. Execute it
    """

    logger.info("Node: try_alternative_shell")

    attempted_shells = state.get("attempted_shells", [])
    current_shell = state.get("shell_type", "powershell")

    # Determine next shell to try
    shell_order = ["powershell", "cmd", "bash"]
    next_shell = None

    for shell in shell_order:
        if shell not in attempted_shells:
            next_shell = shell
            break

    if not next_shell:
        logger.warning("All shell types have been attempted")
        return {
            "error_message": f"Execution failed in all shells: {', '.join(attempted_shells)}",
            "next_step": "present"
        }

    logger.info(f"Trying alternative shell: {next_shell} (previous: {current_shell})")

    try:
        # Ask LLM to generate command for the alternative shell
        context = {
            "previous_shell": current_shell,
            "previous_command": state.get("generated_command"),
            "previous_error": state.get("execution_result", {}).get("stderr", ""),
            "target_shell": next_shell
        }

        # Build prompt for alternative shell
        prompt = f"""The previous {current_shell} command failed with error:
{context['previous_error']}

Previous command: {context['previous_command']}

Please generate an equivalent {next_shell} command to accomplish the same task: {state['user_input']}

Provide ONLY the {next_shell} command, no explanations."""

        # Generate command for alternative shell
        generation_result = await command_generator.generate(
            user_input=prompt,
            context={"shell_type": next_shell}
        )

        # Assess safety
        safety_assessment = command_filter.assess(generation_result["command"])

        logger.info(f"Generated {next_shell} command: {generation_result['command']}")

        return {
            "generated_command": generation_result["command"],
            "command_explanation": f"Alternative {next_shell} command: {generation_result['explanation']}",
            "safety_assessment": {
                "level": safety_assessment["level"],
                "warnings": safety_assessment.get("warnings", []),
                "allow": safety_assessment["allow"]
            },
            "shell_type": next_shell,
            "user_confirmed": True,  # Auto-confirm alternative (already confirmed intent)
            "next_step": "execute"
        }

    except Exception as e:
        logger.error(f"Alternative shell generation failed: {e}")
        return {
            "error_message": f"Failed to generate {next_shell} alternative: {str(e)}",
            "error_type": "alternative_generation_error",
            "next_step": "present"
        }
