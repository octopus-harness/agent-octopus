from typing import Literal, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage
from rich.console import Console

from agent_octopus.config import Settings

SpecialistName = Literal[
    "research_notes",
    "content_productivity",
    "leads_crm",
    "mythology_knowledge",
    "astronomer",
    "biologist",
    "chemist",
    "physicist",
    "statesman",
    "book_rhino",
    "macronx",
    "evox",
]


class ComCommand(BaseModel):
    index: int
    name: str  # e.g. "$$add_research"
    raw_name: str  # e.g. "add_research"
    category: str = "general"  # e.g. "research", "crm", "mythology"
    args: str  # e.g. "[text]" or "-"
    description: str


class HandoffRequest(BaseModel):
    specialist: SpecialistName = Field(
        description="The target specialist agent to hand off work to"
    )
    task: str = Field(
        description="Detailed description of the task or user request to execute"
    )
    command_name: str | None = Field(
        default=None,
        description="Name of the com command being executed (e.g. '$$content_prompt' or 'content_prompt')",
    )
    context_summary: str | None = Field(
        default=None,
        description="Relevant conversational context or arguments needed for this task",
    )


class HandoffResult(BaseModel):
    specialist: str
    command_name: str | None = None
    summary: str
    output: str


@dataclass
class SessionContext:
    settings: Settings
    console: Console
    commands: list[ComCommand] = field(default_factory=list)
    shared_ledger: list[HandoffResult] = field(default_factory=list)
    specialist_histories: dict[str, list[ModelMessage]] = field(default_factory=dict)
