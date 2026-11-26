from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from rich.table import Table

from agent_octopus.models import ComCommand
from agent_octopus.plan_parser import PlanOption
from agent_octopus.cli import render_grouped_commands_table, OctoCommandCompleter, resolve_user_input


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


def test_category_ordering_general_first_help_last():
    # Pass commands in arbitrary category order including general and help
    unordered_cmds = [
        ComCommand(index=1, name="$$help", raw_name="help", category="help", args="-", description="Help"),
        ComCommand(index=2, name="$$add_research", raw_name="add_research", category="research", args="-", description="Note"),
        ComCommand(index=3, name="$$readable_summary", raw_name="readable_summary", category="general", args="-", description="Summary"),
        ComCommand(index=4, name="$$leads_get", raw_name="leads_get", category="crm", args="-", description="Leads"),
    ]
    table = render_grouped_commands_table(unordered_cmds)

    # Extract all category header row cells in order of rendering
    category_headers = [str(cell) for cell in table.columns[1]._cells if not str(cell).startswith("$$")]

    assert len(category_headers) == 4
    assert "GENERAL" in category_headers[0]
    assert "HELP" in category_headers[-1]
    # Verify icon was removed and uniform bold magenta color is applied
    for header in category_headers:
        assert "📁" not in header
        assert "bold magenta" in header


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


def test_resolve_user_input_with_active_plan():
    plan_options = [
        PlanOption(
            index=1,
            title="Archetype Clustering",
            tool_name="compute_clusters",
            action_text="Execute plan step 1: Archetype Clustering using compute_clusters",
            label="1. Archetype Clustering (compute_clusters)",
            raw_text="1 Archetype Clustering: compute_clusters(target_type='God', level=5, full_coverage=false) : Group these creator archetypes into connected-component clusters for structural analysis.",
        ),
        PlanOption(
            index=2,
            title="Freeze Cluster Snapshot",
            tool_name="create_cluster_snapshot",
            action_text="Execute plan step 2: Freeze Cluster Snapshot",
            label="2. Freeze Cluster Snapshot (create_cluster_snapshot)",
            raw_text="2 Freeze Cluster Snapshot: create_cluster_snapshot(target_type='God', level=6)",
        ),
    ]
    commands = sample_commands()

    # Selecting '1' must pick the plan option's raw_text, NOT commands[0] ($$add_research / $$content_prompt)
    resolved = resolve_user_input("1", plan_options=plan_options, commands=commands)
    assert resolved == plan_options[0].raw_text
    assert "$$add_research" not in resolved
    assert "$$content_prompt" not in resolved

    # Selecting '1 extra_arg'
    resolved_args = resolve_user_input("1 extra_arg", plan_options=plan_options, commands=commands)
    assert resolved_args == f"{plan_options[0].raw_text} extra_arg"

    # Selecting an out-of-range number (e.g. '9') when plan is active passes through raw input
    resolved_out_of_range = resolve_user_input("9", plan_options=plan_options, commands=commands)
    assert resolved_out_of_range == "9"

    # Input already matching the choice text remains as-is without duplicating
    already_loaded = plan_options[0].raw_text
    resolved_loaded = resolve_user_input(already_loaded, plan_options=plan_options, commands=commands)
    assert resolved_loaded == already_loaded


def test_resolve_user_input_without_active_plan():
    commands = sample_commands()

    # When no plan is active, '1' maps to commands[0] ($$add_research)
    resolved = resolve_user_input("1", plan_options=[], commands=commands)
    assert "The user selected option 1 ($$add_research)" in resolved

    # Non-digit input is untouched
    resolved_text = resolve_user_input("find me a god", plan_options=[], commands=commands)
    assert resolved_text == "find me a god"


def test_resolve_user_input_choice_3_operational_next_steps():
    from agent_octopus.plan_parser import extract_plan_options

    text = """
Operational Next Steps

1 Synthesis Report — create_cluster_report(cluster_snapshot_id=10, prompt='Analyze...')
  Generate a scholarly Map-Reduce report on creator deity theology across the full snapshot.
2 Deep Synthesis Monograph — generate_deep_synthesis(report_id=<report_id>, batch_size=5)
  Execute a 3-phase hierarchical deep synthesis after report completion.
3 Inspect Specific Clusters — get_cluster_group(id=<group_id>, include_members=true)
  Drill into individual cluster groups to verify deity pairings and Atum's specific neighbors.
4 View Snapshot Details — get_cluster_snapshot(id=10, include_groups=true, include_members=true)
  Pull the full breakdown to locate Atum's cluster and audit all member deities.
5 Compare with Myth Clustering — create_cluster_snapshot(target_type='Myth', level=6, title='Creator Myth Narratives Snapshot')
  Build a parallel myth-level snapshot to isolate creator narratives from deity profiles.
6 Research Persistence — $$god_save_research
  Archive findings on Atum's archetype clustering for future comparative mythology work.
"""
    plan_options = extract_plan_options(text)
    commands = [
        ComCommand(index=1, name="$$content_prompt", raw_name="content_prompt", category="content", args="-", description="Prompt"),
        ComCommand(index=2, name="$$leads_get", raw_name="leads_get", category="crm", args="-", description="Leads"),
        ComCommand(index=3, name="$$leads_in_progress", raw_name="leads_in_progress", category="crm", args="-", description="Leads"),
    ]

    # Hitting '3' must resolve to option 3 ("Inspect Specific Clusters — get_cluster_group..."), NOT commands[2] ($$leads_in_progress)
    resolved = resolve_user_input("3", plan_options=plan_options, commands=commands)
    assert "$$leads_in_progress" not in resolved
    assert resolved == plan_options[2].raw_text
    assert "Inspect Specific Clusters — get_cluster_group(id=<group_id>, include_members=true)" in resolved
    assert "Drill into individual cluster groups" in resolved


