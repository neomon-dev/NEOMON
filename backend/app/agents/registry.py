from app.agents.advocate import AdvocateAgent
from app.agents.citation_genealogy import CitationGenealogyAgent
from app.agents.conflict_adjudicator import ConflictAdjudicatorAgent
from app.agents.debate_moderator import DebateModeratorAgent
from app.agents.definitions import AGENT_DEFINITIONS, AgentDefinition
from app.agents.evidence_collector import EvidenceCollectorAgent
from app.agents.intelligence_planner import IntelligencePlannerAgent
from app.agents.methodology_auditor import MethodologyAuditorAgent
from app.agents.report_intelligence import ReportIntelligenceAgent
from app.agents.research_explorer import ResearchExplorerAgent
from app.agents.skeptic import SkepticAgent
from app.agents.source_intelligence import SourceIntelligenceAgent
from app.agents.temporal_intelligence import TemporalIntelligenceAgent

AGENT_CLASSES = {
    "intelligence_planner": IntelligencePlannerAgent,
    "research_explorer": ResearchExplorerAgent,
    "evidence_collector": EvidenceCollectorAgent,
    "advocate": AdvocateAgent,
    "skeptic": SkepticAgent,
    "methodology_auditor": MethodologyAuditorAgent,
    "source_intelligence": SourceIntelligenceAgent,
    "citation_genealogy": CitationGenealogyAgent,
    "temporal_intelligence": TemporalIntelligenceAgent,
    "debate_moderator": DebateModeratorAgent,
    "conflict_adjudicator": ConflictAdjudicatorAgent,
    "report_intelligence": ReportIntelligenceAgent,
}


def create_agent(identifier: str):
    agent_class = AGENT_CLASSES.get(identifier)
    if agent_class is None:
        raise KeyError(identifier)
    return agent_class()
