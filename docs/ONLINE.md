# Run the app online

The API has **no authentication by default**. Only expose it behind a VPN, private network, or after you add auth (see `docs/DEPLOYMENT_AND_SECURITY.md`).

## 1. Try locally with Docker (fastest)

From the repo root:

```bash
docker build -t vantage-api .
docker run --rm -p 8000:8000 -v vantage-data:/data vantage-api
```

Open:

- **UI:** http://127.0.0.1:8000/ui/
- **Docs:** http://127.0.0.1:8000/docs
- **Health:** http://127.0.0.1:8000/health

Stop with Ctrl+C.

## 2. Expose your laptop (temporary public URL)

Use a tunnel if you only need a quick demo (no Docker host required):

```bash
# https://ngrok.com — after install:
ngrok http 8000
```

Or [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/). Share the HTTPS URL; **shut down the tunnel** when done.

## 3. Deploy from GitHub (persistent URL)

### Render (Blueprint)

1. Push this repo to GitHub (already done if you use `origin`).
2. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect the `LRO_DVA_SPK` repo and apply `render.yaml` at the root.
4. Wait for build; open the **Render HTTPS URL** + `/ui/`.

**Note:** Free instances **spin down** when idle; first request may take ~30–60s. Ephemeral disk: large uploads may fill the instance; adjust plan or attach storage for production.

### Fly.io (alternative)

```bash
fly launch --dockerfile Dockerfile --name army-vantage-preprocess
fly deploy
```

Follow prompts; set `VANTAGE_DATA_DIR` to a Fly volume path if you add persistent storage.

## 4. Environment variables (cloud)

| Variable | Typical value |
|----------|----------------|
| `VANTAGE_DATA_DIR` | `/data` (with volume) or default |
| `VANTAGE_MAX_UPLOAD_BYTES` | Lower on small instances (e.g. `52428800` = 50 MiB) |
| `VANTAGE_API_HOST` | `0.0.0.0` (container listens on all interfaces) |

## 5. HTTPS

Platforms (Render, Fly, Railway) terminate TLS for you. Do **not** serve plain HTTP to the public internet without a reverse proxy.
