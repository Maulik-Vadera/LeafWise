# Verification notes

## Version 1.3.0 website and health checks

Checked on 27 September 2026 using Python 3.12/Linux and headless Chromium:

- **80 Python tests passed.** The suite covers the real model's loading and routing, upload validation, separate disease-provider parsing and errors, consent, no fabricated fallback, public routes, secret-file exclusion, manifest launch URLs, exact hosted-domain configuration and visitor-facing provider errors.
- **Website / PWA browser regression passed.** Checked 320, 390, 768 and 1440 px widths, no horizontal overflow, home-to-scanner links, health deep links, old bookmarks, valid manifest, installation help, simulated native install/dismiss/installed events, iPhone user-agent guidance, actual canvas image compression and offline landing/journal/guide access.
- **Disease browser regression passed.** Uses simulated provider results to check the online default, searchable condition list, consent, correct `/api/health` request, disease/EPPO rendering, uncertainty and no-match wording, failed requests without a starter-model fallback, saved reports, journal, mobile layout and Gujarati navigation.
- **Species browser regression passed.** Simulated soybean identification, key errors, consent, scope feedback, journal persistence and mobile layout remain correct.
- **Baseline browser regression passed.** Guide filtering, dialogs, responsive scanner layout, missing-key feedback and navigation language were checked. No new real leaf-photo inference run was used for this update; the bundled model weights are unchanged.
- Desktop/mobile website screenshots and installation help were visually reviewed. All four browser suites completed without uncaught page errors.

These checks validate software behavior, not recognition accuracy. Provider responses and installation events were simulated. No live call using the user's API key, independent Indian-field evaluation, actual Vercel deployment, Windows launch, or physical Android/iOS/desktop app installation was performed. Safari/Firefox rendering has not been exercised. Real installation and a real-photo provider check should be verified after publishing the HTTPS production URL.

To rerun the additional browser checks after installing Playwright (see below):

```bat
set QA_PYTHON=%CD%\.venv\Scripts\python.exe
node tests\browser-website.cjs
node tests\browser-health.cjs
node tests\browser-identity.cjs
```

Each script starts and stops its own local server. The website suite uses port 18126, health uses 18125, identity uses 18124 and baseline uses 18123. No real key is required or used for the provider simulations. The website suite tests compression with a generated noise image, not a disease sample.


## Version 1.1.0 regression checks

Run on 26 September 2026 with Python 3.12/Linux and headless Chromium:

- **52 Python tests passed.** Unknown crops do not invoke disease inference or receive forced classes. Simulated soybean identification blocks potato disease screening. Supported species may proceed; species mismatch, ambiguous species, absent consent and provider errors stop the online path.
- **Browser identity regression passed.** Default species mode, configured-versus-verified connection, rejected-key feedback, photo consent, simulated soybean result, unsupported-disease notice, no local fallback, clearing stale results on retry, journal persistence and 390 px layout were checked.
- **Browser baseline passed.** Desktop/mobile layout, guide filtering, dialogs, English/Gujarati navigation and missing-key state were exercised. Real-photo inference was not repeated in this update; the model files are unchanged.
- The original image validation, metadata stripping, checksum checks and data-split tests remain in the Python suite.

The soybean response in these checks is a test fixture, not a real recognition result. No live Pl@ntNet request with the user's key, actual user soybean photo, Windows launch or independent field-accuracy evaluation was performed. These tests establish software routing and error behavior only. The disease model still has 15 classes across three crops.

The browser routing regression can be rerun after installing Playwright as below:

```bat
set QA_PYTHON=%CD%\.venv\Scripts\python.exe
node tests\browser-identity.cjs
```

It starts its own server on port 18124 and intercepts provider responses in the test browser. It never uses a real API key or calls the real provider.

## Original version 1.0 baseline checks

Checked on 26 September 2026 with Python 3.12 on Linux and headless Chromium. These checks establish that the software paths run; they do not establish clinical/agronomic reliability.

| Check | Result |
|---|---|
| Python backend and data tests | 23 passed |
| Model integrity and label ordering | Both bundled ONNX files matched SHA-256; input/output dimensions matched the manifest |
| Real-photo inference smoke check | Expected top labels on three selected original PlantVillage photos: healthy tomato, potato late blight and bell-pepper bacterial spot |
| Desktop/mobile layout | Rendered and visually inspected at 1440 px and 390 px widths; no horizontal overflow in the mobile check |
| Browser flows | Guide filtering, details dialog, navigation language, photo upload, real inference, saving notes, journal persistence after reload, text export and unsupported-crop feedback passed |
| Browser text handling | A note containing HTML-like characters remained text |
| Offline browsing | Saved journal and cached guide remained available after simulated network loss and reload |
| Missing provider key | Identity action stayed unavailable with an explanatory message |
| Provider contracts | Mocked species, nested-variety, error and metadata-stripping checks passed; no real key was used |
| Training smoke check | Two synthetic classes, 16 images, one epoch without pretrained weights; completed splitting, training, calibration, ONNX export and held-out evaluation |
| Training export parity | Maximum absolute PyTorch/ONNX logit difference in the smoke export: approximately 1.86×10⁻⁹ |

The three dataset photos are not a random independent test set; they could overlap upstream training data. Their predictions are a plumbing check, not an accuracy estimate. They are not included in this ZIP. The disposable synthetic model is also not included; the app uses the upstream pretrained starter weights.

Not executed here: the Windows/macOS launchers on their actual operating systems, Docker build, full-dataset retraining/import, physical phone-camera capture, live Pl@ntNet requests, a farmer usability trial or an independent Indian-field evaluation. The provider response schema was checked against official documentation and simulated in tests.

## Re-run the Python tests

From the extracted project folder in CMD:

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest
```

The current dependency stack may emit a Starlette test-client deprecation warning. It does not affect the app or the passing tests.

## Optional browser test

The app itself requires no Node.js. For this developer-only test, install Node.js and Playwright:

```bat
npm install --no-save playwright
npx playwright install chromium
set QA_PYTHON=%CD%\.venv\Scripts\python.exe
set QA_PHOTO=C:\path\to\your\tomato-leaf.jpg
node tests\browser-smoke.cjs
```

The test starts its own local server on port 18123 and closes it on completion. Use a tomato leaf photo for the scan flow. With `QA_PHOTO` unset it runs layout/guide/language checks only. Outputs go to `test-results/`. This test expects the bundled 15-class model and no configured Pl@ntNet key; use a clean project environment for it. It has been updated for the 1.1 default species screen and explicit crop confirmation.

The testing environment used a separately supplied Chromium executable because its default browser download was unavailable. Browser selection can be overridden with `QA_CHROMIUM` and, when necessary, a JSON array in `QA_CHROMIUM_ARGS`. Those are test-runner settings, not app requirements.

## Checks worth doing before a real pilot

Choose independent crops/farms/seasons, obtain expert labels and separate the data from model development. Report per-class errors, how often the app abstains, and how often it accepts the wrong answer. Include unknown crops, soil/background photos, nutrient stress and multiple simultaneous symptoms. Review every new care card locally. Keep the model's supported scope visible to the farmer.
