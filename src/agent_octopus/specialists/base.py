import re
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any
from rich.panel import Panel

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelContextWindowExceededError
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
    apply_readability_pass: bool = False


def _get_specialists_module():
    return sys.modules.get("agent_octopus.specialists")


def clean_readability_output(text: str) -> str:
    """
    Cleans readability output by removing conversational preambles
    and trailing changelogs or 'Changes made:' meta-commentary.
    """
    if not text:
        return ""

    cleaned = text.strip()

    # Strip leading preambles like "Here is the rewritten text:\n\n"
    cleaned = re.sub(
        r"^(?:Here is (?:the )?(?:rewritten|polished|updated|revised) [^:\n]+:\s*\n+)+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Strip trailing changelog sections (e.g. "Changes made:\n- ...", "What changed:\n- ...")
    cleaned = re.sub(
        r"\n+(?:---+\n+)?(?:#*\s*(?:Changes made|What changed|Summary of changes|Edits made|Key changes|Notes on changes|Changelog)\s*:\s*.*)$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return cleaned.strip()


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
            task=(
                f"Pass the following text through the $${command_name} command runbook and return "
                f"ONLY the rewritten readable prose without any changelog, list of changes made, "
                f"explanations, or meta-commentary:\n\n{raw_text}"
            ),
            context_summary=f"Rewriting specialist output for readability in user voice: {raw_text[:200]}",
        )
        pkg = _get_specialists_module()
        handoff_fn = getattr(pkg, "execute_specialist_handoff", execute_specialist_handoff)
        rewrite_res = await handoff_fn(ctx, rewrite_req)
        if rewrite_res.output and not rewrite_res.output.startswith("Error:"):
            return clean_readability_output(rewrite_res.output)
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

    pkg = _get_specialists_module()
    specialists_dict = getattr(pkg, "SPECIALISTS", {})
    spec = specialists_dict.get(request.specialist)

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
            out_preview = entry.output[:5000] + ("..." if len(entry.output) > 5000 else "")
            recent_ledger += f"[{entry.specialist}]: {entry.summary}\n{out_preview}\n"

    extra_instructions = (
        f"{spec.system_prompt}\n"
        f"{runbook_context}"
        f"{recent_ledger}\n"
    )

    # 3. Load MCP servers for this specialist
    mcp_loader = getattr(pkg, "load_mcp_config", load_mcp_config)
    mcp_defs = mcp_loader(session.settings.mcp_config_path)

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
            retries=3,
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
        try:
            with console.status(f"[bold cyan]Specialist '{request.specialist}' working...[/bold cyan]"):
                result = await specialist_agent.run(
                    prompt_text,
                    deps=session,
                    message_history=history,
                )
        except ModelContextWindowExceededError as e:
            console.print(f"[bold red]Specialist '{request.specialist}' exceeded context window: {e}[/bold red]")
            error_output = (
                f"Specialist [{request.specialist}] was unable to complete the request because the "
                f"context window limit was exceeded: {e}.\n\n"
                "The tool output or conversation history exceeded the model's capacity. "
                "Please refine the query with more specific filters or parameters."
            )
            handoff_res = HandoffResult(
                specialist=request.specialist,
                command_name=request.command_name,
                summary=f"Context window exceeded for {request.specialist}",
                output=error_output,
            )
            session.shared_ledger.append(handoff_res)
            return handoff_res
        except Exception as e:
            console.print(f"[bold red]Specialist '{request.specialist}' failed: {e}[/bold red]")
            error_output = f"Specialist [{request.specialist}] encountered an error during execution: {e}"
            handoff_res = HandoffResult(
                specialist=request.specialist,
                command_name=request.command_name,
                summary=f"Execution error for {request.specialist}",
                output=error_output,
            )
            session.shared_ledger.append(handoff_res)
            return handoff_res

        # Update specialist's history
        session.specialist_histories[request.specialist] = result.all_messages()

        output_str = str(result.output)

        # Apply automated readability post-processing if enabled on specialist definition
        if spec.apply_readability_pass:
            readability_fn = getattr(pkg, "apply_readability_pass", apply_readability_pass)
            output_str = await readability_fn(ctx, output_str, command_name="readable_text")

        summary = f"Completed task via {request.specialist}: {request.task[:60]}"

        handoff_res = HandoffResult(
            specialist=request.specialist,
            command_name=request.command_name,
            summary=summary,
            output=output_str,
        )
        session.shared_ledger.append(handoff_res)
        return handoff_res
