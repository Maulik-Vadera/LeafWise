from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict, deque
import asyncio
import os
import time
import uuid
from urllib.parse import urlparse
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.concurrency import run_in_threadpool
from .catalog import CROPS, entry, generic_guide
from .imaging import decode_image, quality, ImageProblem, MAX_FILE_BYTES
from .inference import LeafModel
from .plantnet import identify, check_connection, health_scope, disease_catalog, PlantNetError

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
MAX_BODY = 20 * 1024 * 1024
MAX_PARALLEL = 2

class BodyLimit:
    """Bound uploads before multipart parsing, including chunked requests."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "POST":
            return await self.app(scope, receive, send)
        chunks, count = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            count += len(message.get("body", b""))
            if count > MAX_BODY:
                return await JSONResponse({"detail": "Photos exceed the 20 MB request limit."}, status_code=413)(scope, receive, send)
            chunks.append(message)
            if not message.get("more_body", False):
                break
        index = 0
        async def replay():
            nonlocal index
            if index < len(chunks):
                result = chunks[index]; index += 1
                return result
            return await receive()
        await self.app(scope, replay, send)

@asynccontextmanager
async def lifespan(app):
    directory = Path(os.getenv("MODEL_DIR", str(ROOT / "models")))
    if not directory.is_absolute():
        directory = ROOT / directory
    app.state.model = LeafModel(directory)
    app.state.inflight = 0
    app.state.requests = defaultdict(deque)
    yield

def hosted():
    return os.getenv("VERCEL") == "1" or os.getenv("PUBLIC_DEPLOYMENT", "").lower() in {"1", "true", "yes"}

def allowed_hosts():
    hosts = {h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver").split(",") if h.strip()}
    # Vercel supplies exact deployment / branch / production hostnames at runtime.
    # Add custom domains to ALLOWED_HOSTS; do not accept arbitrary Host headers.
    if os.getenv("VERCEL") == "1":
        for name in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
            value = os.getenv(name, "").strip()
            if value:
                host = urlparse(value if "://" in value else "https://" + value).hostname
                if host:
                    hosts.add(host)
    return sorted(hosts)

app = FastAPI(title="Leafwise API", version="1.3.0", lifespan=lifespan)
app.add_middleware(BodyLimit)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())

@app.middleware("http")
async def headers_and_limits(request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Please use the app from the same server address."}, status_code=403)
        key = request.client.host if request.client else "local"
        visits = request.app.state.requests
        now = time.monotonic()
        if len(visits) > 1024:
            for k in list(visits):
                if not visits[k] or visits[k][-1] < now - 60:
                    del visits[k]
        queue = visits[key]
        while queue and queue[0] < now - 60:
            queue.popleft()
        if len(queue) >= 20:
            return JSONResponse({"detail": "Please wait a minute before starting more scans."}, status_code=429, headers={"Retry-After": "60"})
        queue.append(now)
        try:
            if int(request.headers.get("content-length", "0")) > MAX_BODY:
                return JSONResponse({"detail": "Photos exceed the 20 MB request limit."}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Invalid request length."}, status_code=400)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif not request.url.path.endswith((".png", ".svg")):
        response.headers["Cache-Control"] = "no-cache"
    return response

@app.exception_handler(PlantNetError)
async def plantnet_error(request, exc):
    message = str(exc)
    if hosted() and exc.code == "unauthorized":
        message = "The identification service could not authorize this website. Please let the website owner know."
    elif hosted() and exc.code == "quota_exhausted":
        message = "This website's shared identification allowance or provider rate limit has been reached. Please try again later."
    return JSONResponse({"detail": message, "code": exc.code}, status_code=exc.status_code)

def provider_config():
    configured = bool(os.getenv("PLANTNET_API_KEY", "").strip())
    message = "API key found. Connection has not been checked yet."
    if not configured:
        message = "Add PLANTNET_API_KEY to .env and restart Leafwise to identify plants."
        if (ROOT / ".env.txt").is_file():
            message = "Found .env.txt. Rename it to .env (remove .txt), then restart Leafwise."
    if hosted():
        message = "Online identification is configured. You can check the connection before scanning." if configured else "Online identification is unavailable. The website owner needs to connect the service."
    return {"state": "configured" if configured else "not_configured", "message": message}

@app.get("/api/status")
def status(request: Request):
    model = request.app.state.model
    return {"ready": model.ready, "error": model.error, "class_count": len(model.labels) if model.ready else 0,
            "crops": [{"id": k, "name": CROPS[k][0]} for k in model.crop_ids],
            "model": model.manifest.get("name", "No model installed"),
            "plantnet_available": bool(os.getenv("PLANTNET_API_KEY", "").strip()),
            "plantnet": provider_config(),
            "online_health_provider": "Pl@ntNet", "local_processing": not hosted(), "hosted": hosted(), "field_validated": False, "version": "1.3.0"}

@app.post("/api/plantnet/check")
async def provider_check():
    key = os.getenv("PLANTNET_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, provider_config()["message"])
    return await check_connection(key)

@app.post("/api/plantnet/diseases")
async def provider_diseases():
    key = os.getenv("PLANTNET_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, provider_config()["message"])
    return await disease_catalog(key)

@app.get("/api/catalog")
def catalog(request: Request):
    return {"entries": [entry(s) for s in request.app.state.model.labels], "reviewed": "2026-09-26"}

async def photos_from_form(request):
    try:
        form = await request.form(max_files=3, max_fields=12, max_part_size=MAX_FILE_BYTES)
    except Exception:
        raise HTTPException(400, "Could not read the upload. Use up to three photos.") from None
    files = form.getlist("photos")
    if not 1 <= len(files) <= 3:
        await form.close()
        raise HTTPException(400, "Add between one and three photos of the same plant.")
    values = {k: form.get(k) for k in ("crop", "consent", "mode", "crop_confirmed", "verification")}
    organs = form.getlist("organs")
    images = []
    try:
        for upload in files:
            if not hasattr(upload, "read"):
                raise HTTPException(400, "Invalid photo upload.")
            data = await upload.read(MAX_FILE_BYTES + 1)
            try:
                images.append(await run_in_threadpool(decode_image, data))
            except ImageProblem as exc:
                raise HTTPException(422, str(exc)) from None
    finally:
        await form.close()
    return images, values, organs

@app.post("/api/analyze")
async def analyze(request: Request):
    model = request.app.state.model
    if not model.ready:
        raise HTTPException(503, model.error)
    if request.app.state.inflight >= MAX_PARALLEL:
        raise HTTPException(429, "The scanner is busy. Try again shortly.")
    request.app.state.inflight += 1
    try:
        images, form, _ = await photos_from_form(request)
        crop = form["crop"] or "auto"
        if crop not in ["auto", "other", *CROPS]:
            raise HTTPException(400, "Choose a crop from the list.")
        checks = await run_in_threadpool(lambda: [quality(img) for img in images])
        common = {"id": str(uuid.uuid4()), "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "quality": checks, "photo_count": len(images)}
        if crop == "auto":
            return {**common, "status": "needs_identification", "reasons": ["The crop is unknown. Use Identify a plant first; this disease model only compares its supported crops."],
                    "guide": generic_guide(), "candidates": [], "candidate": None}
        if crop != "auto" and crop not in model.crop_ids:
            return {**common, "status": "unsupported", "reasons": ["Disease scanning is not trained for this crop. Use Identify plant or consult a crop adviser."],
                    "guide": generic_guide(), "candidates": [], "candidate": None}
        if not all(c["usable"] for c in checks):
            return {**common, "status": "retake", "reasons": ["At least one photo needs more detail or better light. Retake it before scanning."],
                    "guide": generic_guide(), "candidates": [], "candidate": None}
        if form["crop_confirmed"] != "yes":
            return {**common, "status": "needs_confirmation", "reasons": ["Confirm that this really is the crop you selected. A disease model score cannot establish plant identity."],
                    "guide": generic_guide(), "candidates": [], "candidate": None}
        verification = form["verification"]
        if verification not in {"online", "local"}:
            raise HTTPException(400, "Choose online species verification or explicitly select local-only screening.")
        species_result = None
        if verification == "online":
            key = os.getenv("PLANTNET_API_KEY", "").strip()
            if not key:
                raise HTTPException(503, provider_config()["message"])
            if form["consent"] != "yes":
                raise HTTPException(400, "Allow photo sharing to verify the species before disease screening.")
            species_result = await identify(images, ["leaf"] * len(images), key)
            scope = health_scope(species_result, model.crop_ids)
            if scope["status"] != "supported" or scope["crop_id"] != crop:
                reason = scope["message"] if scope["status"] != "supported" else "The species result does not match the crop you selected. Check the plant identity before disease screening."
                return {**common, "status": "unsupported" if scope["status"] == "unsupported" else "uncertain",
                        "reasons": [reason], "guide": generic_guide(), "candidates": [], "candidate": None,
                        "identity": species_result, "species_verified": False}
        result = await run_in_threadpool(model.predict, images, crop, any(c["warnings"] for c in checks))
        return {**common, **result, "species_verified": species_result is not None,
                "identity": species_result, "crop_source": "Species checked with Pl@ntNet; still a prediction." if species_result else "Crop selected by you. The local model did not verify plant identity."}
    except (HTTPException, PlantNetError):
        raise
    except Exception:
        raise HTTPException(500, "The scan could not finish. Try again or check the model installation.") from None
    finally:
        request.app.state.inflight -= 1

@app.post("/api/identify")
async def species(request: Request):
    key = os.getenv("PLANTNET_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, provider_config()["message"])
    if request.app.state.inflight >= MAX_PARALLEL:
        raise HTTPException(429, "The scanner is busy. Try again shortly.")
    request.app.state.inflight += 1
    try:
        images, form, organs = await photos_from_form(request)
        if form["consent"] != "yes":
            raise HTTPException(400, "Allow these photos to be sent to Pl@ntNet before identifying.")
        mode = form["mode"] or "species"
        if mode not in {"species", "variety"}:
            raise HTTPException(400, "Choose species or variety identification.")
        organs = organs or ["auto"] * len(images)
        if len(organs) != len(images) or any(o not in {"leaf", "flower", "fruit", "bark", "auto"} for o in organs):
            raise HTTPException(400, "Choose one plant part for each photo.")
        try:
            result = await identify(images, organs, key, mode)
        except PlantNetError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError):
            raise HTTPException(502, "The plant-identification response could not be read. No local crop guess was substituted.") from None
        return {**result, "health_scope": health_scope(result, request.app.state.model.crop_ids),
                "id": str(uuid.uuid4()), "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    finally:
        request.app.state.inflight -= 1

@app.post("/api/health")
async def online_health(request: Request):
    """Real provider disease inference, independent of the installed starter model."""
    key = os.getenv("PLANTNET_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, provider_config()["message"])
    if request.app.state.inflight >= MAX_PARALLEL:
        raise HTTPException(429, "The scanner is busy. Try again shortly.")
    request.app.state.inflight += 1
    try:
        images, form, organs = await photos_from_form(request)
        if form["consent"] != "yes":
            raise HTTPException(400, "Allow these photos to be sent to Pl@ntNet for disease and pest identification.")
        organs = organs or ["auto"] * len(images)
        if len(organs) != len(images) or any(o not in {"leaf", "flower", "fruit", "bark", "auto"} for o in organs):
            raise HTTPException(400, "Choose one plant part for each photo.")
        result = await identify(images, organs, key, "disease")
        return {**result, "id": str(uuid.uuid4()), "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "photo_count": len(images)}
    finally:
        request.app.state.inflight -= 1

@app.get("/")
def home():
    return FileResponse(ROOT / "web" / "index.html")

@app.get("/app", include_in_schema=False)
@app.get("/app/", include_in_schema=False)
def scanner():
    return FileResponse(ROOT / "web" / "scanner.html")

app.mount("/", StaticFiles(directory=ROOT / "web"), name="web")
