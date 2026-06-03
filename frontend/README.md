# VieNeu Studio

VieNeu Studio is a Next.js PWA control surface for the local VieNeu FastAPI server.

## Setup

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

Open `http://127.0.0.1:3000`.

## Backend

Start the backend separately:

```bash
vieneu-server
```

The browser-facing frontend defaults to a same-origin proxy:

```bash
NEXT_PUBLIC_VIENEU_API_BASE=/api/vieneu
```

The Next.js route at `/api/vieneu/*` forwards requests to:

```bash
VIENEU_INTERNAL_API_BASE=http://127.0.0.1:8000
```

Create `frontend/.env.local` to override these values.

For Docker or Cloudflare, keep the browser on the proxy path and point the internal backend URL at the Compose service:

```bash
NEXT_PUBLIC_VIENEU_API_BASE=/api/vieneu
VIENEU_INTERNAL_API_BASE=http://server:8000
```

This hides the backend origin from normal browser fetches and avoids CORS for HTTP/audio endpoints. It is not authentication; keep the backend private or protected if you do not want it called directly.

When running the Docker Compose Cloudflare profile, run from the repository root and pass the root `.env` explicitly:

```powershell
docker compose --env-file .env -f docker/docker-compose.pwa.yml --profile frontend-tunnel up --build
```

WebSocket upgrades cannot be proxied by a plain Next.js route handler. For realtime online events, route `/ws/*` to the backend in Cloudflare and optionally set:

```bash
NEXT_PUBLIC_VIENEU_WS_BASE=https://tts.example.com
```

Status polling remains active if WebSocket connection fails.

## Checks

```bash
pnpm lint
pnpm build
```
