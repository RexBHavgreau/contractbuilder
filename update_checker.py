"""Check GitHub Releases for a newer application version.

No credentials are embedded in the application. Public repositories work
without configuration. For a private repository, users may supply a
read-only token through CONTRACTBUILDER_GITHUB_TOKEN or GH_TOKEN.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class UpdateCheckError(Exception):
    """A readable failure while checking the release endpoint."""


@dataclass(frozen=True)
class ReleaseInfo:
    current_version: str
    latest_version: str
    release_url: str
    release_name: str
    notes: str
    published_at: str

    @property
    def available(self) -> bool:
        return version_key(self.latest_version) > version_key(self.current_version)


def version_key(value: str) -> tuple[int, ...]:
    """Convert a v-prefixed or plain dotted version to comparable integers."""
    match = re.search(r"\d+(?:\.\d+)*", str(value))
    if not match:
        raise ValueError(f"Unrecognized version: {value!r}")
    parts = [int(part) for part in match.group(0).split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def check_for_update(
    current_version: str,
    repository: str,
    timeout: float = 5.0,
) -> ReleaseInfo:
    """Retrieve the latest published GitHub release and compare its tag."""
    token = (
        os.environ.get("CONTRACTBUILDER_GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    )
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
            raise UpdateCheckError(
                "GitHub returned 404. No published release may exist yet, "
                "or this repository is private. For a private repository, "
                "set CONTRACTBUILDER_GITHUB_TOKEN to a GitHub token with "
                "read-only Contents access to this repository."
            ) from exc
        if exc.code in (401, 403):
            raise UpdateCheckError(
                "GitHub denied the update check. Check the token permissions "
                "and any GitHub API rate limit."
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

    return ReleaseInfo(
        current_version=current_version,
        latest_version=tag.lstrip("vV"),
        release_url=str(payload.get("html_url", "")),
        release_name=str(payload.get("name") or tag),
        notes=str(payload.get("body") or ""),
        published_at=str(payload.get("published_at") or ""),
    )
