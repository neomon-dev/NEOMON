from app.schemas import ResearchMode
from app.research.providers import SearchQuery


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
