from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="astronomer",
    description="Specialist in comparative astrophysics, cosmic structures, star systems, celestial body manifolds, and pgvector clustering.",
    mcp_servers=["astronomer"],
    system_prompt=(
        "You are the Astronomer Specialist Agent. You interact with the Astronomer computational research "
        "platform for comparative astrophysics, stellar systems, and celestial body manifolds over pgvector."
    ),
)
