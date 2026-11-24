from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from rich.table import Table

from agent_octopus.models import ComCommand
from agent_octopus.cli import render_grouped_commands_table, OctoCommandCompleter


def sample_commands() -> list[ComCommand]:
    return [
        ComCommand(
            index=1,
            name="$$add_research",
            raw_name="add_research",
            category="research",
            args="[text]",
            description="Save note",
        ),
        ComCommand(
            index=2,
            name="$$commands",
            raw_name="commands",
            category="help",
            args="-",
            description="List commands",
        ),
        ComCommand(
            index=3,
            name="$$god_find",
            raw_name="god_find",
            category="mythology",
            args="<name>",
            description="Find god",
        ),
        ComCommand(
            index=4,
            name="$$god_save_research",
            raw_name="god_save_research",
            category="mythology",
            args="[god name]",
            description="Save god research",
        ),
        ComCommand(
            index=5,
            name="$$leads_get",
            raw_name="leads_get",
            category="crm",
            args="-",
            description="Get leads",
        ),
    ]


def test_render_grouped_commands_table():
    cmds = sample_commands()
    table = render_grouped_commands_table(cmds)

    assert isinstance(table, Table)
    assert "Available Commands" in str(table.title)
    # Check that columns are properly configured
    col_names = [col.header for col in table.columns]
    assert "#" in col_names
    assert "Command Name" in col_names
    assert "Args" in col_names
    assert "Description" in col_names


def test_octo_command_completer_prefix_dollar():
    cmds = sample_commands()
    completer = OctoCommandCompleter(cmds)

    # When user types '$', should complete all commands
    doc = Document("$", cursor_position=1)
    event = CompleteEvent(completion_requested=False)
    completions = list(completer.get_completions(doc, event))

    assert len(completions) == 5
    assert completions[0].text == "$$add_research "
    assert "[research]" in completions[0].display_meta_text
    assert "[help]" in completions[1].display_meta_text


def test_octo_command_completer_filter():
    cmds = sample_commands()
    completer = OctoCommandCompleter(cmds)

    # When user types '$$god', should match only mythology god commands
    doc = Document("$$god", cursor_position=5)
    event = CompleteEvent(completion_requested=False)
    completions = list(completer.get_completions(doc, event))

    assert len(completions) == 2
    assert completions[0].text == "$$god_find "
    assert completions[1].text == "$$god_save_research "


def test_octo_command_completer_tab_requested():
    cmds = sample_commands()
    completer = OctoCommandCompleter(cmds)

    # When user presses Tab on an empty input
    doc = Document("", cursor_position=0)
    event = CompleteEvent(completion_requested=True)
    completions = list(completer.get_completions(doc, event))

    assert len(completions) == 5


def test_octo_command_completer_normal_text_ignored():
    cmds = sample_commands()
    completer = OctoCommandCompleter(cmds)

    # When user types ordinary text without '$' and without pressing Tab
    doc = Document("please draft an article", cursor_position=23)
    event = CompleteEvent(completion_requested=False)
    completions = list(completer.get_completions(doc, event))

    # Should not trigger completion
    assert len(completions) == 0
