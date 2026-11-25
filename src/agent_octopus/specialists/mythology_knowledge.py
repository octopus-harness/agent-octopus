from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="mythology_knowledge",
    description="Specialist in comparative mythology, gods, myths, counterparts, and Wikidata entity queries.",
    mcp_servers=["syncretica", "wikidata"],
    system_prompt=(
        "You are the Mythology & Knowledge Specialist Agent. You interact with Syncretica and Wikidata "
        "to find gods, myths, cross-pantheon counterparts, and knowledge entities.\n"
        "When running commands like $$god_find, generate spelling variants and search as instructed.\n"
        "Use the `question` tool if clarification is required."
    ),
)
