from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="biologist",
    description="Specialist in comparative biology, ecology, organismal taxonomy, biomes, and species manifolds.",
    mcp_servers=["biologist"],
    system_prompt=(
        "You are the Biologist Specialist Agent. You interact with the Biologist computational research "
        "platform for comparative biology, ecology, and evolutionary convergence inquiries over pgvector."
    ),
)
