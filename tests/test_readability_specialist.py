import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from rich.console import Console

from agent_octopus.config import load_settings
from agent_octopus.models import SessionContext, HandoffRequest, HandoffResult
from agent_octopus.specialists import (
    SPECIALISTS,
    READABILITY_ENHANCED_SPECIALISTS,
    apply_readability_pass,
    execute_specialist_handoff,
)


def test_readability_specialist_definition():
    assert "readability" in SPECIALISTS
    spec = SPECIALISTS["readability"]
    assert spec.name == "readability"
    assert "memorable" in spec.mcp_servers
    assert "noteking" in spec.mcp_servers
    assert "writing rulesets" in spec.system_prompt.lower() or "readability" in spec.system_prompt.lower()


def test_readability_enhanced_registry():
    assert SPECIALISTS["mythology_knowledge"].apply_readability_pass is True
    assert SPECIALISTS["readability"].apply_readability_pass is False
    assert SPECIALISTS["astronomer"].apply_readability_pass is False
    assert "mythology_knowledge" in READABILITY_ENHANCED_SPECIALISTS
    assert "readability" not in READABILITY_ENHANCED_SPECIALISTS
    assert "astronomer" not in READABILITY_ENHANCED_SPECIALISTS


@pytest.mark.asyncio
async def test_apply_readability_pass_empty_or_error():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    # Empty string should return as-is without handoff
    res = await apply_readability_pass(mock_ctx, "")
    assert res == ""

    # Whitespace only should return as-is
    res = await apply_readability_pass(mock_ctx, "   \n  ")
    assert res == "   \n  "

    # Error string should return as-is
    error_text = "Error: Specialist 'foo' is not recognized."
    res = await apply_readability_pass(mock_ctx, error_text)
    assert res == error_text


@pytest.mark.asyncio
async def test_apply_readability_pass_success():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    raw_text = "Raw deity info: Odin is allfather, associated with wisdom, war."
    polished_text = "Odin stands as the Allfather in Norse cosmology, presiding over wisdom and war."

    mock_handoff_result = HandoffResult(
        specialist="readability",
        command_name="readable_text",
        summary="Rewrote text",
        output=polished_text,
    )

    with patch("agent_octopus.specialists.execute_specialist_handoff", new=AsyncMock(return_value=mock_handoff_result)) as mock_handoff:
        res = await apply_readability_pass(mock_ctx, raw_text, command_name="readable_text")
        assert res == polished_text
        mock_handoff.assert_called_once()
        call_req = mock_handoff.call_args[0][1]
        assert call_req.specialist == "readability"
        assert call_req.command_name == "readable_text"
        assert raw_text in call_req.task


@pytest.mark.asyncio
async def test_apply_readability_pass_fallback_on_exception():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    raw_text = "Raw mythology output that must survive if rewriting errors out."

    with patch("agent_octopus.specialists.execute_specialist_handoff", new=AsyncMock(side_effect=RuntimeError("MCP server unavailable"))):
        res = await apply_readability_pass(mock_ctx, raw_text)
        assert res == raw_text


@pytest.mark.asyncio
async def test_mythology_handoff_triggers_readability():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    req = HandoffRequest(
        specialist="mythology_knowledge",
        command_name="god_find",
        task="Find details for Quetzalcoatl",
    )

    raw_mythology = "Name: Quetzalcoatl. Pantheon: Aztec. Feathered Serpent deity of wind and wisdom."
    rewritten_mythology = "Quetzalcoatl, the revered Feathered Serpent of the Aztec pantheon, rules wind and wisdom."

    # Mock the internal agent run inside execute_specialist_handoff
    mock_run_result = MagicMock()
    mock_run_result.output = raw_mythology
    mock_run_result.all_messages.return_value = []

    with patch("agent_octopus.specialists.load_mcp_config", return_value={}):
        with patch("pydantic_ai.Agent.run", new=AsyncMock(return_value=mock_run_result)):
            with patch("agent_octopus.specialists.apply_readability_pass", new=AsyncMock(return_value=rewritten_mythology)) as mock_pass:
                handoff_res = await execute_specialist_handoff(mock_ctx, req)
                assert handoff_res.output == rewritten_mythology
                mock_pass.assert_called_once_with(mock_ctx, raw_mythology, command_name="readable_text")


@pytest.mark.asyncio
async def test_non_registered_specialist_skips_readability():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    req = HandoffRequest(
        specialist="astronomer",
        task="Analyze stellar flare in Proxima Centauri",
    )

    raw_output = "Stellar flare analysis complete."

    mock_run_result = MagicMock()
    mock_run_result.output = raw_output
    mock_run_result.all_messages.return_value = []

    with patch("agent_octopus.specialists.load_mcp_config", return_value={}):
        with patch("pydantic_ai.Agent.run", new=AsyncMock(return_value=mock_run_result)):
            with patch("agent_octopus.specialists.apply_readability_pass", new=AsyncMock()) as mock_pass:
                handoff_res = await execute_specialist_handoff(mock_ctx, req)
                assert handoff_res.output == raw_output
                mock_pass.assert_not_called()
