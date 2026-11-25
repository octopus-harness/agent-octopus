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
        description="Specialist in saving research notes and managing NoteKing/Memorable content.",
        mcp_servers=["noteking", "memorable"],
        system_prompt=(
            "You are the Research & Notes Specialist Agent. You manage notes in NoteKing and retrieve "
            "rulesets/memories from Memorable.\n"
            "When executing a com command runbook, follow its step-by-step instructions strictly.\n"
            "If you need user input (e.g. asking for text to summarize or clarifying a deity/note topic), "
            "use the `question` tool to ask the user directly."
        ),
    ),
    "readability": SpecialistDefinition(
        name="readability",
        description="Specialist in rewriting text into clear, readable prose or concise summaries in the user's voice using Memorable writing rules and NoteKing context.",
        mcp_servers=["memorable", "noteking"],
        system_prompt=(
            "You are the Readability & Voice Specialist Agent. You retrieve writing rulesets from Memorable "
            "and reference notes in NoteKing to rewrite and polish text into clear, readable prose matching the user's voice.\n"
            "When executing command runbooks like $$readable_text or $$readable_summary, follow instructions strictly.\n"
            "Keep the original meaning, facts, and structure intact while eliminating jargon, fluff, and robotic phrasing."
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
        description="Specialist in comparative astrophysics, cosmic structures, star systems, celestial body manifolds, and pgvector clustering.",
        mcp_servers=["astronomer"],
        system_prompt=(
            "You are the Astronomer Specialist Agent. You interact with the Astronomer computational research "
            "platform for comparative astrophysics, stellar systems, and celestial body manifolds over pgvector."
        ),
    ),
    "biologist": SpecialistDefinition(
        name="biologist",
        description="Specialist in comparative biology, ecology, organismal taxonomy, biomes, and species manifolds.",
        mcp_servers=["biologist"],
        system_prompt=(
            "You are the Biologist Specialist Agent. You interact with the Biologist computational research "
            "platform for comparative biology, ecology, and evolutionary convergence inquiries over pgvector."
        ),
    ),
    "chemist": SpecialistDefinition(
        name="chemist",
        description="Specialist in comparative chemistry, molecular structures, functional group manifolds, and synthesis reports.",
        mcp_servers=["chemist"],
        system_prompt=(
            "You are the Chemist Specialist Agent. You interact with the Chemist computational research "
            "platform for comparative chemistry, molecular structures, and functional group manifolds."
        ),
    ),
    "physicist": SpecialistDefinition(
        name="physicist",
        description="Specialist in comparative particle physics, subatomic particles, and quantum state manifolds.",
        mcp_servers=["physicist"],
        system_prompt=(
            "You are the Physicist Specialist Agent. You interact with the Physicist computational research "
            "platform for comparative particle physics, quantum state manifolds, and quantum cluster synthesis."
        ),
    ),
    "statesman": SpecialistDefinition(
        name="statesman",
        description="Specialist in comparative geopolitics, statecraft, urban power centers, and cross-continental manifolds.",
        mcp_servers=["statesman"],
        system_prompt=(
            "You are the Statesman Specialist Agent. You interact with the Statesman computational research "
            "platform for comparative geopolitics, statecraft, and urban power centers over pgvector."
        ),
    ),
    "book_rhino": SpecialistDefinition(
        name="book_rhino",
        description="Specialist in AI-assisted novel architecture, worldbuilding, character taxonomies, Sidekiq AI pipelines, and manuscript compilation.",
        mcp_servers=["book-rhino"],
        system_prompt=(
            "You are the Book Rhino Specialist Agent. You interact with Book Rhino to architect novels, build worlds "
            "and characters, manage creative taxonomies, run Sidekiq generation jobs, and export compiled manuscripts."
        ),
    ),
    "macronx": SpecialistDefinition(
        name="macronx",
        description="Specialist in Open-Source Intelligence (OSINT) signal ingestion, multimodal attachments, inbox triage, and Executive Intelligence Briefs (EIB).",
        mcp_servers=["macronx"],
        system_prompt=(
            "You are the MacronX Specialist Agent. You interact with the MacronX OSINT pipeline to ingest raw signals, "
            "triage intelligence inboxes, inspect multimodal media attachments, and synthesize Executive Intelligence Briefs (EIB)."
        ),
    ),
    "evox": SpecialistDefinition(
        name="evox",
        description="Specialist in structured Song AST authoring and PDF songbook compilation with aligned chords and Table of Contents.",
        mcp_servers=["evox"],
        system_prompt=(
            "You are the Evox Specialist Agent. You interact with Evox to author Song ASTs and compile "
            "publication-quality PDF songbooks with multi-column lyrics, aligned chords, and automatic Table of Contents."
        ),
    ),
}


READABILITY_ENHANCED_SPECIALISTS: set[SpecialistName] = {
    "mythology_knowledge",
}


async def apply_readability_pass(
    ctx: RunContext[SessionContext],
    raw_text: str,
    command_name: str = "readable_text",
) -> str:
    """
    Passes raw specialist output text through the readability specialist using the specified command runbook (default $$readable_text).
    Falls back gracefully to raw_text on error.
    """
    if not raw_text or not raw_text.strip() or raw_text.startswith("Error:"):
        return raw_text

    try:
        ctx.deps.console.print(
            f"[dim]Polishing output via readability specialist ($${command_name})...[/dim]"
        )
        rewrite_req = HandoffRequest(
            specialist="readability",
            command_name=command_name,
            task=f"Pass the following text through the $${command_name} command runbook and return the rewritten readable prose:\n\n{raw_text}",
            context_summary=f"Rewriting specialist output for readability in user voice: {raw_text[:200]}",
        )
        rewrite_res = await execute_specialist_handoff(ctx, rewrite_req)
        if rewrite_res.output and not rewrite_res.output.startswith("Error:"):
            return rewrite_res.output
    except Exception as e:
        ctx.deps.console.print(
            f"[yellow]Warning: Readability pass failed: {e}. Preserving raw output.[/yellow]"
        )

    return raw_text


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
            name=spec.name,
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
            return await ask_user_interactive(sub_ctx.deps, question_text, options)

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

        # Apply automated readability post-processing if specialist is registered
        if request.specialist in READABILITY_ENHANCED_SPECIALISTS:
            output_str = await apply_readability_pass(ctx, output_str, command_name="readable_text")

        summary = f"Completed task via {request.specialist}: {request.task[:60]}"

        handoff_res = HandoffResult(
            specialist=request.specialist,
            command_name=request.command_name,
            summary=summary,
            output=output_str,
        )
        session.shared_ledger.append(handoff_res)
        return handoff_res
