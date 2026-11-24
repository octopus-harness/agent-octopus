import json
import os
from pathlib import Path
from contextlib import AsyncExitStack
from pydantic_ai.mcp import StdioTransport, MCPToolset

from agent_octopus.config import MCPConfigFile, MCPServerDefinition


def load_mcp_config(config_path: str = "mcp_config.json") -> dict[str, MCPServerDefinition]:
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"MCP configuration file not found at: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    parsed = MCPConfigFile.model_validate(data)
    return parsed.mcpServers


def create_toolset_for_server(name: str, definition: MCPServerDefinition) -> MCPToolset:
    # Merge existing environment with configured env
    merged_env = os.environ.copy()
    merged_env.update(definition.env)

    transport = StdioTransport(
        command=definition.command,
        args=definition.args,
        env=merged_env,
    )
    return MCPToolset(transport)
