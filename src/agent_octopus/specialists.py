from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any
from rich.panel import Panel

from pydantic_ai import Agent, RunContext
from agent_octopus.config import get_model
from agent_octopus.models import (
    SpecialistName,
    SessionContext,
    HandoffRequest,
    HandoffResult,
)
from agent_octopus.mcp_loader import load_mcp_config, create_toolset_for_server
from agent_octopus.com_cli import run_com_get
from agent_octopus.tools import ask_user_interactive


@dataclass
class SpecialistDefinition:
    name: SpecialistName
    description: str
    mcp_servers: list[str]
    system_prompt: str


SPECIALISTS: dict[SpecialistName, SpecialistDefinition] = {
    "research_notes": SpecialistDefinition(
        name="research_notes",
        description="Specialist in saving research notes, creating readable summaries in the user's voice, and managing NoteKing/Memorable content.",
        mcp_servers=["noteking", "memorable"],
        system_prompt=(
            "You are the Research & Notes Specialist Agent. You manage notes in NoteKing and retrieve "
            "rulesets/memories from Memorable.\n"
            "When executing a com command runbook, follow its step-by-step instructions strictly.\n"
            "If you need user input (e.g. asking for text to summarize or clarifying a deity/note topic), "
            "use the `question` tool to ask the user directly."
        ),
    ),
    "content_productivity": SpecialistDefinition(
        name="content_productivity",
        description="Specialist in tasks, backlogs, todo lists, and prompt engineering with Doer and Devbook.",
        mcp_servers=["doer", "devbook"],
        system_prompt=(
            "You are the Content & Productivity Specialist Agent. You interact with Doer (for todo lists and ideas) "
            "and Devbook (for prompt templates).\n"
            "When executing a com command runbook (like $$content_prompt), follow the exact instructions.\n"
            "When presenting options or needing user selection, use the `question` tool with options."
        ),
    ),
    "leads_crm": SpecialistDefinition(
        name="leads_crm",
        description="Specialist in CRM lead management, status progression, and email outreach drafting with Ninja CRM.",
        mcp_servers=["ninja-crm"],
        system_prompt=(
            "You are the Leads & CRM Specialist Agent. You interact with Ninja CRM to retrieve leads, "
            "transition their statuses, and draft personalized outreach emails.\n"
            "Follow the com command runbook closely (e.g. $$leads_get, $$leads_in_progress, $$leads_merge).\n"
            "If a command requires prior leads from the session, check the provided context summary and ledger.\n"
            "Use the `question` tool when selecting backlogs or confirming choices."
        ),
    ),
    "mythology_knowledge": SpecialistDefinition(
        name="mythology_knowledge",
        description="Specialist in comparative mythology, gods, myths, counterparts, and Wikidata entity queries.",
        mcp_servers=["syncretica", "wikidata"],
        system_prompt=(
            "You are the Mythology & Knowledge Specialist Agent. You interact with Syncretica and Wikidata "
            "to find gods, myths, cross-pantheon counterparts, and knowledge entities.\n"
            "When running commands like $$god_find, generate spelling variants and search as instructed.\n"
            "Use the `question` tool if clarification is required."
        ),
    ),
    "astronomer": SpecialistDefinition(
        name="astronomer",
        description="Specialist in astronomy, celestial coordinates, stars, and telescope observations.",
        mcp_servers=["astronomer"],
        system_prompt="You are the Astronomer Specialist Agent. You interact with the Astronomer MCP server.",
    ),
    "biologist": SpecialistDefinition(
        name="biologist",
        description="Specialist in biological taxonomy, species, genetics, and life sciences.",
        mcp_servers=["biologist"],
        system_prompt="You are the Biologist Specialist Agent. You interact with the Biologist MCP server.",
    ),
    "chemist": SpecialistDefinition(
        name="chemist",
        description="Specialist in chemical compounds, molecular properties, and reactions.",
        mcp_servers=["chemist"],
        system_prompt="You are the Chemist Specialist Agent. You interact with the Chemist MCP server.",
    ),
    "physicist": SpecialistDefinition(
        name="physicist",
        description="Specialist in physical constants, mechanics, quantum theory, and calculations.",
        mcp_servers=["physicist"],
        system_prompt="You are the Physicist Specialist Agent. You interact with the Physicist MCP server.",
    ),
    "statesman": SpecialistDefinition(
        name="statesman",
        description="Specialist in geopolitics, international relations, and governance data.",
        mcp_servers=["statesman"],
        system_prompt="You are the Statesman Specialist Agent. You interact with the Statesman MCP server.",
    ),
    "book_rhino": SpecialistDefinition(
        name="book_rhino",
        description="Specialist in books, publishing catalog, reading lists, and literary metadata.",
        mcp_servers=["book-rhino"],
        system_prompt="You are the Book Rhino Specialist Agent. You interact with the Book Rhino MCP server.",
    ),
    "macronx": SpecialistDefinition(
        name="macronx",
        description="Specialist in nutrition logs, macronutrient tracking, and dietary analytics.",
        mcp_servers=["macronx"],
        system_prompt="You are the Macronx Specialist Agent. You interact with the Macronx MCP server.",
    ),
    "evox": SpecialistDefinition(
        name="evox",
        description="Specialist in songbook management, chord charts, and publishable songbook projects.",
        mcp_servers=["evox"],
        system_prompt="You are the Evox Specialist Agent. You interact with the Evox MCP server.",
    ),
}


