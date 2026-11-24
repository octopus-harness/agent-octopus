from prompt_toolkit import prompt
from rich.panel import Panel
from rich.table import Table

from agent_octopus.models import SessionContext
from agent_octopus.com_cli import run_com_list, run_com_get


def ask_user_interactive(
    ctx_session: SessionContext,
    question_text: str,
    options: list[str] | None = None,
) -> str:
    """
    Renders an interactive terminal prompt to ask the user a question
    and returns their input.
    """
    console = ctx_session.console

    if options:
        table = Table(title="Please select an option", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Option", style="bold yellow")
        for i, opt in enumerate(options, start=1):
            table.add_row(str(i), str(opt))

        console.print(Panel(question_text, title="Agent Question", border_style="bold magenta"))
        console.print(table)

        user_input = prompt("Your choice: ").strip()
        # If user picked a number, map it back to the option text if valid
        if user_input.isdigit():
            idx = int(user_input)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        return user_input
    else:
        console.print(Panel(question_text, title="Agent Question", border_style="bold magenta"))
        user_input = prompt("Your answer: ").strip()
        return user_input
