import os
from typing import Literal
import logfire


def setup_observability(
    service_name: str = "agent-octopus",
    send_to_logfire: bool | Literal["if-token-present"] | None = "if-token-present",
    console: bool | None = None,
) -> None:
    """Configure Pydantic Logfire observability and instrument Pydantic AI.

    Args:
        service_name: Service name reported in telemetry.
        send_to_logfire: Whether to send to Logfire (defaults to 'if-token-present').
        console: Whether to log spans to terminal console. If None, respects LOGFIRE_CONSOLE
                 env var, defaulting to False in interactive CLI to preserve clean UI.
    """
    console_env = os.environ.get("LOGFIRE_CONSOLE")
    if console is None:
        console_val = None if console_env is not None else False
    else:
        console_val = console

    logfire.configure(
        service_name=service_name,
        send_to_logfire=send_to_logfire,
        console=console_val,
    )
    logfire.instrument_pydantic_ai()
