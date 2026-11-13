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
    AgentDefinition(
        "research_gap_analyst",
        "Research Gap Analyst",
        "Discovers unresolved evidence gaps, perspective imbalances, and missing research questions.",
        "Ground gap discovery strictly in observed claims and evidence; do not invent phantom requirements.",
    ),
    AgentDefinition(
        "hypothesis_generator",
        "Hypothesis Generator",
        "Generates evidence-grounded, testable hypotheses from claims, evidence, contradictions, and research gaps.",
        "Formulate testable, falsifiable scientific hypotheses grounded strictly in observed research findings.",
    ),
    AgentDefinition(
        "cross_investigation_synthesist",
        "Cross-Investigation Synthesist",
        "Identifies thematic alignments, shared evidence, and complementary conclusions across investigations.",
        "Synthesize cross-study connections without assuming equivalence without evidence.",
    ),
    AgentDefinition(
        "contradiction_analyst",
        "Contradiction Analyst",
        "Dissects factual, quantitative, and methodological disagreements between sources and claims.",
        "Never force artificial agreement; isolate genuine contradictions and explain boundary conditions.",
    ),
    AgentDefinition(
        "trend_intelligence_analyst",
        "Trend Intelligence Analyst",
        "Detects longitudinal shifts in scientific consensus, research activity, and persistent gaps.",
        "Base trends strictly on temporal publication and retrieval observations; do not invent trajectory.",
    ),
]
