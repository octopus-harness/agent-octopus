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


KNOWN_SYNCRETICA_TOOLS = sorted([
    "compute_clusters",
    "create_cluster_snapshot",
    "list_cluster_snapshots",
    "get_cluster_snapshot",
    "delete_cluster_snapshot",
    "get_cluster_group",
    "create_cluster_report",
    "generate_deep_synthesis",
    "wait_for_cluster_report",
    "list_cluster_reports",
    "get_cluster_report",
    "get_report_summary",
    "get_report_sub_report",
    "find_counterparts",
    "search",
    "list_gods",
    "get_god",
    "create_god",
    "update_god",
    "delete_god",
    "upsert_gods_batch",
    "generate_god_embedding",
    "populate_god_myth",
    "populate_gods_bulk",
    "list_myths",
    "get_myth",
    "create_myth",
    "update_myth",
    "delete_myth",
    "generate_myth_embedding",
    "populate_myths_bulk",
    "list_pantheons",
    "get_pantheon",
    "create_pantheon",
    "update_pantheon",
    "delete_pantheon",
    "upsert_pantheons_batch",
    "populate_pantheons",
    "populate_pantheon_gods",
    "list_jobs",
    "get_job_status",
    "wait_for_job",
    "get_platform_status",
    "get_settings",
    "update_context_window",
    "trigger_bulk_embeddings",
    "get_openapi_spec",
    "$$god_save_research",
    "god_save_research",
    "$$add_research",
    "add_research",
], key=len, reverse=True)


def extract_plan_options(text: str) -> list[PlanOption]:
    """
    Parses a markdown response and extracts plan options from the
    final contiguous numbered list (1..N) in the response (e.g. 'Recommended Next Steps & Actions',
    'Operational Next Steps', 'Recommended Plan', etc.).
    """
    if not text:
        return []

    # 1. Match all potential numbered items: "1. ...", "### 1. ...", "1 ...", etc.
    item_pattern = re.compile(
        r"(?:^|\n)(?:###?\s*)?(\d+)(?:[\.\)]\s*|\s+)(?:\*\*)?(.*?)(?:\*\*)?(?=\n|$)",
        re.MULTILINE,
    )
    matches = list(item_pattern.finditer(text))
    if not matches:
        return []

    # 2. Group into contiguous sequences starting with 1 (e.g. [1, 2, 3...])
    sequences: list[list[re.Match]] = []
    current_seq: list[re.Match] = []
    for m in matches:
        num = int(m.group(1))
        if num == 1:
            if current_seq:
                sequences.append(current_seq)
            current_seq = [m]
        elif current_seq and num == int(current_seq[-1].group(1)) + 1:
            current_seq.append(m)
        else:
            if current_seq:
                sequences.append(current_seq)
                current_seq = []
    if current_seq:
        sequences.append(current_seq)

    if not sequences:
        return []

    # Per grill-me requirement: Pick the last contiguous numbered sequence in the text
    chosen_matches = sequences[-1]
    options: list[PlanOption] = []

    for i, m in enumerate(chosen_matches):
        step_num = int(m.group(1))
        raw_header = m.group(2).strip()

        # Parse title and header_rest using markdown bolding, em-dash, en-dash, hyphen, or colon
        bold_match = re.search(r"^\s*\*\*(.*?)\*\*", raw_header)
        if bold_match:
            title = bold_match.group(1).strip()
            header_rest = raw_header[bold_match.end():].lstrip(":—-– ").strip()
        elif "**" in raw_header:
            title_part, rest_part = raw_header.split("**", 1)
            title = title_part.strip().strip("*").strip()
            header_rest = rest_part.lstrip(":—-– ").strip()
        else:
            delim_match = re.search(r"\s*(?:—|–|\s-\s|:)\s*", raw_header)
            if delim_match:
                title = raw_header[:delim_match.start()].strip()
                header_rest = raw_header[delim_match.end():].strip()
            else:
                title = raw_header.strip("*:").strip()
                header_rest = ""

        # Item body is from the end of this header to the start of the next item (or section end)
        start_pos = m.end()
        if i + 1 < len(chosen_matches):
            end_pos = chosen_matches[i + 1].start()
        else:
            trailing = text[chosen_matches[i].start():]
            section_end = re.search(r"\n(?:#{1,2}\s+[A-Za-z]|What changed:|---{3,})", trailing, re.IGNORECASE)
            end_pos = chosen_matches[i].start() + section_end.start() if section_end else len(text)

        item_body = (header_rest + "\n" + text[start_pos:end_pos]).strip()
        raw_text = re.sub(r"^[#\s]+", "", text[m.start():end_pos].strip())

        # Find tool references
        tool_name = None
        details = ""

        # Check for explicit "Tool: <tool_name> ..." line
        tool_line_match = re.search(r"-\s*Tool:\s*`?([^\n`]+)`?", item_body, re.IGNORECASE)
        if tool_line_match:
            raw_tool = tool_line_match.group(1).strip()
            tool_matches = []
            for known in KNOWN_SYNCRETICA_TOOLS:
                pattern = rf"(?:`|\b|^|(?<=[\s])){re.escape(known)}(?:`|\b|$|(?=[\s:,]))"
                tm = re.search(pattern, raw_tool)
                if tm:
                    tool_matches.append((tm.start(), known))
            if tool_matches:
                tool_matches.sort(key=lambda x: (x[0], -len(x[1])))
                tool_name = tool_matches[0][1]
            if not tool_name:
                tool_name = raw_tool.split()[0].rstrip(",:")
            remainder = raw_tool.replace(tool_name, "").strip().strip(",:")
            if remainder:
                details = remainder
        else:
            # Check for known tools in the body (prefer earliest occurrence in body)
            tool_matches = []
            for known in KNOWN_SYNCRETICA_TOOLS:
                pattern = rf"(?:`|\b|^|(?<=[\s])){re.escape(known)}(?:`|\b|$|(?=[\s:,]))"
                tm = re.search(pattern, item_body)
                if tm:
                    tool_matches.append((tm.start(), known))
            if tool_matches:
                tool_matches.sort(key=lambda x: (x[0], -len(x[1])))
                tool_name = tool_matches[0][1]
                param_match = re.search(rf"(?:\*\*)?`?{re.escape(tool_name)}`?(?:\*\*)?\s*\(([^)]+)\)", item_body)
                if param_match:
                    details = f"({param_match.group(1).strip()})"

        # Dynamic tool detection fallback (e.g. tool_name(...) or $$command)
        if not tool_name:
            fn_match = re.search(r"(?:`|\b)([a-z_][a-z0-9_]*)\s*\(([^)]*)\)", item_body)
            cmd_match = re.search(r"\$\$([a-z_][a-z0-9_]*)", item_body)
            if fn_match:
                tool_name = fn_match.group(1)
                details = f"({fn_match.group(2).strip()})"
            elif cmd_match:
                tool_name = f"$${cmd_match.group(1)}"

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
