import asyncio
import sys
import argparse
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

from agent_octopus.config import load_settings, get_model
from agent_octopus.models import SessionContext
from agent_octopus.com_cli import run_com_list
from agent_octopus.orchestrator import create_orchestrator_agent


async def async_main():
    parser = argparse.ArgumentParser(description="Octopus Multi-Agent CLI")
    parser.add_argument("--model", type=str, help="Override OLLAMA_MODEL")
    parser.add_argument("--api-base", type=str, help="Override OLLAMA_API_BASE")
    parser.add_argument("--mcp-config", type=str, help="Override MCP_CONFIG_PATH")
    parser.add_argument("-c", "--once", type=str, help="Run single command and exit")
    args = parser.parse_args()

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

    session = SessionContext(
        settings=settings,
        console=console,
        commands=parsed_cmds,
    )

    model = get_model(settings)
    orchestrator = create_orchestrator_agent(model=model)

    # Prepare startup turn prompt
    startup_prompt = (
        f"The CLI just started. Here is the raw output from `com list`:\n\n"
        f"```text\n{raw_list}\n```\n\n"
        f"Please format this into a clean, numbered list (1..{len(parsed_cmds)}) showing the command name, "
        f"args, and description, and ask the user what they would like to do."
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
    prompt_session = PromptSession(history=InMemoryHistory())

    while True:
        try:
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
        except Exception as e:
            console.print(f"[bold red]Error during agent execution:[/bold red] {e}")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
