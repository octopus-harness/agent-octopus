from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="evox",
    description="Specialist in structured Song AST authoring and PDF songbook compilation with aligned chords and Table of Contents.",
    mcp_servers=["evox"],
    system_prompt=(
        "You are the Evox Specialist Agent. You interact with Evox to author Song ASTs and compile "
        "publication-quality PDF songbooks with multi-column lyrics, aligned chords, and automatic Table of Contents."
    ),
)
