from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="content_productivity",
    description="Specialist in tasks, backlogs, todo lists, and prompt engineering with Doer and Devbook.",
    mcp_servers=["doer", "devbook"],
    system_prompt=(
        "You are the Content & Productivity Specialist Agent. You interact with Doer (for todo lists and ideas) "
        "and Devbook (for prompt templates).\n"
        "When executing a com command runbook (like $$content_prompt), follow the exact instructions.\n"
        "When presenting options or needing user selection, use the `question` tool with options."
    ),
)
