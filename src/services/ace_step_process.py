"""Manages the ACE-Step 1.5 API server subprocess lifecycle."""

import logging
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_STOP_TIMEOUT = 10  # seconds to wait for graceful shutdown


def _get_api_port() -> int:
    """Parse the configured ACE-Step port from the api_url setting."""
    from src.database import get_setting
    url = get_setting("api_url", "http://127.0.0.1:8001")
    return urlparse(url).port or 8001


def is_port_in_use(port: int) -> bool:
    """Return True if something is already listening on *port*."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_ace_step(path: str) -> "subprocess.Popen | None":
    """Launch the ACE-Step API server as a background subprocess.

    Returns the Popen handle, or None if launch was skipped or failed.
    """
    if not path:
        logger.warning("ACE-Step autostart enabled but no path configured — skipping")
        return None

    repo = Path(path)
    if not repo.is_dir():
        logger.warning("ACE-Step path does not exist: %s — skipping", path)
        return None

    port = _get_api_port()
    if is_port_in_use(port):
        logger.info(
            "Port %d already in use — ACE-Step appears to be running, skipping launch",
            port,
        )
        return None

    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        proc = subprocess.Popen(
            ["uv", "run", "acestep-api"],
            cwd=repo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
        logger.info("ACE-Step server launched (pid %d) from %s", proc.pid, path)
        return proc
    except FileNotFoundError:
        logger.error("'uv' not found on PATH — cannot auto-start ACE-Step server")
    except Exception as exc:
        logger.error("Failed to launch ACE-Step server: %s", exc)
    return None


def stop_ace_step(proc: "subprocess.Popen | None") -> None:
    """Terminate the ACE-Step subprocess tree if it is still running."""
    if proc is None:
        return
    if proc.poll() is not None:
        return  # already exited

    logger.info("Stopping ACE-Step server (pid %d)…", proc.pid)
    if sys.platform == "win32":
        # taskkill /T kills the entire process tree (uv + its python child)
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
        )
        proc.wait()
    else:
        proc.terminate()
        try:
            proc.wait(timeout=_STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.warning("ACE-Step did not stop in time — killing process")
            proc.kill()
            proc.wait()
    logger.info("ACE-Step server stopped")
