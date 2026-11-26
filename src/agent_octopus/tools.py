import html
import json
from contextlib import contextmanager
from typing import Any
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
            buf.insert_text(chosen.raw_text or chosen.action_text)
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


def parse_options_input(options: list[str] | str | None) -> list[str] | None:
    """
    Safely parses and normalizes option inputs for the question tool.
    Accepts native list of strings, JSON-encoded array strings, comma-separated strings,
    or newline-separated lists.
    """
    if options is None:
        return None

    if isinstance(options, list):
        cleaned = [str(opt).strip() for opt in options if str(opt).strip()]
        return cleaned or None

    if isinstance(options, str):
        stripped = options.strip()
        if not stripped:
            return None

        # 1. Attempt JSON deserialization
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    cleaned = [str(opt).strip() for opt in parsed if str(opt).strip()]
                    return cleaned or None
            except Exception:
                pass

        # 2. Check newline-delimited options
        if "\n" in stripped:
            lines = [
                line.strip().lstrip("-*0123456789.) ").strip()
                for line in stripped.splitlines()
            ]
            cleaned = [l for l in lines if l]
            if cleaned:
                return cleaned

        # 3. Check comma-delimited options
        if "," in stripped:
            parts = [p.strip().strip("'\"") for p in stripped.split(",")]
            cleaned = [p for p in parts if p]
            if cleaned:
                return cleaned

        # Fallback single scalar string
        return [stripped.strip("'\"")]

    return None


@contextmanager
def pause_status(ctx_session: SessionContext):
    """
    Temporarily pauses all active Rich status spinners in ctx_session.active_statuses,
    clearing them from the terminal display during user interaction, and resumes them on exit.
    """
    active = getattr(ctx_session, "active_statuses", [])
    for status in active:
        try:
            status.stop()
        except Exception:
            pass
    try:
        yield
    finally:
        for status in active:
            try:
                status.start()
            except Exception:
                pass


@contextmanager
def track_status(session: SessionContext, message: str):
    """
    Context manager that displays a Rich status spinner while registering it in
    session.active_statuses so nested interactive prompts can cleanly pause it.
    """
    status = session.console.status(message)
    if hasattr(session, "active_statuses"):
        session.active_statuses.append(status)
    try:
        with status:
            yield status
    finally:
        if hasattr(session, "active_statuses") and status in session.active_statuses:
            session.active_statuses.remove(status)


def make_options_key_bindings(options: list[str], state: dict) -> KeyBindings:
    """
    Creates prompt_toolkit KeyBindings allowing Up/Down arrow selection
    through options, Enter to prefill the selected option into the prompt buffer,
    or typing to start custom dialogue.
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
            buf.insert_text(chosen)
            state["loaded"] = True
            state["dismissed"] = True
            event.app.invalidate()
        else:
            buf.validate_and_handle()

    @kb.add("escape")
    def _esc(event):
        state["dismissed"] = True
        event.app.invalidate()

    return kb


def make_options_bottom_toolbar(options: list[str], state: dict):
    """
    Renders the options in the bottom toolbar when buffer is empty.
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
            "<b>Options</b> (Use ↑/↓ to navigate, Enter to load choice, or type directly):"
        ]
        for i, opt in enumerate(options):
            escaped = html.escape(opt)
            if i == idx:
                lines.append(f" <b><ansicyan>&gt; {i + 1}. {escaped}</ansicyan></b>")
            else:
                lines.append(f"   <ansigray>{i + 1}. {escaped}</ansigray>")
        return HTML("\n".join(lines))

    return bottom_toolbar


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

    with pause_status(ctx_session):
        console.print(Panel(question_text, title="Agent Question", border_style="bold magenta"))

        if options:
            table = Table(title="Please select an option", show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=4)
            table.add_column("Option", style="bold yellow")
            for i, opt in enumerate(options, start=1):
                table.add_row(str(i), str(opt))
            console.print(table)

            state = {"selected_index": 0, "loaded": False, "dismissed": False}
            kb = make_options_key_bindings(options, state)
            toolbar = make_options_bottom_toolbar(options, state)

            user_input = (await prompt_session.prompt_async(
                "Your choice: ",
                key_bindings=kb,
                bottom_toolbar=toolbar,
            )).strip()

            # If user picked a number, map it back to the option text if valid
            if user_input.isdigit():
                idx = int(user_input)
                if 1 <= idx <= len(options):
                    return options[idx - 1]
            return user_input
        else:
            user_input = (await prompt_session.prompt_async("Your answer: ")).strip()
            return user_input

