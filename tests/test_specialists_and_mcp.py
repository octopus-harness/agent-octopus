import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from rich.console import Console

from pydantic_ai.exceptions import ModelContextWindowExceededError
from agent_octopus.models import SessionContext, HandoffRequest
from agent_octopus.config import load_settings, MCPServerDefinition
from agent_octopus.mcp_loader import (
    load_mcp_config,
    create_toolset_for_server,
    summarize_clusters_result,
    summarize_report_result,
    sanitize_mcp_tool_result,
    coerce_mcp_tool_args,
    process_mcp_tool_call,
    MAX_TOOL_OUTPUT_CHARS,
)
from agent_octopus.specialists import SPECIALISTS, execute_specialist_handoff
from agent_octopus.orchestrator import create_orchestrator_agent


def test_mcp_config_loading():
    mcp_defs = load_mcp_config("mcp_config.json")
    expected_servers = [
        "noteking",
        "memorable",
        "doer",
        "devbook",
        "ninja-crm",
        "syncretica",
        "wikidata",
        "astronomer",
        "biologist",
        "chemist",
        "physicist",
        "statesman",
        "book-rhino",
        "macronx",
        "evox",
    ]
    for s in expected_servers:
        assert s in mcp_defs, f"Missing MCP server config for {s}"
        assert mcp_defs[s].command == "node"
        assert len(mcp_defs[s].args) > 0


def test_specialists_mapping():
    assert len(SPECIALISTS) == 13
    assert "readability" in SPECIALISTS
    assert SPECIALISTS["readability"].mcp_servers == ["memorable", "noteking"]
    mcp_defs = load_mcp_config("mcp_config.json")

    for spec_name, spec in SPECIALISTS.items():
        assert spec.name == spec_name
        for server in spec.mcp_servers:
            assert server in mcp_defs, f"Specialist {spec_name} requires missing MCP server {server}"


def test_mythology_knowledge_planning_prompt():
    mythology_spec = SPECIALISTS["mythology_knowledge"]
    assert "Recommended Next Steps & Actions" in mythology_spec.system_prompt
    assert "find_counterparts" in mythology_spec.system_prompt
    assert "compute_clusters" in mythology_spec.system_prompt
    assert "create_cluster_snapshot" in mythology_spec.system_prompt
    assert "generate_deep_synthesis" in mythology_spec.system_prompt
    assert "$$god_save_research" in mythology_spec.system_prompt
    assert "wait_for_cluster_report" in mythology_spec.system_prompt
    assert "NEVER create duplicates" in mythology_spec.system_prompt
    assert mythology_spec.apply_readability_pass is True


def test_summarize_report_result():
    fake_summaries = [
        {"id": i, "cluster_group_id": 100 + i, "cluster_group_name": f"Group {i}", "position": i + 1, "content": "Long analysis " * 100}
        for i in range(20)
    ]
    report_data = {
        "id": 8,
        "cluster_snapshot_id": 7,
        "title": "Cosmogony Study",
        "prompt": "Analyze auto-genesis",
        "status": "completed",
        "content": "# Full Monograph Content\nDetailed scholarly synthesis...",
        "summaries": fake_summaries,
        "summarized_clusters_count": 20,
        "total_clusters_count": 20,
    }
    summarized = summarize_report_result(report_data, max_summaries=5)
    assert "summaries" not in summarized
    assert "summaries_sample" in summarized
    assert len(summarized["summaries_sample"]) == 5
    assert summarized["total_summaries_count"] == 20
    assert summarized["content"] == "# Full Monograph Content\nDetailed scholarly synthesis..."

    # When sanitized via sanitize_mcp_tool_result
    sanitized = sanitize_mcp_tool_result(report_data)
    assert "summaries_sample" in sanitized
    assert "summaries" not in sanitized


