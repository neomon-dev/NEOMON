from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDefinition:
    identifier: str
    name: str
    description: str
    system_instructions: str


AGENT_DEFINITIONS = [
    AgentDefinition("intelligence_planner", "Intelligence Planner", "Breaks questions into testable claims.", "Plan only; do not invent evidence."),
    AgentDefinition("research_explorer", "Research Explorer", "Finds candidate sources.", "Explore only; report source URLs, not unsupported conclusions."),
    AgentDefinition("evidence_collector", "Evidence Collector", "Extracts source-grounded passages.", "Collect exact evidence and preserve metadata."),
    AgentDefinition("advocate", "Advocate", "Builds the strongest supported argument.", "Argue only from supplied evidence."),
    AgentDefinition("skeptic", "Skeptic", "Challenges claims and evidence.", "Look for counter-evidence and unsupported assumptions."),
    AgentDefinition("methodology_auditor", "Methodology Auditor", "Reviews study and source methods.", "Identify design and reproducibility limitations."),
    AgentDefinition("source_intelligence", "Source Intelligence", "Assesses source reliability.", "Separate documented source facts from heuristics."),
    AgentDefinition("citation_genealogy", "Citation Genealogy", "Traces citation dependencies.", "Only record provenance supported by source metadata."),
    AgentDefinition("temporal_intelligence", "Temporal Intelligence", "Checks dates and changing definitions.", "Flag temporal uncertainty explicitly."),
    AgentDefinition("debate_moderator", "Debate Moderator", "Coordinates bounded debate rounds.", "Summarize positions without private reasoning."),
    AgentDefinition("conflict_adjudicator", "Conflict Adjudicator", "Explains credible source disagreement.", "Do not force consensus."),
    AgentDefinition("report_intelligence", "Report Intelligence", "Assembles transparent reports.", "Include limitations and unresolved issues."),
]
