"""Koibokksu v2 — Lo-Fi Radio Desktop App entry point.

Starts a FastAPI server in a background thread and opens a pywebview window.
"""

import asyncio
import logging
import mimetypes
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports work
# regardless of how the script is invoked.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Fix Windows MIME types — Python's mimetypes module reads from the
# registry which can serve .js as text/plain, blocking ES modules.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

import requests
import uvicorn
import webview
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import ALBUM_COVERS_DIR, STATIC_DIR
from src.database import close_db, init_db
from src.routes import albums, audio, categories, playlists, radio, settings, tracks, weather
from src.services.buffer import start_buffer_worker

APP_TITLE = "koibokksu"
HOST = "127.0.0.1"
PORT = 18920

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    init_db()
    asyncio.create_task(start_buffer_worker())
    logger.info("Server ready on http://%s:%s", HOST, PORT)
    yield
    close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title=APP_TITLE, lifespan=lifespan)

    app.include_router(radio.router, prefix="/api")
    app.include_router(tracks.router, prefix="/api")
    app.include_router(playlists.router, prefix="/api")
    app.include_router(albums.router, prefix="/api")
    app.include_router(categories.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    app.include_router(audio.router, prefix="/api")
    app.include_router(weather.router, prefix="/api")

    app.mount("/album-covers", StaticFiles(directory=str(ALBUM_COVERS_DIR)), name="album-covers")
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


def run_server(app: FastAPI):
    """Run uvicorn in the current thread."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def wait_for_server(timeout=10):
    """Block until the server is responding, or timeout."""
    url = f"http://{HOST}:{PORT}/api/radio/genres"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    logger.warning("Server did not become ready within %ds", timeout)
    return False


def main():
    """Launch the application: start server thread, then open pywebview."""
    app = create_app()

    server_thread = threading.Thread(target=run_server, args=(app,), daemon=True)
    server_thread.start()

    # Wait for server to be ready before opening the window
    wait_for_server()

    class WindowApi:
        """Expose window actions to the JS bridge."""

        def __init__(self, win):
            self._win = win

        def minimize(self):
            self._win.minimize()

        def close(self):
            self._win.destroy()

    window = webview.create_window(
        APP_TITLE,
        f"http://{HOST}:{PORT}",
        width=800,
        height=640,
        resizable=False,
        frameless=True,
    )

    api = WindowApi(window)
    window.expose(api.minimize, api.close)
    webview.start()


if __name__ == "__main__":
    main()
