from typing import Any
from rich.panel import Panel
from rich.table import Table

from pydantic_ai import Agent, RunContext
from agent_octopus.config import get_model
from agent_octopus.models import (
    SessionContext,
    HandoffRequest,
    HandoffResult,
    SpecialistName,
)
from agent_octopus.com_cli import run_com_list, run_com_get
from agent_octopus.specialists import execute_specialist_handoff, SPECIALISTS


CINDERBLOCK_SAVE_COMMANDS: dict[str, str] = {
    "mythology_knowledge": "god_save_research",
    "astronomer": "astronomer_save_research",
    "biologist": "biologist_save_research",
    "chemist": "chemist_save_research",
    "physicist": "physicist_save_research",
    "statesman": "statesman_save_research",
}

PERSISTENCE_COMMANDS: set[str] = {
    "add_research",
    *CINDERBLOCK_SAVE_COMMANDS.values(),
}


def infer_persistence_command(orig_specialist: str, task: str) -> str:
    """
    Infers the appropriate *_save_research command based on the original specialist
    or domain keywords in the task text, defaulting to 'add_research'.
    """
    if orig_specialist in CINDERBLOCK_SAVE_COMMANDS:
        return CINDERBLOCK_SAVE_COMMANDS[orig_specialist]

    t = task.lower()
    if any(k in t for k in ("god", "myth", "deity", "pantheon", "syncretica")):
        return "god_save_research"
    if any(k in t for k in ("astronomer", "star system", "celestial body", "cosmic structure")):
        return "astronomer_save_research"
    if any(k in t for k in ("biologist", "species", "organism", "biome")):
        return "biologist_save_research"
    if any(k in t for k in ("chemist", "molecule", "functional group", "chemical class")):
        return "chemist_save_research"
    if any(k in t for k in ("physicist", "subatomic particle", "quantum state", "particle group")):
        return "physicist_save_research"
    if any(k in t for k in ("statesman", "country", "city", "geopolitics", "continent")):
        return "statesman_save_research"
    return "add_research"


ORCHESTRATOR_SYSTEM_PROMPT = """You are the Octopus CLI Orchestrator Agent.
Your job is to manage terminal conversations, present commands, interpret user requests, and hand off work to specialized sub-agents.

Key Responsibilities:
1. STARTUP & COMMAND LISTING:
   Commands belong to distinct categories (e.g. research, content, mythology, astronomy, biology, chemistry, physics, geopolitics, crm, help, general).
   When listing or presenting commands, group them by category and display their number (1..N), command name, args, and description.
   Acknowledge session start warmly and ask the user what they would like to do.

2. SUBSEQUENT TURNS:
   The user may:
   - Provide a number corresponding to a command (e.g., "1", "4", or "4 Zeus").
   - Provide a command name directly (e.g., "$$content_prompt", "$$god_find Odin", "$$astronomer_find TRAPPIST-1").
   - Provide a natural language request (e.g., "Find leads for coaching", "Draft an article prompt").

3. HANDOFF:
   - When a request or command requires action with tools or data, use the `delegate_to_specialist` tool.
   - Map commands to specialists:
     * $$add_research, $$god_save_research, $$astronomer_save_research, $$biologist_save_research, $$chemist_save_research, $$physicist_save_research, $$statesman_save_research, saving research notes, and NoteKing note persistence -> ALWAYS research_notes
     * $$readable_text, $$readable_summary -> readability
     * $$content_prompt -> content_productivity
     * $$leads_get, $$leads_in_progress, $$leads_merge -> leads_crm
     * $$god_find, mythology queries, and Syncretica analytical/planning operations (counterparts, clustering, snapshots, reports, monographs) -> mythology_knowledge
     * $$astronomer_find, astronomy queries, and Astronomer analytical/planning operations (counterparts, clustering, snapshots, reports, monographs) -> astronomer
     * $$biologist_find, biology queries, and Biologist analytical/planning operations (counterparts, clustering, snapshots, reports, monographs) -> biologist
     * $$chemist_find, chemistry queries, and Chemist analytical/planning operations (counterparts, clustering, snapshots, reports, monographs) -> chemist
     * $$physicist_find, physics queries, and Physicist analytical/planning operations (counterparts, clustering, snapshots, reports, monographs) -> physicist
     * $$statesman_find, geopolitics queries, and Statesman analytical/planning operations (counterparts, clustering, snapshots, reports, monographs) -> statesman
     * Other domain requests (novel architecture, OSINT, songbooks) -> book_rhino, macronx, evox
   - CRITICAL ROUTING RULE FOR RESEARCH PERSISTENCE:
     * Step 6 of recommended actions ("Research Persistence: $$<domain>_save_research") or ANY request to save research, notes, or findings into NoteKing or the Research project MUST ALWAYS be delegated to `research_notes`, NEVER to `mythology_knowledge`, `astronomer`, `biologist`, `chemist`, `physicist`, or `statesman`.
     * The Cinderblock domain specialists ONLY connect to their respective domain platforms and CANNOT interact with NoteKing or save notes.
     * When delegating research saving to `research_notes`, always provide the entity name, context, and key findings/counterparts from the session in `task` and `context_summary` so `research_notes` has the complete information to synthesize and save.
   - Meta commands ($$commands, $$help) can be answered directly using the `get_command_help` or `list_commands` tools.
   - When the specialist returns its result, present the specialist's output directly and fully to the user. Always preserve all sections, tables, and action choices (especially 'Recommended Next Steps & Actions') in full without omitting, truncating, or summarizing them away.
"""


