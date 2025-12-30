"""Input and output sanitization utilities."""

from typing import Any


def sanitize_output(output: str, max_length: int = 10000) -> str:
    """
    Sanitize command output for display.

    Args:
        output: Raw output string
        max_length: Maximum length before truncation

    Returns:
        Sanitized output string
    """
    if not output:
        return "(empty)"

    # Truncate if too long
    if len(output) > max_length:
        return output[:max_length] + "\n... (output truncated)"

    return output


def sanitize_error(error: str, max_length: int = 5000) -> str:
    """
    Sanitize error output for display.

    Args:
        error: Raw error string
        max_length: Maximum length before truncation

    Returns:
        Sanitized error string
    """
    if not error:
        return "(no errors)"

    # Truncate if too long
    if len(error) > max_length:
        return error[:max_length] + "\n... (error message truncated)"

    return error


def sanitize_user_input(user_input: str) -> str:
    """
    Sanitize user input.

    Args:
        user_input: Raw user input

    Returns:
        Sanitized input string
    """
    # Strip whitespace
    sanitized = user_input.strip()

    # Limit length
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000]

    return sanitized
