import asyncio
import sys
import argparse
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.markup import escape
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from agent_octopus.config import load_settings, get_model
from agent_octopus.models import SessionContext, ComCommand
from agent_octopus.com_cli import run_com_list, category_sort_key
from agent_octopus.orchestrator import create_orchestrator_agent
from agent_octopus.observability import setup_observability
from agent_octopus.plan_parser import extract_plan_options, PlanOption
from agent_octopus.tools import prompt_with_plan_selector


CATEGORY_HEADER_STYLE: str = "bold magenta"


def render_grouped_commands_table(commands: list[ComCommand]) -> Table:
    """
    Renders a unified Rich Table grouping commands by category with uniform
    colored category section header rows, aligned columns, and sequential numbering.
    """
    table = Table(
        title="🐙 Octopus CLI - Available Commands",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim",
        expand=True,
    )
    table.add_column("#", style="dim cyan", width=4, justify="right")
    table.add_column("Command Name", style="bold cyan", width=22)
    table.add_column("Args", style="green", width=14)
    table.add_column("Description", style="white")

    # Group commands by category
    categories: dict[str, list[ComCommand]] = {}
    for cmd in commands:
        categories.setdefault(cmd.category, []).append(cmd)

    # Ensure 'General' category is always at the top and 'Help' is always at the bottom
    sorted_cat_names = sorted(categories.keys(), key=category_sort_key)

    first = True
    for cat in sorted_cat_names:
        cat_cmds = categories[cat]
        if not first:
            table.add_section()
        first = False
        table.add_row(
            "",
            f"[{CATEGORY_HEADER_STYLE}]{cat.upper()}[/{CATEGORY_HEADER_STYLE}]",
            "",
            "",
        )
        for cmd in cat_cmds:
            table.add_row(
                str(cmd.index),
                escape(cmd.name),
                escape(cmd.args.strip("`")),
                escape(cmd.description),
            )

    return table


class OctoCommandCompleter(Completer):
    """
    Interactive popup completer for prompt_toolkit.
    Prefix-triggered: triggers when typing '$' or explicitly pressing Tab,
    matching against available command names and showing category badges.
    """

    def __init__(self, commands: list[ComCommand]):
        self.commands = commands

    def get_completions(self, document: Document, complete_event):
        word = document.get_word_before_cursor(WORD=True)
        is_tab = complete_event.completion_requested
        is_dollar_prefix = word.startswith("$")

        if not (is_tab or is_dollar_prefix):
            return

        query = word.lower()
        for cmd in self.commands:
            if not query or query in cmd.name.lower() or query in cmd.raw_name.lower():
                display_meta = f"[{cmd.category}] {cmd.args} — {cmd.description}"
                start_pos = -len(word) if word else 0
                yield Completion(
                    text=f"{cmd.name} ",
                    start_position=start_pos,
                    display=cmd.name,
                    display_meta=display_meta,
                )


