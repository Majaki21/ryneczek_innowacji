"""Public catalog and optional private project submissions."""
from contextlib import asynccontextmanager
import os
from pathlib import Path

from starlette.responses import JSONResponse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import ValidationError

from .search import router

WEB = Path(__file__).resolve().parents[1] / "web"
ASSETS = {"style.css", "app.js", "market.svg"}
storage = os.environ.get("RYNECZEK_SUBMISSIONS_DIR")
enabled = bool(storage and Path(storage).is_dir() and os.path.ismount(storage))
if enabled:
    os.environ["RADAR_SQLITE"] = str(Path(storage) / "ryneczek-zgloszenia.sqlite3")
    os.environ["RADAR_UPLOADS"] = str(Path(storage) / "zalaczniki")
    from .api import Project, add_project
    from .db import initialize


@asynccontextmanager
async def lifespan(app):
    if enabled:
        initialize()
    yield


app = FastAPI(lifespan=lifespan, title="Ryneczek Innowacji", docs_url=None, redoc_url=None, openapi_url=None)

app.include_router(router)

if enabled:
    @app.post("/api/projects", status_code=201)
    async def submit(request: Request):
        from starlette.concurrency import run_in_threadpool

        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 56 * 1024 * 1024:
                raise HTTPException(413, "Zgłoszenie przekracza dozwolony rozmiar.")
            body.extend(chunk)
        try:
            project = Project.model_validate_json(body)
        except ValidationError as exc:
            raise HTTPException(422, "Sprawdź dane formularza.") from exc
        return await run_in_threadpool(add_project, project)
else:
    @app.post("/api/projects")
    def submissions_unavailable():
        return JSONResponse(
            {"detail": "Zapisywanie zgłoszeń wymaga podłączenia trwałego dysku."}, status_code=503
        )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    mode = "data-public-form" if enabled else "data-public-preview"
    return html.replace("<body>", f"<body {mode}>")


@app.get("/{asset}")
def asset_file(asset: str):
    if asset not in ASSETS:
        raise HTTPException(404)
    return FileResponse(WEB / asset)
