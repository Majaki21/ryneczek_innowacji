"""Read-only public catalog for a shareable demo."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from .search import router

WEB = Path(__file__).resolve().parents[1] / "web"
ASSETS = {"style.css", "app.js", "market.svg"}
app = FastAPI(title="Ryneczek Innowacji", docs_url=None, redoc_url=None, openapi_url=None)

app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    return html.replace("<body>", "<body data-public-preview>")


@app.get("/{asset}")
def asset_file(asset: str):
    if asset not in ASSETS:
        raise HTTPException(404)
    return FileResponse(WEB / asset)
