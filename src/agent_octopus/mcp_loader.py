import json
import os
from pathlib import Path
from typing import Any
from pydantic_ai import RunContext
from pydantic_ai.mcp import StdioTransport, MCPToolset, CallToolFunc

from agent_octopus.config import MCPConfigFile, MCPServerDefinition

MAX_TOOL_OUTPUT_CHARS: int = 50_000


def summarize_clusters_result(
    data: dict[str, Any],
    max_clusters: int = 15,
    max_members_per_cluster: int = 6,
    max_singletons: int = 10,
) -> dict[str, Any]:
    """
    Summarizes massive live connected-components cluster results (e.g. from compute_clusters).
    Instead of returning full entity models for hundreds of clusters and singletons (which can
    exceed 600KB and blow LLM context windows), extracts essential cluster metadata, top cluster
    groups with sample member names, and singleton counts.
    """
    if not isinstance(data, dict):
        return data

    clusters = data.get("clusters")
    singletons = data.get("singletons")
    if not isinstance(clusters, list) or not isinstance(singletons, list):
        return data

    summarized_clusters = []
    for c in clusters[:max_clusters]:
        if isinstance(c, dict):
            members = c.get("members", [])
            sample_members = [
                m.get("name", m.get("title", str(m))) if isinstance(m, dict) else str(m)
                for m in members[:max_members_per_cluster]
            ]
            summarized_clusters.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "size": c.get("size", len(members)),
                "shared_themes": c.get("shared_themes", []),
                "pantheons": c.get("pantheons", []),
                "sample_members": sample_members,
                "total_members": len(members),
            })
        else:
            summarized_clusters.append(c)

    sample_singletons = [
        s.get("name", s.get("title", str(s))) if isinstance(s, dict) else str(s)
        for s in singletons[:max_singletons]
    ]

    summary = {
        "target_type": data.get("target_type"),
        "level": data.get("level"),
        "distance_threshold": data.get("distance_threshold"),
        "full_coverage": data.get("full_coverage"),
        "total_embedded_count": data.get("total_embedded_count"),
        "unembedded_count": data.get("unembedded_count"),
        "clusters_count": data.get("clusters_count", len(clusters)),
        "singletons_count": data.get("singletons_count", len(singletons)),
        "largest_cluster_size": data.get("largest_cluster_size"),
        "top_clusters": summarized_clusters,
        "sample_singletons": sample_singletons,
    }
    if len(clusters) > max_clusters:
        summary["omitted_clusters_count"] = len(clusters) - max_clusters
    if len(singletons) > max_singletons:
        summary["omitted_singletons_count"] = len(singletons) - max_singletons

    return summary


def sanitize_mcp_tool_result(result: Any, max_chars: int = MAX_TOOL_OUTPUT_CHARS) -> Any:
    """
    Sanitizes and bounds MCP tool outputs to prevent context window overflow.
    Specifically summarizes cluster payloads and truncates any output exceeding max_chars.
    """
    # 1. Check for clustering results in dict or JSON string
    if isinstance(result, dict):
        if "clusters" in result and "singletons" in result:
            result = summarize_clusters_result(result)
        elif "data" in result and isinstance(result["data"], dict) and "clusters" in result["data"]:
            result = summarize_clusters_result(result["data"])
    elif isinstance(result, str) and result.strip().startswith("{") and '"clusters"' in result and '"singletons"' in result:
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                if "clusters" in parsed and "singletons" in parsed:
                    result = summarize_clusters_result(parsed)
                elif "data" in parsed and isinstance(parsed["data"], dict) and "clusters" in parsed["data"]:
                    result = summarize_clusters_result(parsed["data"])
        except Exception:
            pass

    # 2. Bound payload character length
    if isinstance(result, str):
        if len(result) > max_chars:
            result = (
                result[:max_chars]
                + f"\n\n[Warning: Tool output exceeded limit and was truncated ({len(result)} chars -> {max_chars} chars). Refine query parameters for more specific results.]"
            )
    elif isinstance(result, (dict, list)):
        try:
            serialized = json.dumps(result)
            if len(serialized) > max_chars:
                return (
                    serialized[:max_chars]
                    + f"\n\n[Warning: Tool output exceeded limit and was truncated ({len(serialized)} chars -> {max_chars} chars). Refine query parameters for more specific results.]"
                )
        except Exception:
            pass

    return result


NON_NUMERIC_KEYS = {
    "title",
    "name",
    "body",
    "description",
    "prompt",
    "text",
    "summary",
    "query",
    "q",
    "task",
    "content",
    "message",
    "email",
    "url",
    "target_type",
}


def coerce_mcp_tool_args(tool_args: dict[str, Any]) -> dict[str, Any]:
    """
    Coerces stringified numbers and booleans into native types for MCP tools.
    MCP servers (e.g. Node/FastMCP with Zod) strictly reject string types for integer schemas,
    causing validation errors when LLMs serialize numbers as strings (e.g. project_id="3").
    """
    if not isinstance(tool_args, dict):
        return tool_args
    cleaned = dict(tool_args)
    for k, v in cleaned.items():
        if k in NON_NUMERIC_KEYS:
            continue
        if isinstance(v, str):
            stripped = v.strip()
            # Coerce integers for ID/count/level/limit parameters
            if (
                k.endswith("_id")
                or k in ("id", "level", "limit", "batch_size", "pinned_position", "count", "size")
            ) and (
                stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit())
            ):
                try:
                    cleaned[k] = int(stripped)
                except ValueError:
                    pass
            # Coerce booleans
            elif k in ("pinned", "full_coverage", "render_markdown", "enabled", "active"):
                if stripped.lower() == "true":
                    cleaned[k] = True
                elif stripped.lower() == "false":
                    cleaned[k] = False
    return cleaned


async def process_mcp_tool_call(
    ctx: RunContext[Any],
    call_tool: CallToolFunc,
    name: str,
    tool_args: dict[str, Any],
) -> Any:
    """
    Intercepts MCP tool calls to coerce argument types, bound responses, and summarize
    high-cardinality payloads, preventing validation and context window errors.
    """
    coerced_args = coerce_mcp_tool_args(tool_args)
    raw_result = await call_tool(name, coerced_args)
    if name == "compute_clusters" and isinstance(raw_result, dict):
        return summarize_clusters_result(raw_result.get("data", raw_result))
    return sanitize_mcp_tool_result(raw_result)


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
    return MCPToolset(transport, process_tool_call=process_mcp_tool_call)

