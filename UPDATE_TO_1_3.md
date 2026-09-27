# Update to Leafwise 1.3 — website + installable app

**Keep your existing folder. Do not delete it.**

1. Stop Leafwise by pressing Ctrl+C in its terminal.
2. Extract the new ZIP into a temporary location.
3. Copy everything inside the new `Leafwise` folder into your existing `Leafwise` folder. Choose **Replace files** when Windows asks. The ZIP has no `.env` or `.venv`, so your existing key and installed environment are preserved.
4. Double-click `Start-Windows.cmd`. Open `http://127.0.0.1:8000` if the browser doesn't open automatically.
5. The new website appears. Choose **Open Leafwise** to scan, or **Install app** for browser installation.

If updating GitHub/Vercel instead, follow **DEPLOY_ON_VERCEL.md**. Include the full backend and model folders; uploading only the HTML file is not enough.

## What's included

- Public website at `/`, with responsive HTML/CSS, feature explanations, privacy information and installation help.
- Scanner and journal at `/app`. Old `/#scan`, `/#journal` and `/#guide` bookmarks forward to the new address.
- A shared install flow on the website and scanner. The browser's native prompt is used when available; otherwise it shows the right menu instructions. It does not pretend to download an APK.
- PWA manifest, icons and an updated offline cache. Installation opens the scanner directly. Existing journal storage is preserved on the same origin (same protocol, hostname and port).
- Ready-to-configure Vercel files, hosted-domain support and automatic photo compression for uploads.
- The version 1.2 health upgrade: **Check plant health** defaults to Pl@ntNet's disease/pest service. It uses the existing Pl@ntNet key and requires photo-sharing consent. It has limited plant/condition coverage and does not guarantee a diagnosis.
- The old three-crop model remains an explicitly selected starter option. Its weights are unchanged; it is never silently substituted when the online service fails.

## Quick check

Open Leafwise → **Check connection** → **Check plant health**. Leave Health analysis set to **Online · Pl@ntNet disease & pest identification**. Add a clear affected-area photo, tick the sharing permission, then choose **Check disease & pests**. “View supported conditions” loads the provider's current catalog; it does not promise that every listed condition is supported for every plant species.

Your public Vercel domain has a different journal from `localhost`. Export records you need before moving. PWA installation does not enable online identification without internet, and phone scans do not run the Python model on the phone.
