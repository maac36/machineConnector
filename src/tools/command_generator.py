"""Generates PowerShell commands from natural language using OpenAI."""

from openai import AsyncOpenAI
from typing import Dict, Optional
import json
import logging


class CommandGenerator:
    """
    Generates PowerShell commands from natural language using OpenAI.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o", temperature: float = 0.3):
        """
        Initialize the command generator.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
            temperature: Sampling temperature (default: 0.3 for consistency)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.logger = logging.getLogger(__name__)

    async def generate(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        Generate PowerShell command with explanation.

        Args:
            user_input: Natural language command request
            context: Optional context (previous_feedback, retry_count, conversation_history)

        Returns:
            Dictionary containing:
            - command: PowerShell command string
            - explanation: What the command does
            - safety_level: safe|caution|dangerous
            - warnings: List of warnings
            - assumptions: List of assumptions made
        """

        from prompts.command_generation import get_generation_prompt

        prompt = get_generation_prompt(user_input, context)

        self.logger.info(f"Generating command for: {user_input}")

        # Build messages list
        messages = [{"role": "system", "content": prompt["system"]}]

        # Add conversation history if provided
        if context and context.get("conversation_messages"):
            conversation_messages = context["conversation_messages"]
            if conversation_messages:
                self.logger.debug(f"Including {len(conversation_messages)} previous conversation messages")
                messages.extend(conversation_messages)

        # Add current user request
        messages.append({"role": "user", "content": prompt["user"]})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=self.temperature
            )

            result = json.loads(response.choices[0].message.content)

            self.logger.info(f"Generated command: {result.get('command')}")
            self.logger.debug(f"Full response: {result}")

            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")

        except Exception as e:
            self.logger.error(f"Command generation failed: {e}")
            raise
