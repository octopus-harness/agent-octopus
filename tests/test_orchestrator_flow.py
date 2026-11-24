import pytest
from rich.console import Console
from pydantic_ai.models.test import TestModel

from agent_octopus.config import load_settings
from agent_octopus.models import SessionContext, ComCommand
from agent_octopus.orchestrator import create_orchestrator_agent


@pytest.mark.asyncio
async def test_orchestrator_startup_formatting():
    test_model = TestModel(call_tools=[], custom_output_text="Here is your numbered list of commands:\n1. $$add_research\n2. $$commands\nWhat would you like to do?")
    agent = create_orchestrator_agent(model=test_model)

    console = Console(quiet=True)
    settings = load_settings()
    cmds = [
        ComCommand(index=1, name="$$add_research", raw_name="add_research", args="[text]", description="Save note"),
        ComCommand(index=2, name="$$commands", raw_name="commands", args="-", description="List commands"),
    ]
    session = SessionContext(
        settings=settings,
        console=console,
        commands=cmds,
    )

    result = await agent.run(
        "Here are the commands from `com list`:\n1. $$add_research\n2. $$commands\nPlease format.",
        deps=session,
    )
    assert "Here is your numbered list" in result.output
