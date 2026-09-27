# How Leafwise works

## Website and installation

Version 1.3 serves the public website (`web/index.html`) at `/` and the scanner (`web/scanner.html`) at `/app` and `/app/`. The same-origin API and browser journal remain shared. Historical root hash links forward to the scanner. A `mode=health` query opens the online health tab.

`web/install.js` handles the browser's install prompt only after a visitor clicks. If unavailable, it shows menu instructions; it never fabricates an installation or APK download. The PWA keeps its original manifest ID `/`, with a new start URL `/app#scan`. The service worker caches both pages and their assets. Only the care catalog is cached from `/api/`; predictions, uploads and key checks are excluded. Cached scanner navigation tolerates query strings.

Before submission, the browser converts each photo to a JPEG at most 1600 pixels on its longest side and at most 1,000,000 bytes. Up to three images fit below the hosting request budget. Server-side decoding, metadata stripping and validation are independent safeguards. Cancellation and changing inputs invalidate prepared requests before they are submitted.

Vercel uses the `app.main:app` FastAPI entrypoint, Python 3.12, and pinned runtime dependencies. Static serving stays behind security middleware. Vercel deployment/branch/production hostnames are added to the allowlist; custom domains can be explicitly configured. See `DEPLOY_ON_VERCEL.md`. Public mode presents visitor-facing connection messages instead of local `.env` instructions.

## The separate jobs

| Job | Component | Input | Output |
|---|---|---|---|
| Crop-health screening | Local ONNX model | Leaf photos from supported crops | Ranked crop/condition classes |
| Broad plant identification | Optional Pl@ntNet species API | Leaf/flower/fruit/bark photos from one individual | Ranked species, genus and family candidates |
| Online plant-health identification | Pl@ntNet disease API | Affected plant parts from one individual | Ranked disease/pest conditions and EPPO reference codes |
| Useful next steps | Fixed care catalog | Accepted model class | Reviewed observations and non-chemical guidance with sources |

These tasks are kept separate. A disease classifier's crop label is not a general tree-identification result, and a species result does not establish disease or cultivar identity.

Since version 1.2, the main health option calls `POST https://my-api.plantnet.org/v2/diseases/identify`. Its response contains condition `name` codes, `description` and `score`, which are parsed separately from species objects. The local three-crop model is never invoked on this route, even when the provider fails or the model is unavailable. An explicit offline-starter selector retains the older local workflow below. Upload validation and photo consent apply to both online paths.

The provider disease catalog is fetched on user request from `GET /v2/diseases` and displayed with search. It is a condition list, not host-species coverage. Disease no-match/404 responses never become “healthy.” The display labels a result uncertain when its top score is below 0.7 or its margin is below 0.15; this is an uncalibrated presentation rule, not a measured probability of correctness. Reference links are constructed only for valid EPPO code shapes. Provider images are not downloaded or redistributed. Guidance asks for observations and expert confirmation; it does not prescribe chemicals.

## A local crop scan

1. The browser retains selected files in memory and shows previews. It sends them only when the user submits.
2. FastAPI bounds the full request at 20 MiB, each file at 6 MiB, three images per request and 20 megapixels per decoded image. MIME headers are not trusted as proof of content.
3. Pillow verifies decodability and format, handles camera orientation and creates clean RGB pixels without original metadata. Animation and tiny-image inputs are rejected.
4. Photo checks measure brightness, contrast and Laplacian variance. They identify some bad captures; they are not a semantic leaf detector.
   Before inference, an unknown or unsupported crop returns an empty candidate list. A supported crop requires user confirmation. In online verification mode, a Pl@ntNet species call must give a sufficiently distinct supported species matching the chosen crop; otherwise inference stops. The provisional species routing rule uses a top score of 0.8 and margin of 0.2. These are unvalidated routing heuristics, not an accuracy guarantee. Bell pepper still requires user confirmation because Capsicum annuum includes other peppers.
