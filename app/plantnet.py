"""Pl@ntNet species, cultivar and disease adapters; keys never leave the server."""
import math
import re
import httpx
from .imaging import clean_jpeg
from .catalog import CROPS


class PlantNetError(ValueError):
    """Safe, actionable error; never includes a key-bearing request URL."""
    def __init__(self, code, message, status_code=502):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def check_response(response):
    if response.status_code in (401, 403):
        raise PlantNetError("unauthorized", "Pl@ntNet rejected this key or its permissions. Check the key in .env, leave 'Expose my API key' unchecked for this server app, and restart Leafwise.")
    if response.status_code == 429:
        raise PlantNetError("quota_exhausted", "Pl@ntNet's request quota or rate limit has been reached. Check your account quota and try again after it resets.", 429)
    if response.status_code >= 400 or response.is_redirect:
        raise PlantNetError("provider_error", "Pl@ntNet could not complete the request. Try again later; no local crop guess has been substituted.")


def health_scope(result, crop_ids):
    """Conservative routing rule, not a calibrated guarantee of species accuracy."""
    candidates = result.get("candidates", [])
    if result.get("mode") != "species" or not candidates:
        return {"status": "unverified", "crop_id": None, "message": "Identify the plant species before checking whether disease screening covers it."}
    top = candidates[0]
    second = candidates[1]["score"] if len(candidates) > 1 else 0
    if top["score"] < .8 or top["score"] - second < .2:
        return {"status": "uncertain", "crop_id": None, "message": "Species candidates are not clear enough for disease screening. Add a flower, fruit or another clear view."}
    name = top["scientific_name"].casefold().strip()
    crop_id = next((k for k, v in CROPS.items() if v[1].casefold() == name), None)
    if crop_id not in crop_ids:
        return {"status": "unsupported", "crop_id": None, "message": f"The offline starter model does not cover {top['scientific_name']}. Online disease and pest identification is a separate service with its own limited coverage."}
    return {"status": "supported", "crop_id": crop_id, "message": f"The leading species candidate matches the {CROPS[crop_id][0]} category. Confirm the crop before screening; species identity is still a prediction."}

def bounded_score(value):
    try:
        n = float(value)
        return round(max(0, min(n, 1)), 5) if math.isfinite(n) else 0
    except (TypeError, ValueError):
        return 0

def text(value, limit=180):
    return value[:limit] if isinstance(value, str) else ""

def taxon(value):
    return text(value.get("scientificNameWithoutAuthor", value.get("scientificName", ""))) if isinstance(value, dict) else text(value)

def parse_result(payload, mode):
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Invalid provider response")
    candidates = []
    for item in payload["results"][:5]:
        if not isinstance(item, dict):
            raise ValueError("Invalid provider candidate")
        species = item.get("species") or {}
        if not isinstance(species, dict) or not taxon(species):
            raise ValueError("Missing species data")
        common_names = species.get("commonNames") or []
        if not isinstance(common_names, list):
            common_names = []
        base = {"scientific_name": taxon(species),
                "common_names": [text(v) for v in common_names[:4]],
                "family": taxon(species.get("family", "")), "genus": taxon(species.get("genus", ""))}
        if mode == "variety":
            for variety in item.get("varieties", [])[:5]:
                candidates.append({**base, "name": text(variety.get("name", "")),
                                   "score": bounded_score(variety.get("score", 0))})
        else:
            candidates.append({**base, "name": base["scientific_name"], "score": bounded_score(item.get("score", 0))})
    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:5]
    return {"status": "candidates" if candidates else "no_match", "mode": mode,
            "provider": "Pl@ntNet", "candidates": candidates, "version": text(payload.get("version", "")),
            "note": "Candidates need confirmation. Cultivar coverage is limited; a leaf alone may not distinguish varieties." if mode == "variety" else
                    "These are species candidates, not disease diagnoses. Compare flowers, fruit or bark before confirming."}

async def identify(images, organs, key, mode="species", client=None):
    routes = {"species": "identify/all", "variety": "varieties/identify", "disease": "diseases/identify"}
    if mode not in routes:
        raise ValueError("Unknown identification mode")
    route = routes[mode]
    files = [("images", (f"plant-{i+1}.jpg", clean_jpeg(img), "image/jpeg")) for i, img in enumerate(images)]
    # Multipart permits repeated organs fields without encoding a JSON array.
    files += [("organs", (None, organ)) for organ in organs]
    params = {"api-key": key, "include-related-images": "false", "no-reject": "false", "nb-results": 5, "lang": "en"}
    own = client is None
    client = client or httpx.AsyncClient(timeout=httpx.Timeout(35, connect=10), follow_redirects=False)
    try:
        response = await client.post(f"https://my-api.plantnet.org/v2/{route}", params=params, files=files)
        if response.status_code == 404:
            if mode == "disease":
                return parse_disease_result({"results": []})
            return {"status": "no_match", "mode": mode, "provider": "Pl@ntNet", "candidates": [],
                    "note": "No match was returned. Try a clear leaf plus a flower or fruit from the same plant."}
        check_response(response)
        try:
            return parse_disease_result(response.json()) if mode == "disease" else parse_result(response.json(), mode)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise PlantNetError("invalid_response", "Pl@ntNet returned an unreadable result. Try again; no replacement prediction was generated.") from None
    except httpx.TimeoutException:
        raise PlantNetError("timeout", "Pl@ntNet took too long to respond. Check your internet connection and try again.") from None
    except httpx.HTTPError:
        # httpx errors can contain the key-bearing URL. Never forward or log them.
        raise PlantNetError("unreachable", "Cannot reach Pl@ntNet. Check your internet connection. No replacement prediction was generated.") from None
    finally:
        if own:
            await client.aclose()


