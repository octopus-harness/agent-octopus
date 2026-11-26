import html
from prompt_toolkit import PromptSession
from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from rich.panel import Panel
from rich.table import Table

from agent_octopus.models import SessionContext
from agent_octopus.com_cli import run_com_list, run_com_get
from agent_octopus.plan_parser import PlanOption


def make_plan_key_bindings(options: list[PlanOption], state: dict) -> KeyBindings:
    """
    Creates prompt_toolkit KeyBindings allowing Up/Down arrow selection
    through plan options, Enter to prefill the selected action, or typing
    to start custom dialogue.
    """
    kb = KeyBindings()

    @kb.add("up")
    def _up(event):
        buf = event.current_buffer
        if not buf.text and not state.get("dismissed"):
            current = state.get("selected_index", 0)
            state["selected_index"] = (current - 1) % len(options)
            event.app.invalidate()
        else:
            buf.history_backward()

    @kb.add("down")
    def _down(event):
        buf = event.current_buffer
        if not buf.text and not state.get("dismissed"):
            current = state.get("selected_index", 0)
            state["selected_index"] = (current + 1) % len(options)
            event.app.invalidate()
        else:
            buf.history_forward()

    @kb.add("enter")
    def _enter(event):
        buf = event.current_buffer
        idx = state.get("selected_index")
        # If user hasn't typed anything and an option is active, load it into buffer for review
        if not buf.text and idx is not None and not state.get("loaded") and not state.get("dismissed"):
            chosen = options[idx]
            buf.insert_text(chosen.action_text)
            state["loaded"] = True
            state["dismissed"] = True
            event.app.invalidate()
        else:
            # Normal enter accepts buffer
            buf.validate_and_handle()

    @kb.add("escape")
    def _esc(event):
        state["dismissed"] = True
        event.app.invalidate()

    return kb


def make_plan_bottom_toolbar(options: list[PlanOption], state: dict):
    """
    Renders the plan options in the bottom toolbar when buffer is empty.
    Hides automatically once user starts typing.
    """
    def bottom_toolbar():
        try:
            buf = get_app().current_buffer
            if buf and buf.text:
                return None
        except Exception:
            pass

        idx = state.get("selected_index")
        if idx is None or state.get("dismissed"):
            return None

        lines = [
            "<b>Recommended Plan</b> (Use ↑/↓ to navigate, Enter to load action, or type directly to dialogue):"
        ]
        for i, opt in enumerate(options):
            escaped_label = html.escape(opt.label)
            if i == idx:
                lines.append(f" <b><ansicyan>&gt; {escaped_label}</ansicyan></b>")
            else:
                lines.append(f"   <ansigray>{escaped_label}</ansigray>")
        return HTML("\n".join(lines))

    return bottom_toolbar


async def prompt_with_plan_selector(
    prompt_session: PromptSession,
    prompt_text: str,
    options: list[PlanOption],
) -> str:
    """
    Displays prompt_text with an interactive plan selector.
    Navigating with Up/Down and pressing Enter loads the action into the prompt buffer.
    Typing any character transitions to normal text input for free-form dialogue.
    """
    if not options:
        return await prompt_session.prompt_async(prompt_text)

    state = {"selected_index": 0, "loaded": False, "dismissed": False}
    kb = make_plan_key_bindings(options, state)
    toolbar = make_plan_bottom_toolbar(options, state)

    return await prompt_session.prompt_async(
        prompt_text,
        key_bindings=kb,
        bottom_toolbar=toolbar,
    )


async def ask_user_interactive(
    ctx_session: SessionContext,
    question_text: str,
    options: list[str] | None = None,
) -> str:
    """
    Renders an interactive terminal prompt to ask the user a question
    and returns their input asynchronously.
    """
    console = ctx_session.console
    prompt_session: PromptSession = PromptSession()

    if options:
        table = Table(title="Please select an option", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Option", style="bold yellow")
        for i, opt in enumerate(options, start=1):
            table.add_row(str(i), str(opt))

        console.print(Panel(question_text, title="Agent Question", border_style="bold magenta"))
        console.print(table)

        user_input = (await prompt_session.prompt_async("Your choice: ")).strip()
        # If user picked a number, map it back to the option text if valid
        if user_input.isdigit():
            idx = int(user_input)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        return user_input
    else:
        console.print(Panel(question_text, title="Agent Question", border_style="bold magenta"))
        user_input = (await prompt_session.prompt_async("Your answer: ")).strip()
        return user_input
