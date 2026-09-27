# Leafwise

**Version 1.3.0 — public website, browser installation and online disease checks.** See [UPDATE_TO_1_3.md](UPDATE_TO_1_3.md) to update your working folder while keeping its API key and environment.

A crop-health assistant for a first-year CSE AI/ML project. It connects separate online species, cultivar and disease identification services, includes a limited local image classifier, and provides a field guide and observation journal.

**Run first:** read [START_HERE.md](START_HERE.md). The ZIP includes the working starter model. No training or API key is needed for local crop screening.

## Put it online

Follow [DEPLOY_ON_VERCEL.md](DEPLOY_ON_VERCEL.md). The public website is at `/`; the scanner is at `/app`. Visitors can use the browser or install the PWA. The complete backend is included; no separate frontend build is needed. Your API key stays in the hosting environment.

## Scope, honestly stated

The default **Check plant health** option calls Pl@ntNet's real disease/pest endpoint with the existing API key. It is independent of the local classifier. Provider coverage is limited; the live **View supported conditions** list describes conditions, not supported host species. No match does not establish health. See the [official disease API documentation](https://my.plantnet.org/doc/api/diseases).

The optional **offline starter model** has **15 classes across three crops**. A class means a crop plus a condition, including a healthy class. It does not mean 15 distinct diseases.

| Crop | Included classes |
|---|---|
| Bell pepper | Bacterial spot; healthy |
| Potato | Early blight; late blight; healthy |
| Tomato | Bacterial spot; early blight; late blight; leaf mold; Septoria leaf spot; spider-mite damage; target spot; yellow leaf curl virus; mosaic virus; healthy |

The catalog understands all 38 original PlantVillage class names for future training, but **the included weights do not cover all 38**. Retraining on a larger dataset changes coverage. The UI reads installed-model coverage automatically. Crop-specific care protocols beyond the starter set need separate review.

Species and cultivar identification use optional Pl@ntNet endpoints. A species is, for example, *Mangifera indica*; a cultivar is a named cultivated variety. “Breed” is generally not the botanical term. Leaf appearance does not uniquely encode every cultivar. Leafwise does not invent an exact variety from a disease label.

This package is a working educational prototype, not a field-certified diagnostic system. It has no measured Indian farm accuracy. High closed-set model scores can still occur on unfamiliar plants, unsuitable photos and non-leaf objects. Confirm the crop and use an expert when the consequence of an incorrect diagnosis matters.

## Included functionality

- Responsive HTML landing website and scanner with original botanical SVG artwork; no UI framework or frontend build step.
- Browser installation prompts with iPhone/Android/desktop instructions when a prompt is unavailable.
- Vercel configuration, hosted-domain checks and client photo compression (at most 1 MB per image).
- File upload, drag-and-drop and permission-based camera capture; one to three photos.
- Real CPU inference using the included MobileNetV3 ONNX model and its external weight data.
- JPEG/PNG/WebP validation, EXIF orientation correction, metadata removal, size limits and photo-quality feedback.
- Up to three within-crop possibilities, conservative score/margin checks, crop mismatch checks and disagreement handling across views. An unknown crop receives no disease-model species guess.
- Separate species and limited cultivar identification, with explicit external-photo consent and server-held key.
- Plant identification is the default screen. A connection-check button validates the key with the provider, and errors distinguish authorization, quota and network problems.
- The main online health option calls the provider's disease model, with no local-model fallback. Results include possible conditions, EPPO references, uncertainty and no-match handling, and practical observation steps.
- The offline starter option requires a known, confirmed crop and can additionally verify the species online. Its original weights are unchanged.
- Field guide with source links, observations and non-chemical care steps. No generated treatment prescriptions.
- IndexedDB journal, field notes, deletion, text reports, journal JSON export and browser print/PDF.
- PWA manifest and service worker; offline journal and cached guide browsing.
- English/Hindi/Gujarati core navigation; detailed guidance and errors remain English.
- Windows launcher, macOS/Linux launcher, Dockerfile, backend tests and optional browser checks.
- Training, separate calibration, held-out evaluation, confusion matrix, macro F1, expected calibration error and optional unknown-image evaluation.

## Run on macOS / Linux

Use Python 3.12, then:

```sh
bash Start-Mac-Linux.sh
```

Or:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

Python 3.12/Linux is the environment used for verification. Platform-specific launchers and Docker configuration are supplied; they were not all executed on their target platforms.

## Project map

| Location | Role |
|---|---|
| `web/index.html` | Public landing website |
| `web/scanner.html` | Scanner, journal and field guide served at `/app` |
| `web/` | Styles, camera, journal, translations, install flow, PWA cache and artwork |
| `vercel.json`, `pyproject.toml` | Hosted FastAPI configuration |
| `app/main.py` | FastAPI routes, upload limits, host/origin checks, concurrency limits |
| `app/imaging.py` | Safe decoding, quality checks and exact preprocessing |
| `app/inference.py` | Model integrity, ONNX execution, candidate selection and abstention |
| `app/plantnet.py` | Optional provider adapter; metadata-free images and sanitized errors |
| `app/catalog.py` | Label normalization, crop taxonomy and reviewed care cards |
| `models/` | Included pretrained weights, ordered labels, preprocessing and integrity manifest |
| `training/` | Import, group-aware split, transfer learning, export and evaluation |
| `tests/` | Backend/data tests and an optional browser workflow check |
| `docs/` | Architecture, training, research, model card and verification notes |

## Important operating details

There is no visitor account, backend photo database or analytics in this implementation. It can run locally or on a hosted Vercel project. The journal belongs to one browser origin; changing the port, browser or device gives you a different journal. Exporting JSON preserves observations and notes, not thumbnails. Import/sync is not implemented.

The service worker caches the interface and catalog, not API prediction responses or uploaded photos. Offline inference still needs the local Python server. Installing the PWA does not copy the Python model onto a phone.

For a trusted private LAN, set `HOST=0.0.0.0` and add the computer's LAN IP to `ALLOWED_HOSTS`. Only the hosting computer's model runs. Browser camera capture on a remote device generally requires HTTPS; ordinary photo upload can still be used. Use the Vercel deployment instructions for a public HTTPS demo rather than exposing the local development server. Visitors share the owner’s provider allowance. The in-memory rate limit is per process, so it is not a global abuse-control system. See the deployment and architecture notes before a wider rollout.

## Docker, optional

```sh
docker build -t leafwise .
docker run --rm -p 127.0.0.1:8000:8000 leafwise
```

To connect Pl@ntNet, use `--env-file .env`. The `.env` file is excluded from the Docker image. Prefer injecting a deployment secret if you later host the app.

## Attribution

The included pretrained model is `imaflower/plantvillage-mobilenetv3`, revision `d76fe187be1c4c3a5474f835a7a70cd08c7ab085`, with MIT license declared in its repository metadata. We use its ONNX files, class order and training configuration; we did not train those included weights. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The original app code is MIT-licensed. Data, upstream weights, dependency packages and online services have their own terms. Raw training photographs are not included in this ZIP.
