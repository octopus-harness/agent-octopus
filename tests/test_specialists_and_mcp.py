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
    sanitize_mcp_tool_result,
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
    assert mythology_spec.apply_readability_pass is True


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

    result = await process_mcp_tool_call(mock_ctx, mock_call_tool, "compute_clusters", {"level": 6})
    mock_call_tool.assert_awaited_once_with("compute_clusters", {"level": 6})
    assert result["top_clusters"][0]["name"] == "War Domain"
    assert result["sample_singletons"] == ["Hermes"]


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


