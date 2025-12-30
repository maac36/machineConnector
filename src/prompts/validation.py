"""Prompts for result validation."""

from typing import Dict, Any


def get_validation_prompt(
    user_intent: str,
    command: str,
    execution_result: Dict[str, Any]
) -> Dict[str, str]:
    """
    Generate prompts for result validation.

    Args:
        user_intent: The user's original request
        command: The PowerShell command that was executed
        execution_result: The execution results (stdout, stderr, return_code)

    Returns:
        Dictionary with 'system' and 'user' prompts
    """

    system_prompt = """You are an expert at validating PowerShell command execution results.

Your role:
1. Determine if the command execution achieved the user's stated goal
2. Analyze stdout, stderr, and return code
3. Provide clear reasoning for your assessment
4. Suggest improvements if applicable

Validation criteria:
- Return code (0 = success, non-zero = failure)
- Output content matches expected result
- No critical errors in stderr (warnings are acceptable)
- User's intent was fulfilled

Output format (JSON):
{
    "passed": true/false,
    "reasoning": "Detailed explanation of validation decision",
    "suggestions": ["Optional list of improvements or next steps"],
    "confidence": "high|medium|low"
}

Guidelines:
- Return code 0 with expected output = PASS
- Return code 0 with empty output might be PASS if operation doesn't produce output
- Return code non-zero = Usually FAIL unless stderr explains it's a warning
- Check if output actually matches what user asked for
- Consider edge cases (no results found vs. error searching)"""

    stdout_preview = execution_result.get('stdout', '(empty)')[:1000]
    stderr_preview = execution_result.get('stderr', '(empty)')[:1000]

    if len(execution_result.get('stdout', '')) > 1000:
        stdout_preview += "\n... (output truncated)"
    if len(execution_result.get('stderr', '')) > 1000:
        stderr_preview += "\n... (output truncated)"

    user_prompt = f"""User's original intent: {user_intent}

Command executed: {command}

Execution results:
- Return code: {execution_result.get('return_code')}
- Execution time: {execution_result.get('execution_time', 0):.2f} seconds
- Timed out: {execution_result.get('timed_out', False)}

Standard Output:
{stdout_preview}

Standard Error:
{stderr_preview}

Did this execution successfully achieve the user's intent?"""

    return {
        "system": system_prompt,
        "user": user_prompt
    }
