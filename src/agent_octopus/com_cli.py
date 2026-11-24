import subprocess
import re
from agent_octopus.models import ComCommand


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
    # COMMAND              ARGS          DESCRIPTION
    # -------------------  ------------  -----------
    # $$add_research       `[text]`      Save the provided text...
    lines = raw_output.splitlines()
    in_table = False
    idx = 1

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("COMMAND") and "DESCRIPTION" in stripped:
            in_table = True
            continue
        if in_table and stripped.startswith("---"):
            continue
        if in_table:
            # Parse columns: COMMAND, ARGS, DESCRIPTION
            # Columns can be separated by 2 or more spaces
            parts = re.split(r"\s{2,}", stripped)
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
                    args=args,
                    description=desc,
                )
            )
            idx += 1

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
