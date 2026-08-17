import json
import urllib.parse
import urllib.request


SEARXNG_URL = "http://127.0.0.1:8080/search"


def web_search(query):
    """Search SearXNG and return the first five results as JSON."""
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
    })

    url = f"{SEARXNG_URL}?{params}"

    with urllib.request.urlopen(url) as response:
        data = json.load(response)

    results = []

    # Keep only the fields Bob needs. Limiting to five results
    # keeps tool responses smaller and reduces context usage.
    for item in data.get("results", [])[:5]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
        })

    return json.dumps(results)