def create_orchestrator_agent(model: Any = None) -> Agent[SessionContext, str]:
    if model is None:
        model = get_model()

    agent: Agent[SessionContext, str] = Agent(
        model=model,
        name="orchestrator",
        deps_type=SessionContext,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    )

    @agent.tool
    async def list_commands(ctx: RunContext[SessionContext]) -> str:
        """Run `com list` to see all registered commands."""
        raw, _ = run_com_list(com_bin=ctx.deps.settings.com_bin)
        return raw

    @agent.tool
    async def get_command_help(ctx: RunContext[SessionContext], command_name: str) -> str:
        """Run `com get <name>` to view a specific command's markdown runbook definition."""
        return run_com_get(command_name, com_bin=ctx.deps.settings.com_bin)

    @agent.tool
    async def delegate_to_specialist(
        ctx: RunContext[SessionContext],
        specialist: SpecialistName,
        task: str,
        command_name: str | None = None,
        context_summary: str | None = None,
    ) -> str:
        """
        Delegate a task or command execution to one of the 13 specialist sub-agents.
        The specialist will be spun up with its required MCP servers and report back results.
        """
        clean_cmd = command_name.strip().removeprefix("$$") if command_name else None
        orig_specialist = specialist

        # Safeguard: Ensure NoteKing research persistence is always routed to research_notes
        is_persistence_cmd = clean_cmd in PERSISTENCE_COMMANDS
        is_persistence_task = (
            ("save" in task.lower() or "persist" in task.lower())
            and ("research" in task.lower() or "note" in task.lower() or "noteking" in task.lower())
        )
        if is_persistence_cmd or (orig_specialist in CINDERBLOCK_SAVE_COMMANDS and is_persistence_task):
            if specialist != "research_notes":
                ctx.deps.console.print(
                    f"[dim]Routing research persistence request to 'research_notes' specialist (was {orig_specialist}).[/dim]"
                )
                specialist = "research_notes"
            if not clean_cmd:
                clean_cmd = infer_persistence_command(orig_specialist, task)

        ctx.deps.console.print(
            f"[bold magenta]⚡ Orchestrator delegating to specialist: [green]{specialist}[/green][/bold magenta]"
        )
        req = HandoffRequest(
            specialist=specialist,
            task=task,
            command_name=clean_cmd,
            context_summary=context_summary,
        )
        try:
            result: HandoffResult = await execute_specialist_handoff(ctx, req)
            return f"Specialist [{result.specialist}] completed execution:\n\n{result.output}"
        except Exception as e:
            return f"Specialist [{specialist}] failed with error: {e}"

    return agent
