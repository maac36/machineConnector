"""CLI utility functions for formatting and display."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from typing import Dict, Any


console = Console()


def display_welcome():
    """Display welcome message."""
    welcome_text = """[bold]PowerShell Command Assistant[/bold]

Convert natural language to PowerShell commands with AI assistance.

[cyan]Examples:[/cyan]
• "search for abc.txt on my C: drive"
• "launch notepad"
• "show me running processes using more than 100MB RAM"
• "read config.json and explain what it does"

[dim]Special Commands:[/dim]
• /voice - Voice input  • /history - View history  • /clear - Clear history

Type [bold]'exit'[/bold] or [bold]'quit'[/bold] to end session.
"""
    console.print(Panel(welcome_text, border_style="blue", padding=(1, 2)))


def display_command_for_confirmation(state: Dict[str, Any]) -> None:
    """
    Display generated command and prompt for confirmation.

    Args:
        state: Current command state
    """
    console.print("\n[bold cyan]Generated Command:[/bold cyan]")

    # Syntax highlighted PowerShell code
    syntax = Syntax(
        state["generated_command"],
        "powershell",
        theme="monokai",
        line_numbers=False,
        padding=(1, 2)
    )
    console.print(syntax)

    console.print(f"[bold]Explanation:[/bold] {state['command_explanation']}\n")

    # Safety information
    safety = state["safety_assessment"]
    if safety["level"] == "dangerous":
        console.print("[red bold]⚠️  DANGER: This command has been blocked![/red bold]")
        for warning in safety["warnings"]:
            console.print(f"  [red]• {warning}[/red]")
        console.print()
    elif safety["level"] == "suspicious":
        console.print("[yellow bold]⚠️  Caution:[/yellow bold]")
        for warning in safety["warnings"]:
            console.print(f"  [yellow]• {warning}[/yellow]")
        console.print()
    elif safety["warnings"]:
        for warning in safety["warnings"]:
            console.print(f"  [dim]• {warning}[/dim]")
        console.print()


def display_execution_results(state: Dict[str, Any]) -> None:
    """
    Display execution results and validation.

    Args:
        state: Final command state
    """
    result = state.get("execution_result", {})

    # Status
    status = state.get("execution_status", "unknown")
    if status == "success":
        status_color = "green"
        status_icon = "✓"
    elif status == "failed":
        status_color = "yellow"
        status_icon = "⚠"
    else:
        status_color = "red"
        status_icon = "✗"

    console.print(f"\n[{status_color} bold]{status_icon} Execution Status:[/{status_color} bold] [{status_color}]{status.upper()}[/{status_color}]")
    console.print(f"[bold]Return Code:[/bold] {result.get('return_code', 'N/A')}")
    console.print(f"[bold]Execution Time:[/bold] {result.get('execution_time', 0):.2f}s\n")

    # Output
    stdout = result.get("stdout", "")
    if stdout:
        console.print("[bold]Output:[/bold]")
        console.print(Panel(stdout.strip(), border_style="green", padding=(1, 2)))

    # Errors/Warnings
    stderr = result.get("stderr", "")
    if stderr:
        console.print("[bold]Errors/Warnings:[/bold]")
        console.print(Panel(stderr.strip(), border_style="red", padding=(1, 2)))

    # Validation
    if state.get("validation_passed") is not None:
        validation_passed = state["validation_passed"]
        validation_color = "green" if validation_passed else "yellow"
        validation_icon = "✓" if validation_passed else "⚠"
        validation_status = "PASSED" if validation_passed else "NEEDS REVIEW"

        console.print(f"\n[{validation_color} bold]{validation_icon} Validation:[/{validation_color} bold] [{validation_color}]{validation_status}[/{validation_color}]")
        console.print(f"[dim]{state.get('validation_reasoning', '')}[/dim]")

        suggestions = state.get("validation_suggestions", [])
        if suggestions:
            console.print("\n[bold]Suggestions:[/bold]")
            for suggestion in suggestions:
                console.print(f"  [cyan]•[/cyan] {suggestion}")

    console.print()


def display_error(error_message: str) -> None:
    """
    Display error message.

    Args:
        error_message: Error message to display
    """
    console.print(f"\n[red bold]Error:[/red bold] {error_message}\n")


def display_analysis_results(state: Dict[str, Any]) -> None:
    """
    Display content analysis results.

    Args:
        state: Final command state with analysis results
    """
    analysis_result = state.get("analysis_result")

    if not analysis_result:
        return

    console.print("\n[bold cyan]📊 Analysis Results:[/bold cyan]\n")

    # Display analysis metadata
    analysis_type = analysis_result.get("analysis_type", "general")
    analysis_target = state.get("analysis_target")

    if analysis_target:
        console.print(f"[bold]Target:[/bold] {analysis_target}")

    console.print(f"[bold]Analysis Type:[/bold] {analysis_type.replace('_', ' ').title()}\n")

    # Display the analysis content
    analysis_content = analysis_result.get("analysis", "")

    if analysis_content:
        # Pretty print the analysis in a panel
        console.print(Panel(
            analysis_content,
            title="[bold green]LLM Analysis[/bold green]",
            border_style="cyan",
            padding=(1, 2)
        ))

    # Additional metadata
    if "tokens_used" in analysis_result:
        console.print(f"\n[dim]Tokens used: {analysis_result['tokens_used']}[/dim]")

    if "files_analyzed" in analysis_result:
        console.print(f"[dim]Files analyzed: {analysis_result['files_analyzed']}[/dim]")

    console.print()


def display_goodbye() -> None:
    """Display goodbye message."""
    console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