def test_summarize_clusters_result():
    # Simulate a massive compute_clusters response with 50 clusters and 200 singletons
    fake_clusters = []
    for i in range(50):
        fake_clusters.append({
            "id": i,
            "name": f"Archetype Domain {i}",
            "size": 10,
            "shared_themes": ["Solar", "Creation"],
            "pantheons": ["Egyptian", "Norse"],
            "members": [
                {"id": j, "name": f"Deity_{i}_{j}", "description": "A very long detailed bio " * 50}
                for j in range(10)
            ],
        })
    fake_singletons = [
        {"id": k, "name": f"Singleton_{k}", "description": "Long bio " * 50}
        for k in range(200)
    ]
    raw_data = {
        "target_type": "God",
        "level": 6,
        "distance_threshold": 0.21,
        "full_coverage": False,
        "total_embedded_count": 700,
        "unembedded_count": 0,
        "clusters_count": 50,
        "singletons_count": 200,
        "largest_cluster_size": 10,
        "clusters": fake_clusters,
        "singletons": fake_singletons,
    }

    raw_len = len(json.dumps(raw_data))
    assert raw_len > 200_000

    summarized = summarize_clusters_result(raw_data, max_clusters=5, max_members_per_cluster=3, max_singletons=4)
    summarized_len = len(json.dumps(summarized))
    assert summarized_len < 5_000

    assert summarized["target_type"] == "God"
    assert summarized["level"] == 6
    assert summarized["clusters_count"] == 50
    assert summarized["singletons_count"] == 200
    assert len(summarized["top_clusters"]) == 5
    assert summarized["omitted_clusters_count"] == 45
    assert len(summarized["sample_singletons"]) == 4
    assert summarized["omitted_singletons_count"] == 196
    # Check sample members are strings, not dicts
    assert summarized["top_clusters"][0]["sample_members"] == ["Deity_0_0", "Deity_0_1", "Deity_0_2"]


def test_sanitize_mcp_tool_result_truncation():
    # 1. Normal small string passes through
    small_str = "Short result"
    assert sanitize_mcp_tool_result(small_str) == small_str

    # 2. Oversized string gets truncated with warning
    huge_str = "x" * (MAX_TOOL_OUTPUT_CHARS + 500)
    sanitized = sanitize_mcp_tool_result(huge_str)
    assert len(sanitized) > MAX_TOOL_OUTPUT_CHARS
    assert "[Warning: Tool output exceeded limit" in sanitized

    # 3. Oversized dict gets serialized and truncated
    huge_dict = {"data": "y" * (MAX_TOOL_OUTPUT_CHARS + 500)}
    sanitized_dict = sanitize_mcp_tool_result(huge_dict)
    assert isinstance(sanitized_dict, str)
    assert "[Warning: Tool output exceeded limit" in sanitized_dict


@pytest.mark.asyncio
async def test_process_mcp_tool_call():
    mock_ctx = MagicMock()
    mock_call_tool = AsyncMock()

    # Simulate compute_clusters call returning massive cluster data
    fake_cluster_data = {
        "target_type": "God",
        "clusters": [{"id": 1, "name": "War Domain", "members": [{"name": "Ares"}]}],
        "singletons": [{"name": "Hermes"}],
    }
    mock_call_tool.return_value = fake_cluster_data

    # Test that level="6" is coerced to integer 6
    result = await process_mcp_tool_call(mock_ctx, mock_call_tool, "compute_clusters", {"level": "6"})
    mock_call_tool.assert_awaited_once_with("compute_clusters", {"level": 6})
    assert result["top_clusters"][0]["name"] == "War Domain"
    assert result["sample_singletons"] == ["Hermes"]


def test_coerce_mcp_tool_args():
    # 1. noteking_create_note arguments
    raw_args = {
        "project_id": "3",
        "title": "123",
        "body": "456",
        "pinned": "true",
        "pinned_position": "1",
    }
    coerced = coerce_mcp_tool_args(raw_args)
    assert coerced["project_id"] == 3
    assert isinstance(coerced["project_id"], int)
    assert coerced["pinned"] is True
    assert coerced["pinned_position"] == 1
    # title and body must stay strings even if numeric
    assert coerced["title"] == "123"
    assert isinstance(coerced["title"], str)
    assert coerced["body"] == "456"
    assert isinstance(coerced["body"], str)

    # 2. memorable_get_memory arguments
    mem_args = {"id": "5", "render_markdown": "false"}
    coerced_mem = coerce_mcp_tool_args(mem_args)
    assert coerced_mem["id"] == 5
    assert isinstance(coerced_mem["id"], int)
    assert coerced_mem["render_markdown"] is False


def test_create_toolset_for_server_registers_process_tool_call():
    defn = MCPServerDefinition(command="node", args=["test.js"])
    toolset = create_toolset_for_server("test_server", defn)
    assert toolset.process_tool_call is process_mcp_tool_call


@pytest.mark.asyncio
async def test_execute_specialist_handoff_recovers_from_context_window_exceeded():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    req = HandoffRequest(
        specialist="mythology_knowledge",
        task="compute_clusters(level=6)",
    )

    err = ModelContextWindowExceededError(model_name="test-model", message="Prompt is too long: context window exceeded")

    with patch("agent_octopus.specialists.base.load_mcp_config", return_value={"syncretica": MCPServerDefinition(command="node", args=[])}):
        with patch("agent_octopus.specialists.base.create_toolset_for_server"):
            with patch("agent_octopus.specialists.base.Agent") as mock_agent_cls:
                mock_agent = MagicMock()
                mock_agent.run = AsyncMock(side_effect=err)
                mock_agent_cls.return_value = mock_agent

                result = await execute_specialist_handoff(mock_ctx, req)
                assert "context window limit was exceeded" in result.output
                assert result.specialist == "mythology_knowledge"
                assert len(session.shared_ledger) == 1
                assert "Context window exceeded" in session.shared_ledger[0].summary


