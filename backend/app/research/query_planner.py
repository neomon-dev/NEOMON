import re

from app.schemas import ResearchMode
from app.research.providers import SearchQuery
from app.research.relevance import _PRESERVED_ACRONYMS, _terms, question_focus


def generate_queries(question: str, mode: ResearchMode, timeframe: str | None = None) -> list[SearchQuery]:
    suffix = f" {timeframe}" if timeframe else ""
    queries = [
        SearchQuery(question + suffix, "broad"),
        SearchQuery(f"{question} research study{suffix}", "academic"),
        SearchQuery(f"{question} primary source controlled experiment{suffix}", "primary"),
        SearchQuery(f"{question} criticism limitations counter evidence{suffix}", "counter_evidence"),
    ]
    if mode is ResearchMode.deep:
        queries.extend(
            [
                SearchQuery(f"{question} government report dataset{suffix}", "institutional"),
                SearchQuery(f"{question} systematic review meta-analysis{suffix}", "academic"),
                SearchQuery(f"{question} measured outcome methodology{suffix}", "methodology"),
            ]
        )
    seen: set[str] = set()
    return [query for query in queries if not (query.text.casefold() in seen or seen.add(query.text.casefold()))]


def generate_web_queries(question: str, timeframe: str | None = None) -> list[SearchQuery]:
    suffix = f" {timeframe}" if timeframe else ""
    terms, subject, outcomes = question_focus(question)
    q_lower = question.casefold()

    queries: list[SearchQuery] = []

    # Detect technical acronyms and domain topics
    has_ai = "ai" in terms or "artificial" in terms
    has_ram = "ram" in terms or "memory" in terms or "dram" in terms
    has_ddr5 = "ddr5" in terms
    has_electricity = "electricity" in terms or "energy" in terms or "power" in terms
    has_it = "it" in terms or "tech" in terms
    has_layoff = "layoff" in terms or "layoffs" in q_lower

    if has_ai and has_ram:
        # Preserve subject coupling: AI + RAM / Memory
        queries.extend([
            SearchQuery(f"AI datacenter accelerator demand impact on RAM DRAM HBM shortages{suffix}", "web_causal"),
            SearchQuery(f"RAM memory shortages alternative causes PC smartphone demand vs AI{suffix}", "web_counter_evidence"),
            SearchQuery(f"HBM DRAM memory production wafer allocation AI hardware industry report data{suffix}", "web_empirical_data"),
            SearchQuery(f"semiconductor memory manufacturers supply capacity AI demand forecasts{suffix}", "web_critical_perspective"),
        ])
    elif has_ai and has_electricity:
        # Preserve subject coupling: AI + Electricity / Power
        queries.extend([
            SearchQuery(f"AI datacenter power consumption impact on electricity grid demand{suffix}", "web_causal"),
            SearchQuery(f"AI datacenter energy efficiency cooling chip improvements grid load{suffix}", "web_counter_evidence"),
            SearchQuery(f"AI data center electricity demand gigawatt statistics utility reports{suffix}", "web_empirical_data"),
            SearchQuery(f"power grid capacity constraints AI energy consumption critical analysis{suffix}", "web_critical_perspective"),
        ])
    elif has_ddr5 and ("ram" in terms or "price" in terms or "cost" in terms):
        queries.extend([
            SearchQuery(f"DDR5 memory adoption and demand impact on RAM DRAM pricing trends{suffix}", "web_causal"),
            SearchQuery(f"DDR5 vs DDR4 manufacturing yields and memory cost parity{suffix}", "web_counter_evidence"),
            SearchQuery(f"DDR5 DRAM spot market contract price statistics industry data{suffix}", "web_empirical_data"),
            SearchQuery(f"semiconductor memory pricing cycle DDR5 transition market forecasts{suffix}", "web_critical_perspective"),
        ])
    elif has_it and has_layoff:
        queries.extend([
            SearchQuery(f"IT software tech company layoffs employee impact mental health severance morale{suffix}", "web_causal"),
            SearchQuery(f"tech sector layoffs severance packages rehire career transitions positive outcomes{suffix}", "web_counter_evidence"),
            SearchQuery(f"tech industry layoff statistics workforce reduction surveys report data{suffix}", "web_empirical_data"),
            SearchQuery(f"survivor syndrome tech layoffs employee retention organizational performance{suffix}", "web_critical_perspective"),
        ])
    elif "what is" in q_lower and ("ai" in terms or len(terms) <= 3):
        subject_str = " ".join(t.upper() if t in _PRESERVED_ACRONYMS else t for t in terms)
        queries.extend([
            SearchQuery(f"what is {subject_str} definition core principles overview{suffix}", "web_causal"),
            SearchQuery(f"{subject_str} foundational concepts history architecture overview{suffix}", "web_counter_evidence"),
            SearchQuery(f"{subject_str} real-world applications industry adoption statistics{suffix}", "web_empirical_data"),
            SearchQuery(f"{subject_str} capabilities limitations current state expert consensus{suffix}", "web_critical_perspective"),
        ])
    else:
        # General question: couple subject terms with outcome dimensions
        subject_words = [t.upper() if t in _PRESERVED_ACRONYMS else t for t in subject]
        subject_phrase = " ".join(subject_words) if subject_words else question
        outcome_words = list(outcomes)
        outcome_phrase = " ".join(outcome_words) if outcome_words else ""

        queries.extend([
            SearchQuery(f"{subject_phrase} {outcome_phrase} direct causal mechanism primary findings{suffix}".strip(), "web_causal"),
            SearchQuery(f"{subject_phrase} {outcome_phrase} counter evidence null results alternative explanations{suffix}".strip(), "web_counter_evidence"),
            SearchQuery(f"{subject_phrase} {outcome_phrase} industry reports statistics empirical data case studies{suffix}".strip(), "web_empirical_data"),
            SearchQuery(f"{subject_phrase} {outcome_phrase} expert consensus systematic review critical analysis{suffix}".strip(), "web_critical_perspective"),
        ])

    seen: set[str] = set()
    return [q for q in queries if not (q.text.casefold() in seen or seen.add(q.text.casefold()))]

