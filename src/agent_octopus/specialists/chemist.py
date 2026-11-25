from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="chemist",
    description="Specialist in comparative chemistry, molecular structures, functional group manifolds, and synthesis reports.",
    mcp_servers=["chemist"],
    system_prompt=(
        "You are the Chemist Specialist Agent. You interact with the Chemist computational research "
        "platform for comparative chemistry, molecular structures, and functional group manifolds."
    ),
)
