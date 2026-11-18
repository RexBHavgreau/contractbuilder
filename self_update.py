"""Download a newer Windows build and put it in place of the running one.

A running .exe cannot replace itself on Windows, so the swap is done by a
small batch script that starts as the app closes: it waits until the old
file is free, moves the new one over it, and starts the new version.

The download goes beside the running .exe (so the move is a rename on the
same drive). If that folder cannot be written to, such as under
C:\\Program Files, the file is saved to Downloads instead and the person is
told where it is.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

WINDOWS_ASSET = "Word-Template-Filler-windows-x64.exe"
CHUNK = 256 * 1024


class UpdateInstallError(Exception):
    """A readable failure while downloading or installing an update."""


def can_install_in_place() -> bool:
    """Only a built Windows app can swap its own .exe."""
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def running_executable() -> Path:
    return Path(sys.executable).resolve()


class _DropAuthOnRedirect(HTTPRedirectHandler):
    """
    GitHub answers an asset download with a redirect to its file storage,
    which refuses requests that still carry the GitHub token. Drop the
    token whenever a redirect leaves the host it was meant for.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urlsplit(newurl).netloc != urlsplit(req.full_url).netloc:
            for name in list(new.headers):
                if name.lower() == "authorization":
                    del new.headers[name]
            new.unredirected_hdrs.pop("Authorization", None)
        return new


def _opener():
    return build_opener(_DropAuthOnRedirect)


def download_asset(asset, destination: Path, token: str = "", progress=None, timeout: float = 60.0) -> Path:
    """
    Download a release asset to destination, checking its size and, when
    GitHub publishes one, its SHA-256 digest. progress(done, total) is
    called as it goes. A failed download leaves nothing behind.
    """
    if token or not asset.download_url:
        url, headers = asset.api_url, {"Accept": "application/octet-stream"}
    else:
        url, headers = asset.download_url, {}
    headers["User-Agent"] = "Word-Template-Filler"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    destination = Path(destination)
    partial = destination.with_name(destination.name + ".part")
    digest = hashlib.sha256()
    done = 0
    try:
        with _opener().open(Request(url, headers=headers), timeout=timeout) as response, \
                open(partial, "wb") as out:
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, asset.size)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise UpdateInstallError(f"The download did not finish: {exc}") from exc

    problem = check_download(asset, done, digest.hexdigest())
    if problem:
        partial.unlink(missing_ok=True)
        raise UpdateInstallError(problem)
    os.replace(partial, destination)
    return destination


def check_download(asset, size: int, sha256: str) -> str:
    """'' when the download matches what GitHub says it should be, else why not."""
    if size <= 0:
        return "The downloaded file is empty."
    if asset.size and size != asset.size:
        return f"The download is {size} bytes, but GitHub says it should be {asset.size}."
    if asset.digest.lower().startswith("sha256:"):
        expected = asset.digest.split(":", 1)[1].strip().lower()
        if expected and expected != sha256.lower():
            return "The downloaded file does not match GitHub's fingerprint (SHA-256), so it was discarded."
    return ""


def folder_is_writable(folder: Path) -> bool:
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix=".write-test-", delete=True):
            return True
    except OSError:
        return False


def downloads_folder() -> Path:
    folder = Path.home() / "Downloads"
    return folder if folder.is_dir() else Path.home()


def swap_script(attempts: int = 60) -> str:
    """
    The batch script that replaces the app (%1) with the download (%2) once
    the app is no longer running, then starts it. The paths arrive as
    arguments rather than written into the script, so any characters in
    folder names survive. It retries the move for about a minute, because the
    old .exe stays locked until the app has fully closed. If the move never
    succeeds it starts the old version again and leaves a note beside it.
    """
    return "\r\n".join([
        "@echo off",
        "setlocal",
        'set "TARGET=%~1"',
        'set "NEWFILE=%~2"',
        "set /a TRIES=0",
        ":retry",
        'move /y "%NEWFILE%" "%TARGET%" >nul 2>&1',
        "if not errorlevel 1 goto started",
        "set /a TRIES+=1",
        f"if %TRIES% geq {attempts} goto failed",
        "ping -n 2 127.0.0.1 >nul",
        "goto retry",
        ":started",
        'start "" "%TARGET%"',
        'del "%~f0"',
        "exit /b 0",
        ":failed",
        'echo The update could not replace the app. The new version was left at "%NEWFILE%".> "%TARGET%.update-failed.txt"',
        'start "" "%TARGET%"',
        'del "%~f0"',
        "exit /b 1",
        "",
    ])


def swap_command(script: Path, target: Path, new_file: Path) -> str:
    """
    The exact command line. cmd /s /c drops only the outermost pair of
    quotes, so every path keeps its own quotes whatever spaces it holds
    (a temp folder under a user name with a space included).
    """
    return f'cmd.exe /d /s /c ""{script}" "{target}" "{new_file}""'


def start_swap(target: Path, new_file: Path) -> None:
    """Start the swap script in the background. The caller then closes the app."""
    script = Path(tempfile.gettempdir()) / "word-template-filler-update.cmd"
    script.write_text(swap_script(), encoding="ascii")
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(swap_command(script, target, new_file),
                     creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



def cleanup_stale_update_download(target: Path, now: float | None = None,
                                  max_age: float = 24 * 60 * 60) -> bool:
    """Remove an abandoned .new update download older than max_age seconds.

    A recent file is left alone because the update swap may still be running.
    Only a regular, non-symlink file is eligible. Returns whether it was removed.
    """
    candidate = Path(target).with_name(Path(target).name + ".new")
    try:
        info = candidate.lstat()
        if not candidate.is_file() or candidate.is_symlink():
            return False
        current_time = time.time() if now is None else now
        if current_time - info.st_mtime <= max_age:
            return False
        candidate.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False

def leftover_note(target: Path) -> str:
    """The note a failed swap leaves beside the app, if any, removed once read."""
    note = target.with_name(target.name + ".update-failed.txt")
    try:
        text = note.read_text(errors="replace").strip()
        note.unlink()
        return text
    except OSError:
        return ""


# --------------------------------------------------------------- settings ---

def settings_path() -> Path:
    """Beside the publisher profiles, in the per-user app data folder."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "TMAI Contract Builder" / "update-settings.json"


AUTOMATIC_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


def _load_update_settings(path: Path | None = None) -> dict:
    try:
        data = json.loads((path or settings_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_update_settings(data: dict, path: Path | None = None) -> None:
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_token(path: Path | None = None) -> str:
    return str(_load_update_settings(path).get("github_token", ""))


def save_token(token: str, path: Path | None = None) -> None:
    data = _load_update_settings(path)
    data["github_token"] = token.strip()
    _save_update_settings(data, path)


def automatic_update_check_due(path: Path | None = None, now: float | None = None) -> bool:
    """Return whether an automatic check is due, using the last successful check."""
    last_check = _load_update_settings(path).get("last_successful_check")
    try:
        last_check = float(last_check)
        current_time = time.time() if now is None else float(now)
    except (TypeError, ValueError):
        return True
    return current_time - last_check >= AUTOMATIC_CHECK_INTERVAL_SECONDS


def record_successful_update_check(path: Path | None = None, now: float | None = None) -> None:
    """Remember a successful manual or automatic check without discarding the token."""
    data = _load_update_settings(path)
    data["last_successful_check"] = time.time() if now is None else float(now)
    _save_update_settings(data, path)
