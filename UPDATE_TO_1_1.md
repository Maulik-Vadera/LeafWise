> The current website release is 1.3. Follow `UPDATE_TO_1_3.md` for the complete update. These notes describe the earlier changes.

# Update Leafwise to 1.1.0 on Windows

Historical instructions for 1.1. For the current release, use [UPDATE_TO_1_2.md](UPDATE_TO_1_2.md).

This update fixes the flow that could show a potato/tomato possibility for an unknown plant. It does not contain a newly trained disease model.

1. In the terminal running the old app, press **Ctrl+C** to stop it.
2. Extract the updated ZIP into a **new folder**. Keep the old folder until this update is working.
3. Copy your existing **.env** file from the old Leafwise folder into the new Leafwise folder, alongside **Start-Windows.cmd**. Keep your key private. The ZIP contains no private key.
4. Double-click **Start-Windows.cmd** in the new folder. The new folder may need its first dependency installation.
5. Open **http://127.0.0.1:8000** and press **Ctrl+F5**. Look for **v1.1.0** near the top. If you changed the port, continue using your configured port.
6. Choose **Check connection**. If it reports a key, quota or network error, resolve that message first. **API setup help** explains where the key belongs.
7. Stay in **Identify a plant**. Add your soybean leaf photo, choose **Leaf**, tick the photo-sharing checkbox, and choose **Identify a plant**.

The page shows species candidates returned by Pl@ntNet, with scientific names. It may still be uncertain or wrong on an individual photo; add another view, flowers or fruit from the same plant where available. Your exact soybean photo has not been tested by the developer.

For soybean, the disease-coverage panel should report that disease screening is unavailable if Pl@ntNet returns Glycine max as a sufficiently distinct leading candidate. The included disease model still covers tomato, potato and bell pepper only. No exact cultivar or soybean disease diagnosis is promised.

## What changed

- Plant identification is the default mode.
- Unknown crops no longer receive forced local disease-model species guesses.
- An API key is labelled “configured” until a real connection check succeeds.
- Key/permission failures, quota limits and network problems have specific messages.
- Online disease screening checks the species before using the local model. Unsupported or unclear species stop the scan.
- Local-only disease screening requires you to choose and confirm a supported crop; it does not verify plant identity.
- A failed retry clears the old result instead of leaving a stale prediction visible.
- Provider failures never silently fall back to a tomato/potato species guess.

Your journal remains in the same browser at the same server address. Do not clear browser data to update the app. Keep `.env` out of source control and shared ZIPs.
