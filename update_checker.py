"""Check GitHub Releases for a newer application version.

No credentials are embedded in the application. Public releases work without
configuration. An optional read-only token can be saved in the app (Help >
Update settings), or supplied through the CONTRACTBUILDER_GITHUB_TOKEN or
GH_TOKEN environment variable, to raise the API rate limit.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class UpdateCheckError(Exception):
    """A readable failure while checking the release endpoint."""

    def __init__(self, message: str, needs_token: bool = False):
        super().__init__(message)
        self.needs_token = needs_token     # a token may be needed or may not have worked


@dataclass(frozen=True)
class ReleaseAsset:
    """One file attached to a release."""

    name: str
    api_url: str                     # API URL for authenticated downloads
    download_url: str                # works for public repositories, without one
    size: int
    digest: str = ""                 # "sha256:...", when GitHub supplies it


@dataclass(frozen=True)
class ReleaseInfo:
    current_version: str
    latest_version: str
    release_url: str
    release_name: str
    notes: str
    published_at: str
    assets: tuple = field(default=())

    @property
    def available(self) -> bool:
        return version_key(self.latest_version) > version_key(self.current_version)

    def asset(self, name: str):
        for item in self.assets:
            if item.name == name:
                return item
        return None


def version_key(value: str) -> tuple[int, ...]:
    """Convert a v-prefixed or plain dotted version to comparable integers."""
    match = re.search(r"\d+(?:\.\d+)*", str(value))
    if not match:
        raise ValueError(f"Unrecognized version: {value!r}")
    parts = [int(part) for part in match.group(0).split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def environment_token() -> str:
    return (
        os.environ.get("CONTRACTBUILDER_GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or ""
    )


def check_for_update(
    current_version: str,
    repository: str,
    timeout: float = 5.0,
    token: str | None = None,
) -> ReleaseInfo:
    """Retrieve the latest published GitHub release and compare its tag."""
    token = token or environment_token()
    url = f"https://api.github.com/repos/{repository}/releases/latest"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Word-Template-Filler",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            if token:
                raise UpdateCheckError(
                    "GitHub returned 404 while using the saved token. Either no release "
                    "has been published yet, the repository has moved, or the token "
                    "cannot read this repository: it needs read-only Contents access to it.",
                    needs_token=True,
                ) from exc
            raise UpdateCheckError(
                "GitHub has no published release for this app yet, or the repository has moved."
            ) from exc
        if exc.code in (403, 429):
            headers = {
                str(name).lower(): str(value).strip()
                for name, value in (exc.headers or {}).items()
            }
            rate_limited = (
                exc.code == 429
                or headers.get("x-ratelimit-remaining") == "0"
                or "retry-after" in headers
            )
            if rate_limited:
                raise UpdateCheckError(
                    "GitHub is limiting update checks from your network for now. "
                    "The app will try again later."
                ) from exc
        if exc.code == 401:
            raise UpdateCheckError(
                "GitHub did not accept the update-check credentials. Remove or "
                "replace the optional token in Help > Update settings."
            , needs_token=True) from exc
        if exc.code == 403:
            raise UpdateCheckError(
                "GitHub refused the update check. If you saved an optional token, "
                "check it in Help > Update settings."
            ) from exc
        raise UpdateCheckError(f"GitHub returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise UpdateCheckError(
            "Could not reach GitHub. Check your internet connection and try again."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateCheckError("GitHub returned an unreadable release response.") from exc

    tag = str(payload.get("tag_name", "")).strip()
    if not tag:
        raise UpdateCheckError("The latest GitHub release has no version tag.")
    try:
        version_key(tag)
        version_key(current_version)
    except ValueError as exc:
        raise UpdateCheckError(str(exc)) from exc

    assets = tuple(
        ReleaseAsset(
            name=str(item.get("name", "")),
            api_url=str(item.get("url", "")),
            download_url=str(item.get("browser_download_url", "")),
            size=int(item.get("size") or 0),
            digest=str(item.get("digest") or ""),
        )
        for item in payload.get("assets") or []
        if isinstance(item, dict)
    )
    return ReleaseInfo(
        current_version=current_version,
        latest_version=tag.lstrip("vV"),
        release_url=str(payload.get("html_url", "")),
        release_name=str(payload.get("name") or tag),
        notes=str(payload.get("body") or ""),
        published_at=str(payload.get("published_at") or ""),
        assets=assets,
    )
