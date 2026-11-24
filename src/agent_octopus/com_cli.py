import subprocess
import re
from agent_octopus.models import ComCommand


def category_sort_key(cat: str) -> tuple[int, str]:
    """
    Returns a sort key ensuring 'General' is always first (rank 0),
    'Help' is always last (rank 2), and other categories are in between (rank 1).
    """
    c = cat.lower()
    if c == "general":
        return (0, c)
    if c == "help":
        return (2, c)
    return (1, c)


def sort_commands_by_category(commands: list[ComCommand]) -> list[ComCommand]:
    """
    Sorts commands so that 'General' is always at the top and 'Help' is always at the bottom,
    with other categories in between, and re-indexes them sequentially (1..N).
    """
    sorted_cmds = sorted(
        commands,
        key=lambda c: (category_sort_key(c.category), c.raw_name),
    )
    reindexed: list[ComCommand] = []
    for i, c in enumerate(sorted_cmds, start=1):
        reindexed.append(
            ComCommand(
                index=i,
                name=c.name,
                raw_name=c.raw_name,
                category=c.category,
                args=c.args,
                description=c.description,
            )
        )
    return reindexed


def run_com_list(com_bin: str = "com") -> tuple[str, list[ComCommand]]:
    """
    Executes `com list` and parses the output into a list of ComCommand objects.
    Returns (raw_output, parsed_commands).
    """
    result = subprocess.run(
        [com_bin, "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to execute `{com_bin} list`: {result.stderr.strip()}")

    raw_output = result.stdout
    commands: list[ComCommand] = []

    # Lines typically have:
    # 10 commands available:
    #
    # COMMAND              CATEGORY   ARGS          DESCRIPTION
    # -------------------  ---------  ------------  -----------
    # $$add_research       research   `[text]`      Save the provided text...
    lines = raw_output.splitlines()
    in_table = False
    has_category = False
    idx = 1

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("COMMAND") and "DESCRIPTION" in stripped:
            in_table = True
            has_category = "CATEGORY" in stripped
            continue
        if in_table and stripped.startswith("---"):
            continue
        if in_table:
            # Parse columns separated by 2 or more spaces
            parts = re.split(r"\s{2,}", stripped)
            if has_category:
                if len(parts) >= 4:
                    name = parts[0].strip()
                    category = parts[1].strip()
                    args = parts[2].strip()
                    desc = "  ".join(parts[3:]).strip()
                elif len(parts) == 3:
                    name = parts[0].strip()
                    category = parts[1].strip()
                    args = "-"
                    desc = parts[2].strip()
                elif len(parts) == 2:
                    name = parts[0].strip()
                    category = "general"
                    args = "-"
                    desc = parts[1].strip()
                else:
                    tokens = stripped.split(maxsplit=3)
                    if len(tokens) == 4:
                        name, category, args, desc = tokens
                    elif len(tokens) == 3:
                        name, category, desc = tokens
                        args = "-"
                    elif len(tokens) == 2:
                        name, desc = tokens
                        category = "general"
                        args = "-"
                    else:
                        continue
            else:
                category = "general"
                if len(parts) >= 3:
                    name = parts[0].strip()
                    args = parts[1].strip()
                    desc = "  ".join(parts[2:]).strip()
                elif len(parts) == 2:
                    name = parts[0].strip()
                    args = "-"
                    desc = parts[1].strip()
                else:
                    tokens = stripped.split(maxsplit=2)
                    if len(tokens) == 3:
                        name, args, desc = tokens
                    elif len(tokens) == 2:
                        name, desc = tokens
                        args = "-"
                    else:
                        continue

            raw_name = name.removeprefix("$$")
            commands.append(
                ComCommand(
                    index=idx,
                    name=name if name.startswith("$$") else f"$${name}",
                    raw_name=raw_name,
                    category=category,
                    args=args,
                    description=desc,
                )
            )
            idx += 1

    commands = sort_commands_by_category(commands)
    return raw_output, commands


def run_com_get(name: str, com_bin: str = "com") -> str:
    """
    Executes `com get <name>` to read the markdown definition of a command.
    """
    cleaned_name = name.strip().removeprefix("$$")
    result = subprocess.run(
        [com_bin, "get", cleaned_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return f"Error: Command `{name}` could not be retrieved from `{com_bin}`. {result.stderr.strip()}"
    return result.stdout