@pytest.mark.asyncio
async def test_delegate_to_specialist_handles_unexpected_error():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    orchestrator = create_orchestrator_agent()
    # Find delegate_to_specialist tool function from agent
    delegate_tool = orchestrator._function_toolset.tools["delegate_to_specialist"]

    with patch("agent_octopus.orchestrator.execute_specialist_handoff", side_effect=RuntimeError("Connection exploded")):
        output = await delegate_tool.function(
            mock_ctx,
            specialist="mythology_knowledge",
            task="Some task",
        )
        assert "Specialist [mythology_knowledge] failed with error: Connection exploded" in output


@pytest.mark.asyncio
async def test_delegate_to_specialist_reroutes_research_persistence_to_research_notes():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    orchestrator = create_orchestrator_agent()
    delegate_tool = orchestrator._function_toolset.tools["delegate_to_specialist"]

    with patch("agent_octopus.orchestrator.execute_specialist_handoff") as mock_handoff:
        mock_handoff.return_value = MagicMock(specialist="research_notes", output="Note saved")

        # 1. Direct command name: god_save_research
        await delegate_tool.function(
            mock_ctx,
            specialist="mythology_knowledge",
            task="Summarize and save Atum research",
            command_name="god_save_research",
        )
        assert mock_handoff.call_count == 1
        req1 = mock_handoff.call_args[0][1]
        assert req1.specialist == "research_notes"
        assert req1.command_name == "god_save_research"

        # 2. Command name with $$ prefix: $$god_save_research
        await delegate_tool.function(
            mock_ctx,
            specialist="mythology_knowledge",
            task="Persist findings to research project",
            command_name="$$god_save_research",
        )
        assert mock_handoff.call_count == 2
        req2 = mock_handoff.call_args[0][1]
        assert req2.specialist == "research_notes"
        assert req2.command_name == "god_save_research"

        # 3. Natural language task without command_name
        await delegate_tool.function(
            mock_ctx,
            specialist="mythology_knowledge",
            task="Save research on Atum to NoteKing research project",
        )
        assert mock_handoff.call_count == 3
        req3 = mock_handoff.call_args[0][1]
        assert req3.specialist == "research_notes"
        assert req3.command_name == "god_save_research"

        # 4. Normal mythology query stays on mythology_knowledge
        await delegate_tool.function(
            mock_ctx,
            specialist="mythology_knowledge",
            task="Find a god named Odin",
            command_name="$$god_find",
        )
        assert mock_handoff.call_count == 4
        req4 = mock_handoff.call_args[0][1]
        assert req4.specialist == "mythology_knowledge"
        assert req4.command_name == "god_find"


@pytest.mark.asyncio
async def test_execute_specialist_handoff_preserves_expanded_ledger_context():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    # Add a large output from mythology_knowledge (2,000 chars)
    large_output = "Atum Egyptian Creator Deity Analysis. " * 50  # ~2,000 chars
    from agent_octopus.models import HandoffResult
    session.shared_ledger.append(
        HandoffResult(
            specialist="mythology_knowledge",
            command_name="god_find",
            summary="Atum research profile",
            output=large_output,
        )
    )

    req = HandoffRequest(
        specialist="research_notes",
        task="Save research to noteking",
        command_name="god_save_research",
    )

    with patch("agent_octopus.specialists.base.load_mcp_config", return_value={
        "noteking": MCPServerDefinition(command="node", args=[]),
        "memorable": MCPServerDefinition(command="node", args=[]),
    }):
        with patch("agent_octopus.specialists.base.create_toolset_for_server"):
            with patch("agent_octopus.specialists.base.Agent") as mock_agent_cls:
                mock_agent = MagicMock()
                mock_agent.run = AsyncMock(return_value=MagicMock(output="Saved", all_messages=lambda: []))
                mock_agent_cls.return_value = mock_agent

                await execute_specialist_handoff(mock_ctx, req)

                # Inspect system_prompt passed to specialist_agent
                call_kwargs = mock_agent_cls.call_args[1]
                prompt = call_kwargs["system_prompt"]
                # Must contain the full 2,000 chars without premature 400-char truncation
                assert large_output in prompt



