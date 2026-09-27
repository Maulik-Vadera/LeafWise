"""Optional external disease/pest identification via Pl@ntNet. No remote call without explicit consent."""
import httpx
from .imaging import clean_jpeg


def bounded_score(value):
    try:
        n = float(value)
        return round(max(0, min(n, 1)), 5) if n == n else 0
    except (TypeError, ValueError):
        return 0


def parse_disease_result(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Invalid provider response")
    candidates = []
    for item in payload["results"][:5]:
        eppo_code = item.get("name", "")
        description = item.get("description", "")
        score = bounded_score(item.get("score", 0))
        images = item.get("images", [])
        # Extract a representative image URL if available
        image_url = None
        if images:
            image_url = images[0].get("url", {}).get("m") or images[0].get("url", {}).get("s")
        candidates.append({
            "eppo_code": eppo_code,
            "name": description or eppo_code,
            "score": score,
            "image_url": image_url,
            "images": images,
        })
    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:5]
    return {
        "status": "candidates" if candidates else "no_match",
        "provider": "Pl@ntNet",
        "candidates": candidates,
        "version": payload.get("version", ""),
        "remaining_quota": payload.get("remainingIdentificationRequests"),
        "note": "These are disease/pest candidates from AI screening, not a confirmed diagnosis. "
                "Consult a local crop adviser or plant clinic for confirmation and management advice. "
                "Coverage is limited to certain crops and pathologies.",
    }


async def identify_disease(images, organs, key, client=None):
    """
    Identify plant diseases/pests using Pl@ntNet API.

    Args:
        images: List of PIL images
        organs: List of organ strings (leaf, flower, fruit, bark, auto)
        key: Pl@ntNet API key
        client: Optional httpx.AsyncClient for testing

    Returns:
        Parsed disease identification result
    """
    files = [("images", (f"disease-{i+1}.jpg", clean_jpeg(img), "image/jpeg")) for i, img in enumerate(images)]
    files += [("organs", (None, organ)) for organ in organs]
    params = {"api-key": key, "include-related-images": "true", "nb-results": 5, "lang": "en"}
    own = client is None
    client = client or httpx.AsyncClient(timeout=httpx.Timeout(35, connect=10), follow_redirects=False)
    try:
        response = await client.post("https://my-api.plantnet.org/v2/diseases/identify", params=params, files=files)
        if response.status_code == 404:
            return {"status": "no_match", "provider": "Pl@ntNet", "candidates": [],
                    "note": "No disease match was returned. Try a clear photo of the affected area."}
        if response.status_code in (401, 403):
            raise ValueError("Disease identification is not authorized. The owner should check the Pl@ntNet key.")
        if response.status_code == 429:
            raise ValueError("The disease-identification quota is used up. Try again later.")
        response.raise_for_status()
        return parse_disease_result(response.json())
    except httpx.HTTPError:
        # httpx errors can contain the key-bearing URL. Never forward or log them.
        raise ValueError("The disease-identification service could not be reached. Your local disease scan still works.") from None
    finally:
        if own:
            await client.aclose()