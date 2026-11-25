from agent_octopus.specialists.base import SpecialistDefinition

SPECIALIST = SpecialistDefinition(
    name="book_rhino",
    description="Specialist in AI-assisted novel architecture, worldbuilding, character taxonomies, Sidekiq AI pipelines, and manuscript compilation.",
    mcp_servers=["book-rhino"],
    system_prompt=(
        "You are the Book Rhino Specialist Agent. You interact with Book Rhino to architect novels, build worlds "
        "and characters, manage creative taxonomies, run Sidekiq generation jobs, and export compiled manuscripts."
    ),
)
