"""Conversation memory manager for maintaining context across sessions."""

import json
import logging
from collections import deque
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation history with persistence.

    Features:
    - Keeps last N conversations in memory
    - Persists to disk (JSON)
    - Provides context for LLM
    - Thread-safe operations
    """

    def __init__(
        self,
        max_conversations: int = 5,
        storage_file: Optional[str] = None,
        enable_persistence: bool = True
    ):
        """
        Initialize conversation memory.

        Args:
            max_conversations: Maximum number of conversations to keep
            storage_file: Path to JSON file for persistence
            enable_persistence: Whether to save/load from disk
        """
        self.max_conversations = max_conversations
        self.enable_persistence = enable_persistence
        self.logger = logging.getLogger(__name__)

        # Use deque for efficient FIFO operations
        self.conversations: deque = deque(maxlen=max_conversations)

        # Storage file path
        if storage_file:
            self.storage_file = Path(storage_file)
        else:
            # Default to user home directory
            home = Path.home()
            self.storage_file = home / ".claude" / "langgraph_powershell" / "conversation_memory.json"

        # Ensure directory exists
        if self.enable_persistence:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing conversations
        if self.enable_persistence:
            self.load_from_disk()

    def add_conversation(
        self,
        user_input: str,
        generated_command: Optional[str] = None,
        execution_result: Optional[Dict[str, Any]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a conversation to memory.

        Args:
            user_input: User's natural language request
            generated_command: Generated command
            execution_result: Command execution results
            analysis_result: Content analysis results
            metadata: Additional metadata
        """

        conversation = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "generated_command": generated_command,
            "execution_result": {
                "status": execution_result.get("return_code", -1) if execution_result else None,
                "stdout_preview": execution_result.get("stdout", "")[:500] if execution_result else None,
                "stderr_preview": execution_result.get("stderr", "")[:200] if execution_result else None
            } if execution_result else None,
            "analysis_result": {
                "analysis_type": analysis_result.get("analysis_type") if analysis_result else None,
                "summary": analysis_result.get("analysis", "")[:500] if analysis_result else None
            } if analysis_result else None,
            "metadata": metadata or {}
        }

        self.conversations.append(conversation)
        self.logger.info(f"Added conversation to memory (total: {len(self.conversations)})")

        # Save to disk
        if self.enable_persistence:
            self.save_to_disk()

    def get_context_for_llm(self, include_last_n: int = 3) -> str:
        """
        Format conversation history as context for LLM.

        Args:
            include_last_n: Number of recent conversations to include

        Returns:
            Formatted context string
        """

        if not self.conversations:
            return ""

        # Get last N conversations
        recent_conversations = list(self.conversations)[-include_last_n:]

        context_lines = ["Previous conversation history:"]

        for i, conv in enumerate(recent_conversations, 1):
            context_lines.append(f"\n{i}. User: {conv['user_input']}")

            if conv.get("generated_command"):
                context_lines.append(f"   Command: {conv['generated_command']}")

            if conv.get("execution_result"):
                result = conv["execution_result"]
                if result.get("status") == 0:
                    context_lines.append("   Result: Success")
                else:
                    context_lines.append(f"   Result: Failed (code {result.get('status')})")

            if conv.get("analysis_result") and conv["analysis_result"].get("summary"):
                summary = conv["analysis_result"]["summary"][:100]
                context_lines.append(f"   Analysis: {summary}...")

        return "\n".join(context_lines)

    def get_recent_commands(self, count: int = 5) -> List[str]:
        """
        Get list of recent commands.

        Args:
            count: Number of commands to return

        Returns:
            List of command strings
        """

        commands = []
        for conv in reversed(self.conversations):
            if conv.get("generated_command"):
                commands.append(conv["generated_command"])
                if len(commands) >= count:
                    break

        return commands

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get all conversations in memory.

        Returns:
            List of conversation dictionaries
        """
        return list(self.conversations)

    def clear_memory(self) -> None:
        """Clear all conversations from memory."""
        self.conversations.clear()
        self.logger.info("Cleared conversation memory")

        if self.enable_persistence:
            self.save_to_disk()

    def save_to_disk(self) -> None:
        """Save conversations to disk."""
        try:
            data = {
                "max_conversations": self.max_conversations,
                "last_updated": datetime.now().isoformat(),
                "conversations": list(self.conversations)
            }

            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"Saved {len(self.conversations)} conversations to {self.storage_file}")

        except Exception as e:
            self.logger.error(f"Failed to save conversations: {e}")

    def load_from_disk(self) -> None:
        """Load conversations from disk."""
        if not self.storage_file.exists():
            self.logger.debug("No existing conversation file found")
            return

        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            conversations = data.get("conversations", [])

            # Load into deque (will automatically limit to max_conversations)
            self.conversations = deque(conversations, maxlen=self.max_conversations)

            self.logger.info(f"Loaded {len(self.conversations)} conversations from disk")

        except Exception as e:
            self.logger.error(f"Failed to load conversations: {e}")
            self.conversations = deque(maxlen=self.max_conversations)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about conversation memory.

        Returns:
            Summary dictionary
        """

        if not self.conversations:
            return {
                "total_conversations": 0,
                "max_capacity": self.max_conversations,
                "oldest_timestamp": None,
                "newest_timestamp": None
            }

        return {
            "total_conversations": len(self.conversations),
            "max_capacity": self.max_conversations,
            "oldest_timestamp": self.conversations[0]["timestamp"],
            "newest_timestamp": self.conversations[-1]["timestamp"],
            "storage_file": str(self.storage_file) if self.enable_persistence else None
        }

    def search_conversations(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Search conversations by keyword.

        Args:
            keyword: Keyword to search for

        Returns:
            List of matching conversations
        """

        keyword_lower = keyword.lower()
        matches = []

        for conv in self.conversations:
            # Search in user input
            if keyword_lower in conv["user_input"].lower():
                matches.append(conv)
                continue

            # Search in command
            if conv.get("generated_command") and keyword_lower in conv["generated_command"].lower():
                matches.append(conv)
                continue

        return matches

    def get_context_messages(self, include_last_n: int = 3) -> List[Dict[str, str]]:
        """
        Get conversation history formatted as OpenAI messages.

        Args:
            include_last_n: Number of recent conversations to include

        Returns:
            List of message dictionaries for OpenAI API
        """

        if not self.conversations:
            return []

        recent_conversations = list(self.conversations)[-include_last_n:]
        messages = []

        for conv in recent_conversations:
            # User message
            messages.append({
                "role": "user",
                "content": conv["user_input"]
            })

            # Assistant response
            assistant_content = []

            if conv.get("generated_command"):
                assistant_content.append(f"Generated command: {conv['generated_command']}")

            if conv.get("execution_result"):
                result = conv["execution_result"]
                if result.get("status") == 0:
                    assistant_content.append("Command executed successfully")
                    if result.get("stdout_preview"):
                        assistant_content.append(f"Output: {result['stdout_preview']}")

            if conv.get("analysis_result") and conv["analysis_result"].get("summary"):
                assistant_content.append(f"Analysis: {conv['analysis_result']['summary']}")

            if assistant_content:
                messages.append({
                    "role": "assistant",
                    "content": "\n".join(assistant_content)
                })

        return messages

    def has_recent_file_analysis(self, file_path: str, within_minutes: int = 30) -> bool:
        """
        Check if a file was recently analyzed.

        Args:
            file_path: File path to check
            within_minutes: Time window in minutes

        Returns:
            True if file was recently analyzed
        """

        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(minutes=within_minutes)

        for conv in reversed(self.conversations):
            # Parse timestamp
            conv_time = datetime.fromisoformat(conv["timestamp"])

            if conv_time < cutoff_time:
                break  # Too old

            # Check if this conversation involved the file
            if file_path.lower() in conv["user_input"].lower():
                return True

        return False
