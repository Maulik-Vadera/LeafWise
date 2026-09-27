> The current website release is 1.3. Follow `UPDATE_TO_1_3.md` for the complete update. These notes describe the earlier changes.

# Update Leafwise to 1.2.0 — online disease identification

Keep your current working Leafwise folder. This update adds a real call to Pl@ntNet's separate disease/pest model using the same `PLANTNET_API_KEY` setting.

## Update without losing your key

1. Stop Leafwise with **Ctrl+C** in its terminal.
2. Right-click the new ZIP and choose **Extract All** into a temporary folder, such as Downloads. Open the extracted **Leafwise** folder.
3. Press **Ctrl+A**, then **Ctrl+C** to copy the files and subfolders inside it.
4. Open your **current working Leafwise folder** (the one containing your working `.env` and `Start-Windows.cmd`). Press **Ctrl+V**. Choose **Replace the files in the destination** when Windows asks.
5. Double-click **Start-Windows.cmd** in that current working folder.
6. Refresh the app with **Ctrl+F5**. The top of the page should show **v1.2.0**.

The ZIP contains no `.env` or `.venv`, so copying its contents into your working folder preserves your private key and Python environment. Do not delete or replace the whole working folder. If you edited the source code yourself, keep a copy of those edits before replacing matching files. Your journal stays in the same browser at the same server address.

## Check a disease or pest

1. Choose **Check plant health**.
2. Leave **Health analysis** set to **Online · Pl@ntNet disease & pest identification**.
3. Add sharp photographs of affected parts of one plant. One close-up plus a wider view is useful. Select the correct plant part under each photo.
4. Tick the photo-sharing checkbox and choose **Check disease & pests**.
5. Read the possible condition, provider score and reference link. Save observations to your journal if useful.

The default health option sends photos to `/v2/diseases/identify`; it does not run the old three-crop disease model. API errors stop the scan instead of silently switching to that model. The **Offline starter model · 3 crops only** option remains available for learning and limited local screening.

**View supported conditions** retrieves the provider's current disease/pest catalog. It is not a host-plant coverage list. Pl@ntNet documents limited plant/pathology coverage, so identifying soybean as a species does not prove it can diagnose every soybean disease. A missing match does not mean healthy, and a candidate does not confirm an infection or prescribe treatment.

One disease scan uses one identification credit from the quota shared with species scans, according to [Pl@ntNet's disease documentation](https://my.plantnet.org/doc/api/diseases).

## What was verified

The implementation and browser flow were checked against simulated provider responses and the official API contract. The tests verify endpoint selection, parsing, upload consent, errors, no-match behavior and independence from the local starter model. They do not measure real disease-recognition accuracy. Your real leaf photographs and private key were not used in these tests.
