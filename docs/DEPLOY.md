# Deployment

Three ways to run TIMEPOINT Flash: local development, Replit (one-click), or production.

---

## Local Development

```bash
git clone https://github.com/realityinspector/timepoint-flash-deploy.git
cd timepoint-flash-deploy
pip install -e .
cp .env.example .env    # Add your API keys
alembic upgrade head     # Run database migrations
./run.sh -r              # Start with auto-reload on port 8000
```

Swagger docs at `http://localhost:8000/docs`

---

## Replit (Recommended for Quick Deploy)

The repo includes `.replit`, `replit.nix`, and `start.sh` — Replit runs automatically on import.

### Setup

1. **Create a new Replit** → "Import from GitHub" → paste:
   ```
   https://github.com/realityinspector/timepoint-flash-deploy
   ```

2. **Set Secrets** in the Replit sidebar (Secrets tab):

   | Secret | Required | Source |
   |--------|----------|--------|
   | `GOOGLE_API_KEY` | Yes | [aistudio.google.com](https://aistudio.google.com) (free) |
   | `OPENROUTER_API_KEY` | No | [openrouter.ai](https://openrouter.ai) (enables hyper/gemini3 presets) |
   | `JWT_SECRET_KEY` | Only if `AUTH_ENABLED=true` | Random 32+ char string (e.g. `openssl rand -hex 32`) |

3. **Hit Run** — done. The server starts on port 8080 and Replit assigns a public URL.

### What Happens on Run

The `.replit` file calls `start.sh`, which:

1. Installs Python dependencies (`pip install -e .` — cached after first run)
2. Runs Alembic database migrations (`alembic upgrade head`)
3. Patches any ORM columns missing from migrations
4. Starts uvicorn on `0.0.0.0:8080`

No manual setup required. On subsequent runs, pip cache makes startup fast (~3-5 seconds).

### Replit File Reference

| File | Purpose |
|------|---------|
| `.replit` | Tells Replit what command to run, port mapping, env vars |
| `replit.nix` | Nix packages: Python 3.11, pip, SQLite |
| `start.sh` | Startup script: deps, migrations, server |

### Verify

```bash
curl https://your-repl.replit.dev/health
# → {"status":"healthy","version":"2.3.3","database":true,"providers":{"google":true,"openrouter":true}}
```

### Generate a Scene

```bash
curl -X POST https://your-repl.replit.dev/api/v1/timepoints/generate/sync \
  -H "Content-Type: application/json" \
  -d '{"query": "Alan Turing breaks Enigma at Bletchley Park Hut 8, winter 1941", "preset": "balanced", "generate_image": true}'
```

### Replit Deployment (Always-On)

To keep the server running after you close the browser:

1. Go to the **Deployments** tab in Replit
2. Select **Reserved VM** or **Autoscale**
3. Replit uses the `[deployment]` section in `.replit` (runs with 2 workers)

---

## Production

For production deployment (AWS, GCP, Railway, Fly.io, etc.):

### Environment

```bash
GOOGLE_API_KEY=your-key
OPENROUTER_API_KEY=your-key
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/timepoint
ENVIRONMENT=production
BLOB_STORAGE_ENABLED=true

# Auth (only needed if AUTH_ENABLED=true — for iOS app mode)
AUTH_ENABLED=false            # default: false — existing deployments unaffected
JWT_SECRET_KEY=your-random-secret-here   # required when AUTH_ENABLED=true
APPLE_BUNDLE_ID=com.yourcompany.app      # required when AUTH_ENABLED=true
SIGNUP_CREDITS=50
```

> **Note:** `AUTH_ENABLED=false` is the default. Existing deployments are unaffected — all endpoints remain open-access. Set `AUTH_ENABLED=true` only when deploying for the iOS app.

### Database

TIMEPOINT supports SQLite (development) and PostgreSQL (production):

```bash
# PostgreSQL
pip install asyncpg
export DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/timepoint
alembic upgrade head
```

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
```

Or with the included script:

```bash
./run.sh -P   # Production mode: 0.0.0.0, 4 workers, no reload
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
RUN alembic upgrade head
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
```

---

## Blob Storage

When `BLOB_STORAGE_ENABLED=true`, each generation writes a self-contained folder:

```
output/timepoints/2026/02/
└── alan-turing-breaks-enigma_20260209_d46138/
    ├── image.png              # Generated image
    ├── metadata.json          # Scene, characters, dialog
    ├── generation_log.json    # Step timings, models used
    ├── manifest.json          # File inventory with SHA256 hashes
    └── index.html             # Self-contained viewer (dark theme)
```

Each folder is portable — copy it anywhere and open `index.html` to view the complete scene.

---

*Last updated: 2026-02-09*
