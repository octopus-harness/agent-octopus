from agent_octopus.mcp_loader import load_mcp_config
from agent_octopus.specialists import SPECIALISTS


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
    assert "Recommended Syncretica Plan" in mythology_spec.system_prompt
    assert "find_counterparts" in mythology_spec.system_prompt
    assert "compute_clusters" in mythology_spec.system_prompt
    assert "create_cluster_snapshot" in mythology_spec.system_prompt
    assert "generate_deep_synthesis" in mythology_spec.system_prompt
    assert "$$god_save_research" in mythology_spec.system_prompt
    assert mythology_spec.apply_readability_pass is True

