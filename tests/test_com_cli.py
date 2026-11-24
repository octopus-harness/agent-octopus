from agent_octopus.com_cli import run_com_list, run_com_get


def test_run_com_list():
    raw, cmds = run_com_list()
    assert len(cmds) >= 10
    assert any(c.name == "$$add_research" for c in cmds)
    assert any(c.name == "$$content_prompt" for c in cmds)
    assert any(c.name == "$$god_find" for c in cmds)

    # Check 1-based indexing
    assert cmds[0].index == 1
    assert cmds[1].index == 2

    # Check category parsing
    research_cmd = next(c for c in cmds if c.name == "$$add_research")
    assert research_cmd.category == "research"
    assert research_cmd.args == "`[text]`"
    assert "Research Project" in research_cmd.description

    mythology_cmd = next(c for c in cmds if c.name == "$$god_find")
    assert mythology_cmd.category == "mythology"
    assert mythology_cmd.args == "`<name>`"

    crm_cmd = next(c for c in cmds if c.name == "$$leads_get")
    assert crm_cmd.category == "crm"
    assert crm_cmd.args == "-"

    # General must be first, Help must be last
    assert cmds[0].category == "general"
    assert cmds[-1].category == "help"


def test_run_com_get():
    content = run_com_get("add_research")
    assert "Usage: $$add_research" in content
    assert "tools.noteking" in content

    # Test with $$ prefix
    content_with_dollar = run_com_get("$$content_prompt")
    assert "Usage: $$content_prompt" in content_with_dollar
