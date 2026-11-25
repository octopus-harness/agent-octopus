from agent_octopus.models import SpecialistName
from .base import (
    SpecialistDefinition,
    READABILITY_ENHANCED_SPECIALISTS,
    apply_readability_pass,
    execute_specialist_handoff,
    load_mcp_config,
)
from .astronomer import SPECIALIST as astronomer_specialist
from .biologist import SPECIALIST as biologist_specialist
from .book_rhino import SPECIALIST as book_rhino_specialist
from .chemist import SPECIALIST as chemist_specialist
from .content_productivity import SPECIALIST as content_productivity_specialist
from .evox import SPECIALIST as evox_specialist
from .leads_crm import SPECIALIST as leads_crm_specialist
from .macronx import SPECIALIST as macronx_specialist
from .mythology_knowledge import SPECIALIST as mythology_knowledge_specialist
from .physicist import SPECIALIST as physicist_specialist
from .readability import SPECIALIST as readability_specialist
from .research_notes import SPECIALIST as research_notes_specialist
from .statesman import SPECIALIST as statesman_specialist

SPECIALISTS: dict[SpecialistName, SpecialistDefinition] = {
    "research_notes": research_notes_specialist,
    "readability": readability_specialist,
    "content_productivity": content_productivity_specialist,
    "leads_crm": leads_crm_specialist,
    "mythology_knowledge": mythology_knowledge_specialist,
    "astronomer": astronomer_specialist,
    "biologist": biologist_specialist,
    "chemist": chemist_specialist,
    "physicist": physicist_specialist,
    "statesman": statesman_specialist,
    "book_rhino": book_rhino_specialist,
    "macronx": macronx_specialist,
    "evox": evox_specialist,
}

__all__ = [
    "SpecialistDefinition",
    "SPECIALISTS",
    "READABILITY_ENHANCED_SPECIALISTS",
    "apply_readability_pass",
    "execute_specialist_handoff",
    "load_mcp_config",
]
