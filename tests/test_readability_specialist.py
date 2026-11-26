import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from rich.console import Console

from agent_octopus.config import load_settings
from agent_octopus.models import SessionContext, HandoffRequest, HandoffResult
from agent_octopus.specialists import (
    SPECIALISTS,
    READABILITY_ENHANCED_SPECIALISTS,
    apply_readability_pass,
    clean_readability_output,
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


def test_clean_readability_output_strips_changelogs_and_preambles():
    # 1. Trailing "Changes made:" block with bullets
    text_with_changelog = """## 🔱 ATUM — Egyptian Creator God

- Name: Atum (ID: 676)
- Pantheon: Egyptian

Changes made:

 • Removed all em-dashes (replaced with periods and commas where needed)
 • Trimmed academic jargon where possible while preserving meaning and all factual content
 • Cleaned up parallel structure in lists
 • Kept all original detail, structure, and information intact
 • Applied punchy declarative rhythm where sentences felt bloated"""

    cleaned = clean_readability_output(text_with_changelog)
    assert "Changes made:" not in cleaned
    assert "Removed all em-dashes" not in cleaned
    assert "## 🔱 ATUM — Egyptian Creator God" in cleaned
    assert "- Pantheon: Egyptian" in cleaned

    # 2. Leading preamble
    text_with_preamble = """Here is the rewritten text in your voice:

Odin is the Allfather in Norse cosmology."""
    cleaned_preamble = clean_readability_output(text_with_preamble)
    assert cleaned_preamble == "Odin is the Allfather in Norse cosmology."

    # 3. Trailing "What changed:" with markdown hr
    text_with_hr_and_what_changed = """Thor wields Mjolnir.

---

What changed:
- Removed filler words
- Made tone grounded"""
    cleaned_hr = clean_readability_output(text_with_hr_and_what_changed)
    assert cleaned_hr == "Thor wields Mjolnir."

    # 4. Clean text with tables and markdown untouched
    clean_text = """| Deity | Distance |
|---|---|
| Ptah | 0.325 |"""
    assert clean_readability_output(clean_text) == clean_text
    assert clean_readability_output("") == ""


@pytest.mark.asyncio
async def test_apply_readability_pass_strips_changelog():
    console = Console(quiet=True)
    session = SessionContext(settings=load_settings(), console=console)
    mock_ctx = MagicMock()
    mock_ctx.deps = session

    raw_text = "Raw deity info"
    output_with_meta = """Polished deity profile.

Changes made:
- Removed buzzwords"""

    mock_handoff_result = HandoffResult(
        specialist="readability",
        command_name="readable_text",
        summary="Rewrote text",
        output=output_with_meta,
    )

    with patch("agent_octopus.specialists.execute_specialist_handoff", new=AsyncMock(return_value=mock_handoff_result)):
        res = await apply_readability_pass(mock_ctx, raw_text)
        assert res == "Polished deity profile."
        assert "Changes made:" not in res

