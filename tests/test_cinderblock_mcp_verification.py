import pytest
from agent_octopus.mcp_loader import load_mcp_config, create_toolset_for_server
from agent_octopus.plan_parser import (
    CINDERBLOCK_DOMAIN_TOOLS,
    CORE_CINDERBLOCK_TOOLS,
    EXTENDED_CLUSTER_REPORT_TOOLS,
    COMMON_CINDERBLOCK_TOOLS,
    SYNCRETICA_TOOLS,
    ASTRONOMER_TOOLS,
    BIOLOGIST_TOOLS,
    CHEMIST_TOOLS,
    PHYSICIST_TOOLS,
    STATESMAN_TOOLS,
)


# Expected tool counts per server: Syncretica has 47, the other 5 have 52
EXPECTED_COUNTS = {
    "syncretica": 47,
    "astronomer": 52,
    "biologist": 52,
    "chemist": 52,
    "physicist": 52,
    "statesman": 52,
}


@pytest.mark.asyncio
@pytest.mark.parametrize("server_name", list(CINDERBLOCK_DOMAIN_TOOLS.keys()))
async def test_cinderblock_mcp_tools_contract(server_name: str):
    """
    Spawns each Cinderblock MCP server over stdio transport and verifies that
    100% of the tools defined in CINDERBLOCK_DOMAIN_TOOLS exist in the MCP server,
    with zero missing tools and zero unexpected extra tools.
    """
    mcp_defs = load_mcp_config("mcp_config.json")
    assert server_name in mcp_defs, f"Missing MCP config definition for '{server_name}'"

    toolset = create_toolset_for_server(server_name, mcp_defs[server_name])
    async with toolset:
        mcp_tools = await toolset.list_tools()
        actual_names = {t.name for t in mcp_tools}
        expected_names = set(CINDERBLOCK_DOMAIN_TOOLS[server_name])

        missing = expected_names - actual_names
        extra = actual_names - expected_names

        assert not missing, f"Server '{server_name}' is missing expected tools: {missing}"
        assert not extra, f"Server '{server_name}' registered extra unlisted tools: {extra}"
        assert len(actual_names) == EXPECTED_COUNTS[server_name]


@pytest.mark.asyncio
@pytest.mark.parametrize("server_name,primary_list_tool,secondary_list_tool,container_list_tool", [
    ("syncretica", "list_gods", "list_myths", "list_pantheons"),
    ("astronomer", "list_star_systems", "list_celestial_bodies", "list_cosmic_structures"),
    ("biologist", "list_species", "list_organisms", "list_biomes"),
    ("chemist", "list_molecules", "list_functional_groups", "list_chemical_classes"),
    ("physicist", "list_subatomic_particles", "list_quantum_states", "list_particle_groups"),
    ("statesman", "list_countries", "list_cities", "list_continents"),
])
async def test_cinderblock_mcp_safe_tool_execution(
    server_name: str,
    primary_list_tool: str,
    secondary_list_tool: str,
    container_list_tool: str,
):
    """
    Executes safe read-only MCP operations against each running Cinderblock MCP server:
    - get_platform_status: verifies environment status is 'ok'
    - get_settings: retrieves platform configuration
    - primary, secondary, and container list tools with limit=1
    - keyword search with limit=1
    """
    mcp_defs = load_mcp_config("mcp_config.json")
    toolset = create_toolset_for_server(server_name, mcp_defs[server_name])

    async with toolset:
        # 1. Platform status
        try:
            status = await toolset.direct_call_tool("get_platform_status", {})
        except Exception as e:
            pytest.skip(f"Backend for {server_name} unreachable: {e}")

        assert isinstance(status, dict)
        assert status.get("status") == "ok"
        assert "counts" in status or "environment" in status

        # 2. Settings
        settings_res = await toolset.direct_call_tool("get_settings", {})
        assert isinstance(settings_res, dict)

        # 3. Primary list tool
        primary_res = await toolset.direct_call_tool(primary_list_tool, {"limit": 1})
        assert isinstance(primary_res, dict)
        assert "data" in primary_res
        assert len(primary_res["data"]) <= 1

        # 4. Secondary list tool
        secondary_res = await toolset.direct_call_tool(secondary_list_tool, {"limit": 1})
        assert isinstance(secondary_res, dict)
        assert "data" in secondary_res
        assert len(secondary_res["data"]) <= 1

        # 5. Container list tool
        container_res = await toolset.direct_call_tool(container_list_tool, {"limit": 1})
        assert isinstance(container_res, dict)
        assert "data" in container_res
        assert len(container_res["data"]) <= 1

        # 6. Search
        search_res = await toolset.direct_call_tool("search", {"q": "a", "limit": 1})
        assert isinstance(search_res, dict)
        assert "data" in search_res or "results" in search_res
