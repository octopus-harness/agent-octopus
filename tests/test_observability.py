import pytest
from pydantic_ai import Agent
from agent_octopus.observability import setup_observability


def test_setup_observability():
    # Setup observability without errors
    setup_observability(service_name="test-agent-octopus", send_to_logfire="if-token-present", console=False)

    # Creating an agent should work cleanly
    agent = Agent("test", name="test_agent")
    res = agent.run_sync("hello")
    assert res.output == "success (no tool calls)"
