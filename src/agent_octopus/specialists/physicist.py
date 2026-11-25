from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="physicist",
    description="Specialist in comparative particle physics, subatomic particles, and quantum state manifolds.",
    mcp_servers=["physicist"],
    system_prompt=(
        "You are the Physicist Specialist Agent. You interact with the Physicist computational research "
        "platform for comparative particle physics, quantum state manifolds, and quantum cluster synthesis."
    ),
)
