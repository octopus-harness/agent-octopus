import re
from dataclasses import dataclass


@dataclass
class PlanOption:
    index: int
    title: str
    tool_name: str | None
    action_text: str
    label: str
    raw_text: str = ""


KNOWN_SYNCRETICA_TOOLS = [
    "compute_clusters",
    "create_cluster_snapshot",
    "create_cluster_report",
    "generate_deep_synthesis",
    "wait_for_cluster_report",
    "find_counterparts",
    "$$god_save_research",
    "god_save_research",
    "search",
    "list_gods",
    "list_myths",
    "get_god",
    "get_myth",
]


def extract_plan_options(text: str) -> list[PlanOption]:
    """
    Parses a markdown response and extracts plan options from the
    'Recommended Syncretica Plan' (or similar plan) section.
    """
    if not text:
        return []

    # 1. Locate the start of the plan / actions section
    match = re.search(
        r"(?:^|\n)[#\s]*Recommended\s+(?:Syncretica\s+)?(?:Next Steps & Actions|Actions|Plan)\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return []

    plan_section = text[match.end():]

    # Stop at the next major section if any (e.g. "## ", "What changed:", or horizontal rule)
    section_end = re.search(r"\n(?:#{1,2}\s+[A-Za-z]|What changed:|---{3,})", plan_section, re.IGNORECASE)
    if section_end:
        plan_section = plan_section[:section_end.start()]

    # 2. Split into numbered items: "1. ...", "### 1. ...", "1 ...", etc.
    # Pattern to find numbered item headers
    item_pattern = re.compile(
        r"(?:^|\n)(?:###?\s*)?(\d+)(?:[\.\)]\s*|\s+)(?:\*\*)?(.*?)(?:\*\*)?(?=\n|$)",
        re.MULTILINE,
    )

    matches = list(item_pattern.finditer(plan_section))
    if not matches:
        return []

    options: list[PlanOption] = []
    for i, m in enumerate(matches):
        step_num = int(m.group(1))
        raw_header = m.group(2).strip()

        # If header contains a bold title: **Title**: <optional rest> or Title**: <optional rest>
        if "**" in raw_header:
            title_part, rest_part = raw_header.split("**", 1)
            title = title_part.strip().strip("*").strip()
            header_rest = rest_part.lstrip(":").strip()
        elif ":" in raw_header:
            title_part, rest_part = raw_header.split(":", 1)
            title = title_part.strip()
            header_rest = rest_part.strip()
        else:
            title = raw_header.strip("*:").strip()
            header_rest = ""

        # Item body is from the end of this header to start of next (or end of section)
        start_pos = m.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(plan_section)
        item_body = (header_rest + "\n" + plan_section[start_pos:end_pos]).strip()
        raw_text = re.sub(r"^[#\s]+", "", plan_section[m.start():end_pos].strip())

        # Find tool references
        tool_name = None
        details = ""

        # Check for explicit "Tool: <tool_name> ..." line
        tool_line_match = re.search(r"-\s*Tool:\s*`?([^\n`]+)`?", item_body, re.IGNORECASE)
        if tool_line_match:
            raw_tool = tool_line_match.group(1).strip()
            # Extract tool name from raw_tool
            for known in KNOWN_SYNCRETICA_TOOLS:
                if known in raw_tool:
                    tool_name = known
                    break
            if not tool_name:
                tool_name = raw_tool.split()[0].rstrip(",:")
            # Additional details from the line
            remainder = raw_tool.replace(tool_name, "").strip().strip(",:")
            if remainder:
                details = remainder
        else:
            # Check for known tools in the body
            for known in KNOWN_SYNCRETICA_TOOLS:
                pattern = rf"(?:`|\b|^|(?<=[\s])){re.escape(known)}(?:`|\b|$|(?=[\s:,]))"
                if re.search(pattern, item_body):
                    tool_name = known
                    # Look for parameters right after: e.g. `compute_clusters` (target: "God", level: 5)
                    # or `compute_clusters(target: "God", level: 5)`
                    param_match = re.search(rf"(?:\*\*)?`?{re.escape(known)}`?(?:\*\*)?\s*\(([^)]+)\)", item_body)
                    if param_match:
                        details = f"({param_match.group(1).strip()})"
                    break

        # Fallback check in title itself
        if not tool_name:
            for known in KNOWN_SYNCRETICA_TOOLS:
                if known.lower() in title.lower():
                    tool_name = known
                    break

        label = f"{step_num}. {title}"
        if tool_name:
            clean_tool = tool_name.lstrip("$")
            label += f" ({clean_tool})"

        action_text = f"Execute plan step {step_num}: {title}"
        if tool_name:
            action_text += f" using {tool_name}"
            if details:
                action_text += f" {details}"

        options.append(
            PlanOption(
                index=step_num,
                title=title,
                tool_name=tool_name,
                action_text=action_text.strip(),
                label=label,
                raw_text=raw_text,
            )
        )

    return options
