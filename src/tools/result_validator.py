"""Validates command execution results using LLM."""

from openai import AsyncOpenAI
from typing import Dict, Any
import json
import logging


class ResultValidator:
    """
    Validates command execution results using LLM.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o", temperature: float = 0.2):
        """
        Initialize the result validator.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
            temperature: Sampling temperature (default: 0.2 for consistent validation)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.logger = logging.getLogger(__name__)

    async def validate(
        self,
        user_intent: str,
        command: str,
        execution_result: Dict[str, Any]
    ) -> Dict:
        """
        Validate if execution achieved user's intent.

        Args:
            user_intent: User's original request
            command: PowerShell command that was executed
            execution_result: Execution results (stdout, stderr, return_code)

        Returns:
            Dictionary containing:
            - passed: Boolean indicating validation success
            - reasoning: Explanation of validation decision
            - suggestions: List of improvement suggestions
            - confidence: high|medium|low
        """

        from prompts.validation import get_validation_prompt

        prompt = get_validation_prompt(user_intent, command, execution_result)

        self.logger.info(f"Validating execution for: {user_intent}")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature
            )

            result = json.loads(response.choices[0].message.content)

            self.logger.info(
                f"Validation result: passed={result.get('passed')}, "
                f"confidence={result.get('confidence')}"
            )
            self.logger.debug(f"Validation reasoning: {result.get('reasoning')}")

            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")

        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            raise