async def execute_specialist_handoff(
    ctx: RunContext[SessionContext],
    request: HandoffRequest,
) -> HandoffResult:
    """
    Executes a task with the requested specialist agent:
    - Loads runbook if command_name is specified
    - Gathers recent session context / ledger
    - Starts only the specialist's required MCP servers via an AsyncExitStack
    - Injects interactive `question` tool
    - Runs the specialist and stores output in session ledger
    """
    session = ctx.deps
    console = session.console

    spec = SPECIALISTS.get(request.specialist)
    if not spec:
        return HandoffResult(
            specialist=request.specialist,
            command_name=request.command_name,
            summary=f"Error: Specialist '{request.specialist}' not found.",
            output=f"Error: Specialist '{request.specialist}' is not recognized.",
        )

    # 1. Fetch command markdown runbook if specified
    runbook_context = ""
    if request.command_name:
        runbook = run_com_get(request.command_name, com_bin=session.settings.com_bin)
        runbook_context = f"\n\n### COMMAND RUNBOOK ({request.command_name}):\n{runbook}\n"

    # 2. Build history/context from shared ledger
    recent_ledger = ""
    if session.shared_ledger:
        recent_ledger = "\n\n### RECENT WORK IN THIS SESSION:\n"
        for entry in session.shared_ledger[-3:]:
            recent_ledger += f"[{entry.specialist}]: {entry.summary}\n{entry.output[:400]}...\n"

    extra_instructions = (
        f"{spec.system_prompt}\n"
        f"{runbook_context}"
        f"{recent_ledger}\n"
    )

    # 3. Load MCP servers for this specialist
    mcp_defs = load_mcp_config(session.settings.mcp_config_path)

    async with AsyncExitStack() as stack:
        toolsets = []
        for server_name in spec.mcp_servers:
            if server_name in mcp_defs:
                console.print(f"[dim]Starting MCP server: {server_name}...[/dim]")
                toolset = create_toolset_for_server(server_name, mcp_defs[server_name])
                await stack.enter_async_context(toolset)
                toolsets.append(toolset)
            else:
                console.print(f"[yellow]Warning: MCP server '{server_name}' not found in config.[/yellow]")

        # Create specialist agent with model, toolsets, and system instructions
        model = get_model(session.settings)
        specialist_agent = Agent(
            model=model,
            deps_type=SessionContext,
            toolsets=toolsets,
            system_prompt=extra_instructions,
        )

        # Register interactive question tool
        @specialist_agent.tool
        async def question(
            sub_ctx: RunContext[SessionContext],
            question_text: str,
            options: list[str] | None = None,
        ) -> str:
            """Ask the user an interactive question in the terminal and receive their response."""
            return ask_user_interactive(sub_ctx.deps, question_text, options)

        prompt_text = (
            f"TASK: {request.task}\n"
            f"CONTEXT: {request.context_summary or 'None'}"
        )

        history = session.specialist_histories.get(request.specialist, [])
        with console.status(f"[bold cyan]Specialist '{request.specialist}' working...[/bold cyan]"):
            result = await specialist_agent.run(
                prompt_text,
                deps=session,
                message_history=history,
            )

        # Update specialist's history
        session.specialist_histories[request.specialist] = result.all_messages()

        output_str = str(result.output)
        summary = f"Completed task via {request.specialist}: {request.task[:60]}"

        handoff_res = HandoffResult(
            specialist=request.specialist,
            command_name=request.command_name,
            summary=summary,
            output=output_str,
        )
        session.shared_ledger.append(handoff_res)
        return handoff_res
