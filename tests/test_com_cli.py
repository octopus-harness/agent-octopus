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


def test_run_com_get():
    content = run_com_get("add_research")
    assert "Usage: $$add_research" in content
    assert "tools.noteking" in content

    # Test with $$ prefix
    content_with_dollar = run_com_get("$$content_prompt")
    assert "Usage: $$content_prompt" in content_with_dollar
