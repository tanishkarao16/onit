import httpx
from typing import List, Dict

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"


def search(query: str, api_key: str, num_results: int = 5, timeout: int = 10) -> List[Dict]:
    """Search SerpApi (Google) and return a list of simplified result dicts.

    The function is intentionally small and provider-isolated so it can be
    mocked in tests.
    """
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": num_results,
    }

    try:
        resp = httpx.get(SERPAPI_SEARCH_URL, params=params, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"SerpApi request failed: {exc}") from exc

    data = resp.json()

    results: List[Dict] = []

    # SerpApi returns 'organic_results' for Google
    for item in data.get("organic_results", [])[:num_results]:
        results.append(
            {
                "title": item.get("title"),
                "snippet": item.get("snippet") or item.get("description"),
                "link": item.get("link"),
                "source": item.get("displayed_link") or item.get("source") or "web",
                "engine": "google",
            }
        )

    # As a fallback, try 'answers' or 'knowledge_graph'
    if not results:
        for item in data.get("answers", [])[:num_results]:
            results.append({
                "title": item.get("type"),
                "snippet": item.get("answer"),
                "link": None,
                "source": "answers",
                "engine": "google",
            })

    return results
