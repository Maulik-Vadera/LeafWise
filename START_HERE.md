> **Version 1.3:** Already have Leafwise? Use `UPDATE_TO_1_3.md` and keep your existing folder. To publish a website, use `DEPLOY_ON_VERCEL.md`. After starting locally, choose **Open Leafwise** on the home page to reach the scanner.

# Start Leafwise on Windows

Leafwise runs in your browser with a Python server on your computer. Species and online disease checks use your Pl@ntNet key. A limited offline starter model is also included. No OpenAI key is needed. Already using Leafwise? Follow [UPDATE_TO_1_2.md](UPDATE_TO_1_2.md) to preserve your working configuration.

## 1. Extract the ZIP

Right-click the ZIP → **Extract All**. Put the extracted `Leafwise` folder somewhere convenient, such as `C:\Users\mauli\Projects\Leafwise`. Run it from the extracted folder, not from inside the ZIP preview.

## 2. Install Python 3.12, 64-bit

Use [Python's official Windows downloads](https://www.python.org/downloads/windows/). Keep the Python launcher enabled during installation. You can keep Python 3.14 or other versions installed alongside it.

In **Command Prompt**, check:

```bat
py -3.12 --version
```

It should print a Python 3.12 version. This project was tested with Python 3.12 on Linux; the Windows launcher is supplied but was not run on a Windows machine here.

## 3. Double-click `Start-Windows.cmd`

The first launch creates a private `.venv` folder and installs the listed Python packages. This requires an internet connection. Later launches reuse the environment. It does not change PowerShell's execution policy or your global Python installation.

A browser window should open at **http://127.0.0.1:8000**. If it doesn't, enter that address yourself. Keep the terminal window open while using the app. Press **Ctrl+C** in that terminal to stop it.

## 4. Try a scan

The app opens in **Identify a plant**. This is the mode for soybean, trees and other plants. It needs a working Pl@ntNet key and internet; setup is below. Adding a key does not expand the local disease model's training.

For online disease or pest identification:

1. Choose **Check plant health** and leave **Online · Pl@ntNet disease & pest identification** selected.
2. Add up to three clear pictures of affected parts of the same plant. Select each photographed plant part.
3. Tick the photo-sharing box and choose **Check disease & pests**. A provider error stops the scan; it never substitutes the local model.
4. Read the possible conditions, reference links and observation steps. A missing result does not establish health.
5. Add a note and choose **Save to journal**. **Download report** creates a text report. **Print / PDF** opens your browser's print dialog.

The online service has limited plant/condition coverage. **View supported conditions** fetches its current condition list. A species result does not certify disease coverage or confirm infection.

For the original local model, explicitly choose **Offline starter model · 3 crops only**, select a known tomato/potato/bell-pepper crop, add leaf photos, and confirm the crop. The **Local only** verification setting works without internet after setup; it cannot verify an unfamiliar plant. The local weights have not changed and do not cover soybean.

## What works immediately?

| Feature | What you get |
|---|---|
| Online health scanning | Pl@ntNet disease/pest candidates; needs a working key and internet; limited provider coverage |
| Offline starter scanning | Included trained model; 15 classes across tomato, potato and bell pepper |
| Photo handling | Camera, file picker, drag-and-drop, up to three views |
| Guidance | Signs to inspect, non-chemical first steps and source links |
| Journal | Saved locally in this browser, with a thumbnail and your note |
| Reports | Text download, journal JSON export, browser print/PDF |
| Navigation | English, Hindi and Gujarati; detailed guidance stays in English |
| Broader plant identity | Optional Pl@ntNet connection; needs the owner's key and internet |
| Variety / cultivar | Optional provider feature with limited crop coverage; no universal guarantee |

After installation, local crop-health inference works without internet **while the Python server is running**. Cached guides and the journal can be browsed without the server. This is not a standalone Android APK or iPhone app; it is a responsive, installable web app.

## Connect species and online disease identification

1. Create a developer account and key at [Pl@ntNet](https://my.plantnet.org/). Check its current quota and terms.
2. Copy `.env.example` to a new file called `.env` in the project folder. In CMD:

   ```bat
   if not exist .env copy .env.example .env
   notepad .env
   ```

3. Add your key after `PLANTNET_API_KEY=`. Do not add it to JavaScript or send it to others.
4. Restart Leafwise.
5. Open the app and choose **Check connection**. This validates the key through Pl@ntNet's quota API without sending photos. Merely finding a key in `.env` does not mean the connection works. Leave “Expose my API key” unchecked in Pl@ntNet settings for this server app.
6. Select **Identify a plant**, add photos of the same individual, select each plant part, tick the photo-sharing checkbox, and submit.

The integrations have been tested with simulated provider responses, not your live key or photographs. Requests use your provider quota. Species, disease and cultivar services are distinct; success in one does not establish the others' recognition accuracy.

## Manual CMD commands

Open Command Prompt in the extracted project folder:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

You do not need to activate the virtual environment, install Node.js, or change script execution policies.

## Common fixes

| Message / situation | Next step |
|---|---|
| `py` or Python 3.12 not found | Install official 64-bit Python 3.12 with the Python launcher, then reopen CMD |
| A package won't install | Confirm `py -3.12 --version`, check internet, and use the manual commands |
| `onnxruntime` DLL import problem | Confirm 64-bit Python; consult [ONNX Runtime's installation prerequisites](https://onnxruntime.ai/docs/install/) for Microsoft's Visual C++ runtime requirements |
| Browser cannot connect | Keep the terminal running and look for its error message; use `127.0.0.1:8000` |
| Port 8000 is already in use | Copy `.env.example` to `.env`, set `PORT=8001`, restart, then use `127.0.0.1:8001` |
| Model unavailable / checksum failure | Run `.venv\Scripts\python.exe scripts\restore_starter_model.py`, then restart |
| Camera denied | Allow camera permission for localhost, or use a saved photo; file upload always remains available |
| Phone photo is HEIC | Export as JPEG first; JPEG, PNG and WebP are supported |
| Photo larger than 6 MB | Export a smaller copy; keep the leaf sharp and visible |
| Identity button disabled | Configure the Pl@ntNet key, restart, add a photo and check the sharing box |
| The page still looks like the old app | Stop the old terminal, run the updated folder, then press Ctrl+F5; the page should show v1.2.0 |
| Key entered but not found | Ensure the file is named `.env`, not `.env.txt`, and restart the server |
| Pl@ntNet rejected the key | Check the key and account permissions; leave “Expose my API key” unchecked for this server app, then restart |
| Health scans still use the old three-crop model | Confirm v1.2.0 and choose Online · Pl@ntNet disease & pest identification under Health analysis |
| No disease match | Try better photographs and consult an adviser; the cause may be outside provider coverage, and no match does not prove health |
| Journal appears empty in another browser | Journal data belongs to the original browser and server address; it does not sync |

Start by reading `README.md`, then `docs/ARCHITECTURE.md`. For your own model, continue with `docs/TRAINING.md`. All source code is editable.