async def check_connection(key, client=None):
    """Validate credentials against the documented quota route; sends no photos."""
    own = client is None
    client = client or httpx.AsyncClient(timeout=httpx.Timeout(15, connect=8), follow_redirects=False)
    try:
        response = await client.get("https://my-api.plantnet.org/v2/quota/daily", params={"api-key": key})
        check_response(response)
        try:
            quota = response.json()["quota"]
            if not isinstance(quota, dict):
                raise ValueError()
            identify_quota = quota.get("identify") or {}
            remaining = identify_quota.get("remaining")
            if remaining is not None and (isinstance(remaining, bool) or not isinstance(remaining, (int, float)) or not math.isfinite(remaining) or remaining < 0):
                raise ValueError()
        except (ValueError, KeyError, TypeError, AttributeError):
            raise PlantNetError("invalid_response", "The API responded, but its quota details could not be read. Connection is not verified.") from None
        return {"state": "quota_exhausted" if remaining == 0 else "ready", "remaining": remaining,
                "message": "Key accepted, but today's shared identification quota is used up." if remaining == 0 else
                f"Key accepted by Pl@ntNet. {int(remaining)} identification requests remaining today (shared by species and disease scans)." if remaining is not None else
                "Key accepted by Pl@ntNet. Identification availability will be checked when you submit a photo."}
    except httpx.TimeoutException:
        raise PlantNetError("timeout", "Connection check timed out. Check your internet connection and try again.") from None
    except httpx.HTTPError:
        raise PlantNetError("unreachable", "Cannot reach Pl@ntNet. Check your internet connection and try again.") from None
    finally:
        if own:
            await client.aclose()


def eppo_link(code):
    return f"https://gd.eppo.int/taxon/{code}" if re.fullmatch(r"[A-Z0-9]{6}", code) else None


def parse_disease_result(payload):
    """Parse the disease response itself, never reuse a species or local-model label."""
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Invalid disease response")
    candidates = []
    for item in payload["results"][:5]:
        if not isinstance(item, dict):
            raise ValueError("Invalid disease candidate")
        code = text(item.get("name", ""), 80).strip()
        value = item.get("score")
        if not code or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Missing disease code or score")
        description = text(item.get("description", ""), 300).strip()
        candidates.append({"name": description or code, "code": code,
                           "score": round(float(value), 5), "reference_url": eppo_link(code)})
    candidates.sort(key=lambda c: c["score"], reverse=True)
    top = candidates[0]["score"] if candidates else 0
    second = candidates[1]["score"] if len(candidates) > 1 else 0
    # Display policy only: these cutoffs have not been calibrated on field images.
    state = "no_match" if not candidates else "candidates" if top >= .7 and top - second >= .15 else "uncertain"
    notes = {
        "no_match": "No supported condition was identified. This does not establish that the plant is healthy; the cause may be outside the service's coverage.",
        "uncertain": "There is no clear leading condition. The ranked candidates below need more evidence; do not treat them as a diagnosis.",
        "candidates": "These are possible diseases or pests returned by Pl@ntNet. A photo cannot confirm an infection, its cause or a treatment."}
    remaining = payload.get("remainingIdentificationRequests")
    if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining < 0:
        remaining = None
    return {"provider": "Pl@ntNet", "mode": "disease", "status": state, "candidates": candidates,
            "version": text(payload.get("version", "")), "remaining_requests": remaining,
            "note": notes[state], "score_note": "Provider scores rank its supported conditions. They are not measured diagnostic accuracy or infection severity.",
            "coverage_note": "Pl@ntNet supports a limited set of plants and conditions. Species identification alone does not prove that disease identification covers that species.",
            "next_steps": ["Take a sharp close-up of the affected area and a wider view of the same plant in daylight.",
                           "Record when symptoms began, which leaves are affected, and whether nearby plants show the same changes.",
                           "Compare the candidate with an authoritative reference. If damage is spreading, take the photos and notes to a local crop adviser or KVK.",
                           "Confirm the cause before choosing treatment. This result does not prescribe pesticides or establish that an infection is present."]}


async def disease_catalog(key, client=None):
    """Current provider condition catalog; does not imply a host-plant coverage list."""
    own = client is None
    client = client or httpx.AsyncClient(timeout=httpx.Timeout(20, connect=8), follow_redirects=False)
    try:
        response = await client.get("https://my-api.plantnet.org/v2/diseases", params={"api-key": key, "lang": "en"})
        check_response(response)
        try:
            payload = response.json()
            if not isinstance(payload, list) or len(payload) > 10000:
                raise ValueError()
            entries = []
            for item in payload:
                if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
                    raise ValueError()
                code = text(item["name"], 80).strip()
                categories = item.get("categories") or []
                entries.append({"code": code, "name": text(item.get("label"), 300) or code,
                                "categories": [text(x) for x in categories[:8]] if isinstance(categories, list) else [],
                                "reference_url": eppo_link(code)})
        except (ValueError, TypeError, KeyError):
            raise PlantNetError("invalid_response", "The disease catalog could not be read. Coverage is not verified.") from None
        return {"provider": "Pl@ntNet", "entries": entries, "count": len(entries),
                "note": "This is the provider's current condition list, not a list of supported host plants. A listed condition is not a diagnosis and does not guarantee support for your crop."}
    except httpx.TimeoutException:
        raise PlantNetError("timeout", "The disease-catalog request timed out. Check your connection and try again.") from None
    except httpx.HTTPError:
        raise PlantNetError("unreachable", "Cannot reach the Pl@ntNet disease catalog. Check your connection and try again.") from None
    finally:
        if own:
            await client.aclose()
