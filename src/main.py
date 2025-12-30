"""Interactive CLI for PowerShell command execution system."""

import asyncio
import logging
from datetime import datetime
from uuid import uuid4
from typing import Optional
from rich.prompt import Prompt, Confirm

from config.settings import settings
from graph.workflow import create_workflow
from graph.state import CommandState
from utils.logger import setup_logging
from utils.cli_helpers import (
    console,
    display_welcome,
    display_command_for_confirmation,
    display_execution_results,
    display_analysis_results,
    display_error,
    display_goodbye
)
from security.sanitizer import sanitize_user_input
from utils.conversation_memory import ConversationMemory

# Audio/Voice imports (optional)
try:
    from tools.audio_recorder import AudioRecorder, AUDIO_AVAILABLE
    from tools.whisper_transcriber import WhisperTranscriber
    VOICE_ENABLED = AUDIO_AVAILABLE and settings.enable_voice_input
except ImportError:
    VOICE_ENABLED = False
    AudioRecorder = None
    WhisperTranscriber = None


class PowerShellCLI:
    """
    Interactive CLI for PowerShell command execution system.
    """

    def __init__(self):
        """Initialize the CLI."""
        self.workflow = create_workflow()
        self.session_id = str(uuid4())
        setup_logging(settings.log_level, settings.log_file)
        self.logger = logging.getLogger(__name__)

        # Initialize conversation memory
        self.memory_enabled = settings.enable_conversation_memory
        if self.memory_enabled:
            try:
                self.conversation_memory = ConversationMemory(
                    max_conversations=settings.max_conversations_in_memory,
                    storage_file=settings.memory_storage_file,
                    enable_persistence=True
                )
                self.logger.info(f"Conversation memory enabled ({settings.max_conversations_in_memory} conversations)")
            except Exception as e:
                self.logger.warning(f"Conversation memory disabled: {e}")
                self.memory_enabled = False
                self.conversation_memory = None
        else:
            self.conversation_memory = None

        # Initialize voice components if available
        self.voice_enabled = VOICE_ENABLED
        if self.voice_enabled:
            try:
                self.audio_recorder = AudioRecorder(
                    sample_rate=settings.audio_sample_rate,
                    channels=settings.audio_channels,
                    silence_threshold=settings.silence_threshold,
                    auto_stop_silence_duration=settings.auto_stop_silence_duration
                )
                self.transcriber = WhisperTranscriber(
                    api_key=settings.openai_api_key,
                    model=settings.whisper_model,
                    use_local=settings.use_local_whisper
                )
                self.logger.info("Voice input enabled")
            except Exception as e:
                self.logger.warning(f"Voice input disabled: {e}")
                self.voice_enabled = False
        else:
            self.audio_recorder = None
            self.transcriber = None

    def display_conversation_history(self) -> None:
        """Display conversation history from memory."""
        if not self.memory_enabled:
            console.print("[yellow]Conversation memory is not enabled[/yellow]")
            return

        history = self.conversation_memory.get_conversation_history()

        if not history:
            console.print("[dim]No conversation history available[/dim]")
            return

        console.print(f"\n[bold cyan]📜 Conversation History ({len(history)} conversations):[/bold cyan]\n")

        from rich.table import Table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Timestamp", width=20)
        table.add_column("User Input", width=40)
        table.add_column("Command", width=30)
        table.add_column("Status", width=10)

        for i, conv in enumerate(history, 1):
            timestamp = conv["timestamp"][:19]  # Remove microseconds
            user_input = conv["user_input"][:37] + "..." if len(conv["user_input"]) > 40 else conv["user_input"]
            command = conv.get("generated_command", "N/A")
            command = command[:27] + "..." if command and len(command) > 30 else command or "N/A"

            # Status
            exec_result = conv.get("execution_result")
            if exec_result:
                status = "✓" if exec_result.get("status") == 0 else "✗"
            else:
                status = "-"

            table.add_row(str(i), timestamp, user_input, command, status)

        console.print(table)
        console.print()

    async def get_voice_input(self) -> Optional[str]:
        """
        Record audio and transcribe to text.

        Returns:
            Transcribed text or None if failed
        """
        if not self.voice_enabled:
            console.print("[yellow]Voice input is not available[/yellow]")
            return None

        try:
            # Status callback for recording
            def status_callback(message):
                console.print(f"[cyan]{message}[/cyan]")

            # Record audio
            console.print("\n[bold green]🎙️  Voice Mode Activated[/bold green]")
            console.print("[dim]Speak your command (will auto-stop on silence)...[/dim]")

            audio_file = await self.audio_recorder.record_until_silence(
                max_duration=settings.recording_duration,
                callback=status_callback
            )

            if not audio_file:
                console.print("[yellow]No audio recorded[/yellow]")
                return None

            # Transcribe audio
            console.print("[cyan]🔄 Transcribing...[/cyan]")
            result = await self.transcriber.transcribe_file(audio_file)

            transcribed_text = result["text"]
            console.print(f"\n[bold green]✓ Transcribed:[/bold green] {transcribed_text}\n")

            return transcribed_text

        except Exception as e:
            self.logger.error(f"Voice input failed: {e}")
            console.print(f"[red]Voice input error: {str(e)}[/red]")
            return None

    async def run_interactive_loop(self):
        """Main interactive loop."""

        display_welcome()

        # Show voice input availability
        if self.voice_enabled:
            console.print("[green]🎤 Voice input enabled! Type '/voice' to use voice[/green]")
        else:
            console.print("[dim]Voice input not available (install: pip install sounddevice soundfile numpy)[/dim]")

        # Show memory status
        if self.memory_enabled:
            summary = self.conversation_memory.get_summary()
            console.print(f"[green]💾 Conversation memory enabled ({summary['total_conversations']}/{summary['max_capacity']} conversations stored)[/green]")

        console.print("\n[dim]Special commands: /voice, /history, /clear, exit[/dim]")

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]Enter command request[/bold cyan]")

                if user_input.lower() in ["exit", "quit", "q"]:
                    display_goodbye()
                    break

                # Check for voice command
                if user_input.lower() in ["/voice", "/v", "voice"]:
                    if not self.voice_enabled:
                        console.print("[yellow]Voice input is not available[/yellow]")
                        continue

                    user_input = await self.get_voice_input()
                    if not user_input:
                        continue

                # Check for history command
                if user_input.lower() in ["/history", "/h", "history"]:
                    self.display_conversation_history()
                    continue

                # Check for clear history command
                if user_input.lower() in ["/clear", "/c", "clear"]:
                    if self.memory_enabled:
                        self.conversation_memory.clear_memory()
                        console.print("[green]✓ Conversation history cleared[/green]")
                    else:
                        console.print("[yellow]Conversation memory is not enabled[/yellow]")
                    continue

                # Sanitize and validate input
                user_input = sanitize_user_input(user_input)
                if not user_input:
                    console.print("[yellow]Please enter a valid command request.[/yellow]")
                    continue

                # Run workflow
                await self.execute_workflow(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
                continue
            except Exception as e:
                self.logger.exception("Unexpected error in interactive loop")
                display_error(f"Unexpected error: {str(e)}")

    async def execute_workflow(self, user_input: str):
        """
        Execute the LangGraph workflow for a single command.

        Args:
            user_input: User's natural language request
        """

        # Get conversation history context if enabled
        conversation_messages = []
        if self.memory_enabled and settings.include_context_in_prompt:
            conversation_messages = self.conversation_memory.get_context_messages(
                include_last_n=settings.context_conversations_count
            )
            if conversation_messages:
                self.logger.debug(f"Using {len(conversation_messages)} conversation messages as context")

        # Initialize state
        initial_state: CommandState = {
            "user_input": user_input,
            "session_id": self.session_id,
            "timestamp": datetime.now(),
            "generated_command": None,
            "command_explanation": None,
            "safety_assessment": None,
            "shell_type": "powershell",  # Start with PowerShell
            "attempted_shells": [],
            "user_confirmed": None,
            "confirmation_timestamp": None,
            "user_feedback": None,
            "execution_status": "pending",
            "execution_result": None,
            "execution_timestamp": None,
            "validation_passed": None,
            "validation_reasoning": None,
            "validation_suggestions": None,
            "requires_analysis": None,
            "analysis_type": None,
            "analysis_target": None,
            "analysis_result": None,
            "content_to_analyze": None,
            "error_message": None,
            "error_type": None,
            "retry_count": 0,
            "max_retries": settings.max_retries,
            "messages": [],
            "execution_history": [],
            "conversation_messages": conversation_messages,  # Add conversation context
            "next_step": "generate"
        }

        # Configuration for workflow
        config = {"configurable": {"thread_id": self.session_id}}

        try:
            # Start the workflow
            stream_mode = initial_state

            while True:
                interrupted = False

                # Execute workflow with interrupt handling
                async for event in self.workflow.astream(stream_mode, config):
                    # Handle interrupt for confirmation
                    if "__interrupt__" in event:
                        interrupted = True
                        # Get current state
                        current_state = await self.workflow.aget_state(config)
                        state_data = current_state.values

                        # Display command for confirmation
                        display_command_for_confirmation(state_data)

                        # Get user confirmation
                        confirmed = Confirm.ask(
                            "[bold]Execute this command?[/bold]",
                            default=False
                        )

                        feedback = None
                        if not confirmed:
                            feedback = Prompt.ask(
                                "Feedback for improvement (optional, or press Enter to skip)",
                                default=""
                            )

                        # Resume workflow with user response
                        await self.workflow.aupdate_state(
                            config,
                            {
                                "user_confirmed": confirmed,
                                "user_feedback": feedback if feedback else None,
                                "confirmation_timestamp": datetime.now()
                            }
                        )

                        # Break to resume from None
                        break

                # If interrupted, resume from checkpoint
                if interrupted:
                    stream_mode = None
                else:
                    # Workflow completed, exit loop
                    break

            # Get final state
            final_state = await self.workflow.aget_state(config)

            # Save conversation to memory
            if self.memory_enabled:
                try:
                    self.conversation_memory.add_conversation(
                        user_input=user_input,
                        generated_command=final_state.values.get("generated_command"),
                        execution_result=final_state.values.get("execution_result"),
                        analysis_result=final_state.values.get("analysis_result"),
                        metadata={
                            "shell_type": final_state.values.get("shell_type"),
                            "validation_passed": final_state.values.get("validation_passed"),
                            "requires_analysis": final_state.values.get("requires_analysis")
                        }
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to save conversation to memory: {e}")

            # Display results
            if final_state.values.get("analysis_result"):
                # Display analysis results first
                display_analysis_results(final_state.values)

            if final_state.values.get("execution_result"):
                display_execution_results(final_state.values)
            elif final_state.values.get("error_message"):
                display_error(final_state.values["error_message"])

        except Exception as e:
            self.logger.exception(f"Workflow execution failed: {e}")
            display_error(f"Workflow execution failed: {str(e)}")


async def main():
    """Entry point."""
    cli = PowerShellCLI()
    await cli.run_interactive_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! 👋[/yellow]")
    except Exception as e:
        console.print(f"\n[red bold]Fatal error:[/red bold] {str(e)}")
        logging.getLogger(__name__).exception("Fatal error")
