from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="leads_crm",
    description="Specialist in CRM lead management, status progression, and email outreach drafting with Ninja CRM.",
    mcp_servers=["ninja-crm"],
    system_prompt=(
        "You are the Leads & CRM Specialist Agent. You interact with Ninja CRM to retrieve leads, "
        "transition their statuses, and draft personalized outreach emails.\n"
        "Follow the com command runbook closely (e.g. $$leads_get, $$leads_in_progress, $$leads_merge).\n"
        "If a command requires prior leads from the session, check the provided context summary and ledger.\n"
        "Use the `question` tool when selecting backlogs or confirming choices."
    ),
)
