import httpx
from typing import Dict, List


SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"


def search(
    query: str,
    api_key: str,
    num_results: int = 5,
    timeout: int = 60,
) -> List[Dict]:
    """Search SerpApi (Google) and return simplified result dictionaries."""

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": num_results,
    }

    try:
        resp = httpx.get(
            SERPAPI_SEARCH_URL,
            params=params,
            timeout=timeout,
        )
        resp.raise_for_status()

        data = resp.json()

    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"SerpApi request timed out after {timeout} seconds"
        ) from exc

    except httpx.HTTPError as exc:
        raise RuntimeError(f"SerpApi request failed: {exc}") from exc

    organic_results = data.get("organic_results", [])

    results: List[Dict] = []

    for item in organic_results:
        results.append(
            {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
            }
        )

    return results