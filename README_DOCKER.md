## Deploying SHL API with Docker (Python 3.11)

This repository provides a small FastAPI app serving `GET /health` and `POST /chat`.

What I added:
- `Dockerfile` — builds the app on Python 3.11 and runs `uvicorn main:app`.
- `.dockerignore` — excludes common files from the build context.

Local test (if you have Docker installed):

```bash
# build image
docker build -t shl-api:latest .

# run container (maps 8000)
docker run --rm -p 8000:8000 shl-api:latest

# test endpoints
curl -sS http://localhost:8000/health
curl -sS -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"Data scientist, mid-level hiring"}]}'
```

Render deployment notes:
- `render.yaml` already configured to use Docker. When you push these files to GitHub, Render will build the Docker image using Python 3.11.
- If you prefer I can push these changes to the project's GitHub and trigger the deploy for you.
