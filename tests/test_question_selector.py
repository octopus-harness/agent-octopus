import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from rich.console import Console
from prompt_toolkit.key_binding import KeyBindings

from agent_octopus.models import SessionContext
from agent_octopus.config import load_settings
from agent_octopus.tools import (
    parse_options_input,
    pause_status,
    track_status,
    make_options_key_bindings,
    make_options_bottom_toolbar,
    ask_user_interactive,
)


def test_parse_options_input_variants():
    # 1. Native list of strings
    assert parse_options_input(["Coaching backlog", "Recruiting backlog"]) == [
        "Coaching backlog",
        "Recruiting backlog",
    ]

    # 2. JSON-encoded array string (the bug from the logfire trace!)
    assert parse_options_input('["Coaching backlog", "Recruiting backlog"]') == [
        "Coaching backlog",
        "Recruiting backlog",
    ]

    # 3. Comma-separated string
    assert parse_options_input("Coaching backlog, Recruiting backlog") == [
        "Coaching backlog",
        "Recruiting backlog",
    ]

    # 4. Newline-separated options with list numbering/bullets
    newline_str = "1. Coaching backlog\n2. Recruiting backlog"
    assert parse_options_input(newline_str) == [
        "Coaching backlog",
        "Recruiting backlog",
    ]

    # 5. Single scalar string
    assert parse_options_input("Coaching backlog") == ["Coaching backlog"]

    # 6. None or empty string
    assert parse_options_input(None) is None
    assert parse_options_input("") is None
    assert parse_options_input("   ") is None
    assert parse_options_input([]) is None


def test_track_and_pause_status():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)

    mock_status = MagicMock()
    with patch.object(console, "status", return_value=mock_status):
        with track_status(session, "Testing spinner"):
            assert mock_status in session.active_statuses
            mock_status.__enter__.assert_called_once()

            # Now verify pause_status stops and restarts it
            with pause_status(session):
                mock_status.stop.assert_called_once()
            mock_status.start.assert_called_once()

        # Once track_status exits, it should be removed from active_statuses
        assert mock_status not in session.active_statuses
        mock_status.__exit__.assert_called_once()


def test_options_key_bindings_navigation_and_enter():
    options = ["Coaching backlog", "Recruiting backlog"]
    state = {"selected_index": 0, "loaded": False, "dismissed": False}
    kb = make_options_key_bindings(options, state)

    # Mock prompt_toolkit event and buffer
    event = MagicMock()
    buf = MagicMock()
    buf.text = ""
    event.current_buffer = buf

    # Test down arrow increments selected_index
    down_handler = kb.get_bindings_for_keys(("down",))[0].handler
    down_handler(event)
    assert state["selected_index"] == 1
    event.app.invalidate.assert_called()

    # Down arrow wraps around
    down_handler(event)
    assert state["selected_index"] == 0

    # Up arrow wraps backwards
    up_handler = kb.get_bindings_for_keys(("up",))[0].handler
    up_handler(event)
    assert state["selected_index"] == 1

    # Enter loads selected option into buffer on first press
    from prompt_toolkit.keys import Keys
    enter_handler = kb.get_bindings_for_keys((Keys.ControlM,))[0].handler
    enter_handler(event)
    buf.insert_text.assert_called_once_with("Recruiting backlog")
    assert state["loaded"] is True
    assert state["dismissed"] is True

    # Next Enter validates and handles buffer
    buf.text = "Recruiting backlog"
    enter_handler(event)
    buf.validate_and_handle.assert_called_once()


def test_options_key_bindings_escape_dismiss():
    options = ["Coaching backlog", "Recruiting backlog"]
    state = {"selected_index": 0, "loaded": False, "dismissed": False}
    kb = make_options_key_bindings(options, state)

    event = MagicMock()
    esc_handler = kb.get_bindings_for_keys(("escape",))[0].handler
    esc_handler(event)
    assert state["dismissed"] is True
    event.app.invalidate.assert_called()


def test_options_bottom_toolbar():
    options = ["Coaching backlog", "Recruiting backlog"]
    state = {"selected_index": 0, "loaded": False, "dismissed": False}
    toolbar_fn = make_options_bottom_toolbar(options, state)

    with patch("agent_octopus.tools.get_app") as mock_get_app:
        mock_app = MagicMock()
        mock_app.current_buffer.text = ""
        mock_get_app.return_value = mock_app

        res = toolbar_fn()
        assert res is not None
        # formatted HTML should contain > 1. Coaching backlog
        assert "&gt; 1. Coaching backlog" in res.value

        # If buffer has text, toolbar hides
        mock_app.current_buffer.text = "Coaching"
        assert toolbar_fn() is None


@pytest.mark.asyncio
async def test_ask_user_interactive_with_options_and_number_selection():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    options = ["Coaching backlog", "Recruiting backlog"]

    with patch("agent_octopus.tools.PromptSession.prompt_async", new=AsyncMock(return_value="2")):
        ans = await ask_user_interactive(session, "Which backlog?", options)
        # "2" maps to options[1] -> "Recruiting backlog"
        assert ans == "Recruiting backlog"

    with patch("agent_octopus.tools.PromptSession.prompt_async", new=AsyncMock(return_value="Coaching backlog")):
        ans = await ask_user_interactive(session, "Which backlog?", options)
        assert ans == "Coaching backlog"


@pytest.mark.asyncio
async def test_question_tool_accepts_json_options_without_validation_error():
    """Verify that the question tool accepts JSON array strings directly without Pydantic AI validation failure."""
    from pydantic_ai import Agent, RunContext
    from agent_octopus.models import SessionContext
    from agent_octopus.specialists.base import SpecialistDefinition

    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)

    test_agent = Agent(
        "test",
        deps_type=SessionContext,
    )

    @test_agent.tool
    async def question(
        sub_ctx: RunContext[SessionContext],
        question_text: str,
        options: list[str] | str | None = None,
    ) -> str:
        parsed_options = parse_options_input(options)
        return f"Asked: {question_text}, Options: {parsed_options}"

    # Simulate tool call with stringified JSON options
    mock_run_ctx = MagicMock()
    mock_run_ctx.deps = session
    result = await question(
        mock_run_ctx,
        question_text="Which backlog?",
        options='["Coaching backlog", "Recruiting backlog"]',
    )
    assert result == "Asked: Which backlog?, Options: ['Coaching backlog', 'Recruiting backlog']"