async def async_main():
    parser = argparse.ArgumentParser(description="Octopus Multi-Agent CLI")
    parser.add_argument("--model", type=str, help="Override OLLAMA_MODEL")
    parser.add_argument("--api-base", type=str, help="Override OLLAMA_API_BASE")
    parser.add_argument("--mcp-config", type=str, help="Override MCP_CONFIG_PATH")
    parser.add_argument("-c", "--once", type=str, help="Run single command and exit")
    parser.add_argument(
        "--logfire-console",
        action="store_true",
        help="Display live Logfire spans in the terminal console",
    )
    args = parser.parse_args()

    setup_observability(console=True if args.logfire_console else None)

    settings = load_settings()
    if args.model:
        settings.ollama_model = args.model
    if args.api_base:
        settings.ollama_api_base = args.api_base
    if args.mcp_config:
        settings.mcp_config_path = args.mcp_config

    console = Console()
    console.print(
        Panel.fit(
            f"[bold cyan]🐙 Agent Octopus[/bold cyan]\n"
            f"[dim]Model: {settings.ollama_model} @ {settings.ollama_api_base}[/dim]",
            border_style="cyan",
        )
    )

    # 1. First thing: execute `com list`
    try:
        raw_list, parsed_cmds = run_com_list(com_bin=settings.com_bin)
    except Exception as e:
        console.print(f"[bold red]Error running com list:[/bold red] {e}")
        sys.exit(1)

    # Display grouped commands table directly
    console.print()
    console.print(render_grouped_commands_table(parsed_cmds))
    console.print()

    session = SessionContext(
        settings=settings,
        console=console,
        commands=parsed_cmds,
    )

    model = get_model(settings)
    orchestrator = create_orchestrator_agent(model=model)

    # Prepare startup turn prompt
    startup_prompt = (
        f"The CLI just started. The available commands grouped by category have already been rendered in a table for the user:\n\n"
        f"```text\n{raw_list}\n```\n\n"
        f"Briefly acknowledge the session start (in 1-2 friendly sentences) and ask the user what they would like to do."
    )

    message_history = []

    with console.status("[bold green]Loading commands and preparing agent menu...[/bold green]"):
        startup_res = await orchestrator.run(
            startup_prompt,
            deps=session,
            message_history=message_history,
        )
        message_history = startup_res.all_messages()

    console.print()
    console.print(Markdown(str(startup_res.output)))
    console.print()

    # If single shot execution was requested via -c / --once
    if args.once:
        with console.status("[bold green]Agent thinking...[/bold green]"):
            res = await orchestrator.run(
                args.once,
                deps=session,
                message_history=message_history,
            )
        console.print()
        console.print(Markdown(str(res.output)))
        console.print()
        return

    # 2. Interactive REPL Loop
    completer = OctoCommandCompleter(session.commands)
    prompt_style = Style.from_dict({
        "completion-menu.completion": "bg:#262626 #e0e0e0",
        "completion-menu.completion.current": "bg:#005f87 #ffffff bold",
        "completion-menu.meta.completion": "bg:#1a1a1a #9e9e9e italic",
        "completion-menu.meta.completion.current": "bg:#004060 #5fd7ff bold",
    })
    prompt_session = PromptSession(
        history=InMemoryHistory(),
        completer=completer,
        complete_while_typing=True,
        style=prompt_style,
    )

    active_plan_options: list[PlanOption] = []

    while True:
        try:
            if active_plan_options:
                user_input = (await prompt_with_plan_selector(
                    prompt_session,
                    "🐙 octo > ",
                    active_plan_options,
                )).strip()
                active_plan_options = []
            else:
                user_input = (await prompt_session.prompt_async("🐙 octo > ")).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting Agent Octopus. Goodbye![/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        # Check if user input is an index number or index + args (e.g. "4", "4 Zeus")
        parts = user_input.split(maxsplit=1)
        if parts[0].isdigit():
            idx = int(parts[0])
            matched_cmd = next((c for c in session.commands if c.index == idx), None)
            if matched_cmd:
                extra_args = parts[1] if len(parts) > 1 else ""
                enriched_input = (
                    f"The user selected option {idx} ({matched_cmd.name}). "
                    f"Additional arguments provided by user: '{extra_args}'."
                )
                console.print(f"[dim]Mapped choice #{idx} to {matched_cmd.name}[/dim]")
                user_input = enriched_input

        try:
            with console.status("[bold green]Agent thinking...[/bold green]"):
                result = await orchestrator.run(
                    user_input,
                    deps=session,
                    message_history=message_history,
                )
                message_history = result.all_messages()

            console.print()
            console.print(Markdown(str(result.output)))
            console.print()

            # Check if output contains a plan to offer in the next prompt turn
            active_plan_options = extract_plan_options(str(result.output))
        except Exception as e:
            console.print(f"[bold red]Error during agent execution:[/bold red] {e}")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
