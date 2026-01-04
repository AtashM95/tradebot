from __future__ import annotations

import webbrowser

import uvicorn

from src.core.settings import load_settings


if __name__ == "__main__":
    settings = load_settings()
    url = f"http://{settings.app.host}:{settings.app.port}"
    if settings.app.auto_open_browser:
        webbrowser.open(url)
    uvicorn.run("src.app.main:app", host=settings.app.host, port=settings.app.port, reload=False)
