# Put Leafwise on the web

This release includes a public HTML website, the scanner, an installable web app, and a Python backend. Keep them together in one Vercel project. Uploading only `web/index.html` will not provide plant identification.

## 1. Update your project files

Extract the new ZIP. Copy the **contents of its `Leafwise` folder** into the existing `Leafwise` folder in your project. Replace matching files. Keep your existing `.env` and `.venv` on your computer; do not delete your old project folder.

Commit the updated source to your GitHub repository. Include `web`, `app`, `models`, `requirements.txt`, `pyproject.toml`, `.python-version` and `vercel.json`. Keep the repository private if you prefer. Do not upload `.env`, `.venv` or your API key. The included `.gitignore` excludes those files for Git users.

The repository structure you described is:

```text
Leafwise-Helping-nature/
  Leafwise/
    vercel.json
    pyproject.toml
    .python-version
    requirements.txt
    app/
    models/
    web/
```

## 2. Import into Vercel

In the [Vercel dashboard](https://vercel.com/new), import your `Leafwise-Helping-nature` GitHub repository and use these settings:

| Setting | Value |
|---|---|
| Root Directory | `Leafwise` for the structure above |
| Framework Preset | FastAPI |
| Build Command | Leave the override off |
| Output Directory | Leave the override off |
| Install Command | Leave the override off |
| Environment variable name | `PLANTNET_API_KEY` |
| Environment variable value | Your private Pl@ntNet key |

If `vercel.json` and `requirements.txt` are already at the repository root, use `./` as Root Directory instead. Select the directory that **directly contains** those files. Do not select `web` and do not choose the “Other” static-site preset.

Set the key for **Production**. Add it to **Preview** only if you want preview deployments to use the same identification allowance. Use Vercel environment variables, not an uploaded `.env` file. The frontend never needs the key.

Choose **Deploy**. Vercel supplies the site address after the build succeeds. This ZIP has not been deployed to your Vercel account, and there is no live site address included.

For an existing Vercel project, update Root Directory and the key in Project Settings, then redeploy. A changed environment variable does not change a deployment that has already been built.

## 3. Check the published website

Open your production URL. The home page should appear. Choose **Open Leafwise**, then **Check connection** in the scanner. Confirm that it reaches Pl@ntNet before trying a photo.

Use **Identify a plant** for species, or **Check plant health → Online** for disease and pest candidates. A failed connection is shown as an error; it is never replaced with a made-up plant or disease result.

Open the production URL in a private browser window to check that visitors can reach it without your Vercel login. If the deployment is protected, use the production domain and review your project's Deployment Protection setting for the intended public site.

## 4. Visitors install from the website

Share the production URL. Visitors open it and choose **Install app**. A supported browser displays its installation prompt; other browsers receive device-specific instructions. On iPhone/iPad, use the browser's Share menu → Add to Home Screen. On desktop, Chrome or Edge can install it from the browser menu/address bar.

This is a **PWA (installable web app)**, not an APK or App Store submission. Visitors do not install Python or supply an API key. The public website must use HTTPS for installation. Online species and disease checks still need internet and use your shared API allowance. Journal entries stay in the browser that saved them.

## Custom domain, optional

Add the domain in Vercel. Then add a server environment variable, for example:

```text
ALLOWED_HOSTS=leafwise.example.org,www.leafwise.example.org
```

Use your actual hostname(s), without `https://` or paths. Redeploy after changing it. Leafwise also admits the exact Vercel deployment, branch and production hostnames provided by Vercel's system environment variables. Keep those system variables available to the app. Do not replace host checking with `*`.

## If something goes wrong

| What you see | What to do |
|---|---|
| Build cannot find the app or requirements | Set Root Directory to the folder directly containing `vercel.json`, `requirements.txt` and `app`. |
| “Invalid host header” | Check that Vercel system environment variables are exposed. Add your exact custom domain to `ALLOWED_HOSTS`, then redeploy. |
| Website opens, but online scanning is unavailable | Add `PLANTNET_API_KEY` to this deployment's environment and redeploy. A local `.env` does not configure Vercel. |
| Key rejected / service not authorized | Check your key and its service permissions in Pl@ntNet. Do not enable browser exposure for this server-held key. |
| Provider quota reached | The website's visitors share your account allowance. Wait for the reset or review the provider account. |
| Installation button shows instructions | Some browsers don't expose an install prompt. Follow the displayed menu steps or continue in the browser. |
| You still see an older interface | Close other Leafwise tabs/app windows, reopen, then reload. Avoid clearing browser storage unless your journal is exported. |

## What the deployment files do

- `pyproject.toml` identifies `app.main:app` as the FastAPI entrypoint. `.python-version` selects Python 3.12. Runtime dependencies are pinned in `requirements.txt`.
- `vercel.json` allows a 60-second function duration and excludes development files and secrets. Security middleware stays active for static files as well as API routes.
- Photos are resized to at most 1600 pixels on the longest side and at most 1 MB each before upload. Three uploads plus form fields stay below Vercel's documented 4.5 MB request limit. Server validation and metadata stripping remain enabled.
- The bundled 15-class starter model runs on the server. Installing the website does not move it onto the visitor's phone.

This release supports an anonymous public demo. Its basic in-memory rate limit is per server instance, not a global or per-account quota system. Before broad public promotion, use deployment-level traffic limits and monitor the provider allowance. There is no authentication, cross-device journal sync or paid-user metering in this release.

## Official references checked for this release

- [Vercel FastAPI deployment](https://vercel.com/docs/frameworks/backend/fastapi)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel function limits](https://vercel.com/docs/functions/limitations)
- [MDN: installable web apps](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable)
- [Pl@ntNet disease and pest service](https://my.plantnet.org/doc/api/diseases)

Local route, browser and mocked-provider tests are documented in `docs/TESTING.md`. A real Vercel build and physical-device installation still need checking after deployment.