5. Preprocessing resizes the short side to 256, crops the centre to 224×224, rescales RGB to 0–1, applies the model's ImageNet normalization, and converts to NCHW float32.
6. ONNX Runtime executes on the CPU. Every model and external data file must match the manifest's SHA-256 digest. The model output width must match the exact class ordering.
7. Logits become softmax scores using the saved temperature. For multiple images, probabilities are averaged. If the views disagree on the top class, the app abstains.
8. The provisional policy also requires a known matching crop, a top score of at least 0.85, a top-two margin of at least 0.25, and no quality warnings. These numbers are design defaults, not validated agronomic decision thresholds.
9. Accepted outputs are called **possible matches**. Other cases get general evidence-gathering steps, not a disease-specific care card. “Healthy” is displayed as “No listed disease pattern.”

No random or fabricated classification is used. No green-pixel heuristic guesses the species. There is no general learned out-of-distribution detector: even with thresholds, an unfamiliar image can still produce a high score. A real deployment should add and evaluate an explicit leaf/plant gate and rejection model.

## An optional identity request

The owner configures the provider key in `.env`. The browser cannot read it. The user chooses species or variety mode and explicitly allows photo sharing. The server sends JPEGs after removing metadata and reducing resolution. The adapter uses repeated multipart `images` and `organs` fields and extracts only relevant taxonomic fields; provider image URLs are not fetched.

Provider errors are sanitized so key-bearing request URLs do not reach the user. There is no automatic fallback to external processing when local analysis fails. A variety request is a separate call and may consume additional quota. The app reports candidates rather than certifying a cultivar.

Version 1.1 opens in species mode. Disease-mode `crop=auto` no longer runs inference or reveals a forced class. Local-only health screening remains possible after the user confirms a known supported crop; that mode cannot reject every unfamiliar plant. Provider failures never trigger a fallback species guess from the disease model. Starting a new request clears the old displayed result, so a failed retry cannot leave a stale prediction visible.

`/api/status` reports only whether the key is configured. A user-requested connection check calls the provider's documented `/v2/quota/daily` endpoint without photographs. A successful check establishes key acceptance at that time, not recognition accuracy or permanent availability. See [Pl@ntNet quota documentation](https://my.plantnet.org/doc/api/quota).

## Journal and reporting

The IndexedDB store has one record per saved scan: UUID, creation date, the returned observation, a browser-generated JPEG thumbnail and the user's note. A record can be updated by saving again. At 50 records the user is asked to export/delete older entries. The server holds no journal database.

Report export is plain text, so strings are not executed as HTML. UI dynamic text is escaped before insertion. Browser printing can create a PDF. The JSON journal export omits thumbnails and is meant for user records; an import function is not included.

## API

| Method / path | Purpose | Main fields |
|---|---|---|
| `GET /api/status` | Model readiness and provider configuration | No secrets returned; a configured key is not a verified connection |
| `POST /api/plantnet/check` | Verify provider credentials / species quota | No photos; returns a safe status/message and remaining quota when supplied |
| `POST /api/plantnet/diseases` | Fetch current provider condition catalog | No photos; returns condition names, EPPO codes and categories |
| `GET /api/catalog` | Installed model's care cards | Ordered supported classes |
| `POST /api/analyze` | Disease screening, optionally after species verification | Multipart `photos` repeated, `crop`, `crop_confirmed=yes`, `verification=online` or `local`; online additionally requires `consent=yes` |
| `POST /api/identify` | Optional online identity | Multipart `photos`, matching `organs`, `mode`, `consent=yes` |
| `POST /api/health` | Online disease and pest identification | Multipart `photos`, matching `organs`, `consent=yes`; no three-crop restriction or local-model requirement |

The interactive FastAPI documentation is at `/docs`. File routes are parsed manually so multipart limits apply before app processing; refer to this table for request fields.

## Before a public pilot

This prototype defaults to loopback with no sign-in. Its host/origin checks, bounded uploads, two-request inference concurrency and per-process request limiter are useful local safeguards, not a complete internet-facing security architecture. The supplied Vercel setup provides HTTPS hosting for an anonymous demo. The current request limiter is per instance and does not enforce a shared global quota. Wider public rollout needs shared rate limiting and deployment-level abuse controls; authenticated accounts are needed if adding per-user quotas or server-side journal storage. Avoid debug logs that include provider URLs or photo content.

More importantly, test with consented local farm photographs from crops, seasons and devices excluded from training. Ask agronomists to verify labels, review language and care content, and identify symptom classes the model cannot diagnose. Make low-confidence rejection useful to the farmer. Measure real errors and follow-up outcomes before advertising reliability.
