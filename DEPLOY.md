# Deploying to qr.tootiedesigns.com

This is a **Flask (Python) app** with server-side image processing, so it needs a
running Python process — it can't be served as a static site by GitHub Pages or
Cloudflare Pages. The shape is:

**GitHub (code) → Python host (runs Flask) → Cloudflare DNS (subdomain + HTTPS)**

## 1. Push to GitHub

```bash
git add .
git commit -m "Make app production-ready for deployment"
git push
```

## 2. Deploy the app to a Python host (Render — free, auto-deploys from GitHub)

1. Go to https://render.com and sign in with GitHub.
2. **New → Blueprint**, select this repo. Render reads `render.yaml` and provisions
   the web service automatically (build: `pip install -r requirements.txt`,
   start: `gunicorn app:app ...`).
3. When it finishes you get a URL like `https://qr-code-generator-xxxx.onrender.com`.
   Confirm it loads.

> Any host that reads a `Procfile` / `requirements.txt` works too (Railway, Fly.io,
> etc.). The `PORT` env var is injected by the host; the app already reads it.

## 3. Point the Cloudflare subdomain at it

1. In Render: your service → **Settings → Custom Domains → Add** `qr.tootiedesigns.com`.
   Render shows a **CNAME target** (e.g. `qr-code-generator-xxxx.onrender.com`).
2. In **Cloudflare → tootiedesigns.com → DNS → Add record**:
   - Type: **CNAME**
   - Name: **qr**
   - Target: *(the Render CNAME target)*
   - Proxy status: **Proxied** (orange cloud) — gives Cloudflare SSL + CDN
3. Wait for DNS + certificate to provision (usually minutes). `https://qr.tootiedesigns.com`
   is now live for desktop and mobile browsers.

## Notes

- **HTTPS / mobile:** Cloudflare terminates SSL; `ProxyFix` in `app.py` makes Flask
  trust the forwarded scheme so everything resolves as `https`.
- **SSL mode:** in Cloudflare → SSL/TLS, use **Full** (Render serves valid HTTPS).
- **Uploads:** generated PNGs live on the host's ephemeral disk (fine — they're
  created and downloaded immediately). Free Render instances sleep when idle and
  cold-start on the next request.
- **Mobile UI:** the page is already responsive (viewport meta, single-column
  stacking, 44px touch targets), so it renders correctly on phones as-is.

## Alternative: self-host via Cloudflare Tunnel

If you'd rather run the app on your own machine/VPS and expose it directly through
Cloudflare (no third-party host):

```bash
# on the machine running `python app.py` (or gunicorn)
cloudflared tunnel login
cloudflared tunnel create qr
cloudflared tunnel route dns qr qr.tootiedesigns.com
cloudflared tunnel run --url http://localhost:7860 qr
```

The machine must stay on for the site to stay up.
