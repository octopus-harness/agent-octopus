from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="statesman",
    description="Specialist in comparative geopolitics, statecraft, urban power centers, and cross-continental manifolds.",
    mcp_servers=["statesman"],
    system_prompt=(
        "You are the Statesman Specialist Agent. You interact with the Statesman computational research "
        "platform for comparative geopolitics, statecraft, and urban power centers over pgvector."
    ),
)
