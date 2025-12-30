"""Intelligent failure analyzer that uses LLM to understand and fix command failures."""

import logging
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class FailureAnalyzer:
    """
    Analyzes command failures using LLM and suggests fixes.

    Capabilities:
    - Understands error messages and failure reasons
    - Identifies root causes (syntax, permissions, missing files, etc.)
    - Suggests specific corrections
    - Generates corrected commands automatically
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        temperature: float = 0.3
    ):
        """
        Initialize failure analyzer.

        Args:
            api_key: OpenAI API key
            model: Model to use for analysis
            temperature: Temperature for generation
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.logger = logging.getLogger(__name__)

    async def analyze_failure(
        self,
        user_intent: str,
        failed_command: str,
        error_output: str,
        return_code: int,
        shell_type: str = "powershell",
        previous_attempts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze why a command failed and suggest corrections.

        Args:
            user_intent: What the user wanted to do
            failed_command: The command that failed
            error_output: Error message from stderr
            return_code: Exit code
            shell_type: Shell that was used (powershell/cmd/bash)
            previous_attempts: List of previous failed attempts

        Returns:
            Dictionary containing:
            - failure_reason: Why the command failed
            - root_cause: Root cause category
            - corrected_command: Suggested fix
            - explanation: What was changed and why
            - confidence: How confident in the fix (low/medium/high)
            - should_retry: Whether to retry automatically
        """

        self.logger.info(f"Analyzing failure: {failed_command}")

        # Build analysis prompt
        system_prompt = f"""You are an expert {shell_type} troubleshooter. Analyze command failures and provide corrections.

Your task:
1. Understand WHY the command failed
2. Identify the root cause
3. Generate a corrected command that will work
4. Explain what you changed

Be specific and technical. Focus on fixing the actual problem."""

        # Build detailed user prompt
        user_prompt = f"""User wanted: "{user_intent}"

Failed Command ({shell_type}):
```
{failed_command}
```

Error Output:
```
{error_output[:1000]}
```

Return Code: {return_code}

Shell Type: {shell_type}
"""

        # Add previous attempts if available
        if previous_attempts:
            user_prompt += f"\n\nPrevious Failed Attempts ({len(previous_attempts)}):\n"
            for i, attempt in enumerate(previous_attempts, 1):
                user_prompt += f"{i}. Command: {attempt.get('command', 'N/A')}\n"
                user_prompt += f"   Error: {attempt.get('error', 'N/A')[:200]}\n"

        user_prompt += """
Provide your analysis in JSON format:
{
    "failure_reason": "Brief explanation of why it failed",
    "root_cause": "syntax_error|permission_denied|file_not_found|invalid_argument|path_issue|command_not_found|other",
    "corrected_command": "The fixed command",
    "explanation": "What you changed and why",
    "confidence": "low|medium|high",
    "should_retry": true/false,
    "alternative_approaches": ["list", "of", "alternative", "solutions"]
}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )

            import json
            analysis = json.loads(response.choices[0].message.content)

            self.logger.info(f"Failure analysis: {analysis['failure_reason']}")
            self.logger.info(f"Corrected command: {analysis.get('corrected_command')}")

            return analysis

        except Exception as e:
            self.logger.error(f"Failure analysis failed: {e}")
            # Return a basic fallback analysis
            return {
                "failure_reason": f"Analysis failed: {str(e)}",
                "root_cause": "other",
                "corrected_command": None,
                "explanation": "Could not analyze failure",
                "confidence": "low",
                "should_retry": False,
                "alternative_approaches": []
            }

    async def analyze_execution_timeout(
        self,
        user_intent: str,
        command: str,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """
        Analyze why a command timed out.

        Args:
            user_intent: User's original request
            command: Command that timed out
            timeout_seconds: Timeout duration

        Returns:
            Analysis with suggestions
        """

        system_prompt = """You are a command optimization expert. Analyze why commands timeout and provide faster alternatives."""

        user_prompt = f"""User wanted: "{user_intent}"

Command timed out after {timeout_seconds} seconds:
```
{command}
```

Why might this timeout? Suggest a faster alternative or optimized version.

Respond in JSON:
{{
    "failure_reason": "Why it likely timed out",
    "root_cause": "performance_issue",
    "corrected_command": "Optimized or alternative command",
    "explanation": "What you optimized",
    "confidence": "low|medium|high",
    "should_retry": true/false
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )

            import json
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            self.logger.error(f"Timeout analysis failed: {e}")
            return {
                "failure_reason": "Command execution exceeded timeout",
                "root_cause": "performance_issue",
                "corrected_command": None,
                "explanation": "Try breaking down into smaller operations",
                "confidence": "low",
                "should_retry": False
            }

    async def suggest_alternative_approach(
        self,
        user_intent: str,
        failed_attempts: List[Dict[str, Any]],
        shell_type: str = "powershell"
    ) -> Dict[str, Any]:
        """
        When multiple attempts fail, suggest a completely different approach.

        Args:
            user_intent: What user wants to achieve
            failed_attempts: All previous failed attempts
            shell_type: Current shell type

        Returns:
            Alternative approach suggestion
        """

        system_prompt = f"""You are a creative problem solver for {shell_type}.
When standard approaches fail, find alternative methods to achieve the same goal."""

        attempts_summary = "\n".join([
            f"Attempt {i+1}: {attempt['command']}\nError: {attempt['error'][:200]}"
            for i, attempt in enumerate(failed_attempts)
        ])

        user_prompt = f"""User goal: "{user_intent}"

Multiple approaches have failed:
```
{attempts_summary}
```

Suggest a COMPLETELY DIFFERENT approach that might work. Think outside the box.

Respond in JSON:
{{
    "failure_reason": "Summary of why previous attempts failed",
    "alternative_approach": "Describe the new approach",
    "corrected_command": "Command using the new approach",
    "explanation": "Why this might work when others didn't",
    "confidence": "low|medium|high",
    "should_retry": true/false
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.5,  # Higher temperature for creativity
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )

            import json
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            self.logger.error(f"Alternative approach suggestion failed: {e}")
            return {
                "failure_reason": "Multiple attempts failed",
                "alternative_approach": "Could not suggest alternative",
                "corrected_command": None,
                "explanation": "Manual intervention may be required",
                "confidence": "low",
                "should_retry": False
            }

    def categorize_error(self, error_output: str, return_code: int) -> str:
        """
        Quick categorization of error type based on patterns.

        Args:
            error_output: Error message
            return_code: Exit code

        Returns:
            Error category
        """

        error_lower = error_output.lower()

        # Pattern matching for common errors
        if "access" in error_lower or "denied" in error_lower or "permission" in error_lower:
            return "permission_denied"
        elif "not found" in error_lower or "cannot find" in error_lower:
            return "file_not_found"
        elif "syntax" in error_lower or "unexpected token" in error_lower:
            return "syntax_error"
        elif "invalid" in error_lower or "illegal" in error_lower:
            return "invalid_argument"
        elif "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        elif "path" in error_lower and ("not" in error_lower or "invalid" in error_lower):
            return "path_issue"
        elif return_code == 127 or "not recognized" in error_lower:
            return "command_not_found"
        elif return_code == 1:
            return "general_error"
        else:
            return "unknown_error"
