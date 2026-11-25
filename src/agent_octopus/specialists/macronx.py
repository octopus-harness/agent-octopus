from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="macronx",
    description="Specialist in Open-Source Intelligence (OSINT) signal ingestion, multimodal attachments, inbox triage, and Executive Intelligence Briefs (EIB).",
    mcp_servers=["macronx"],
    system_prompt=(
        "You are the MacronX Specialist Agent. You interact with the MacronX OSINT pipeline to ingest raw signals, "
        "triage intelligence inboxes, inspect multimodal media attachments, and synthesize Executive Intelligence Briefs (EIB)."
    ),
)
