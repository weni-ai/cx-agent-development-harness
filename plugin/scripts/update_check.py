"""Tell the user when a newer `weni` plugin version is published.

Claude Code does not announce plugin updates from third-party marketplaces, so the
session-start hook (check_ready.py --hook) asks this module. It reads where the
`weni-ai` marketplace installs from (~/.claude/plugins/known_marketplaces.json:
GitHub URL + ref), fetches that ref's plugin.json, and compares versions. It checks
at most once a day per project (cached in `.harness/update_check.json`), with a short
timeout, and never raises.

Silent when the plugin is not installed from the marketplace (e.g. `--plugin-dir`),
offline, or when updates are disabled (DISABLE_UPDATES, DISABLE_AUTOUPDATER,
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC).
"""

from __future__ import annotations

# Standard library
import json
import os
import re
import time
import urllib.request
from pathlib import Path

# Local
from _common import project_root

MARKETPLACE = "weni-ai"
PLUGIN_JSON = Path(__file__).resolve().parents[1] / ".claude-plugin" / "plugin.json"
REMOTE_PATH = "plugin/.claude-plugin/plugin.json"
CHECK_EVERY_SECONDS = 24 * 3600
TIMEOUT_SECONDS = 3
DISABLING_ENV = ("DISABLE_UPDATES", "DISABLE_AUTOUPDATER", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")
GITHUB = re.compile(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$")


def parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def installed_version() -> str:
    return json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]


def remote_url() -> str | None:
    """Return the raw plugin.json URL of the ref the marketplace installs from."""
    known = Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
    source = (json.loads(known.read_text(encoding="utf-8")).get(MARKETPLACE) or {}).get("source") or {}
    match = GITHUB.search(source.get("url") or "")
    if not match:
        return None
    owner, repo = match.groups()
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{source.get('ref') or 'HEAD'}/{REMOTE_PATH}"


def fetch_version(url: str) -> str:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))["version"]


def latest_version() -> str | None:
    """Return the published version, from the daily cache or the network."""
    cache = project_root() / ".harness" / "update_check.json"
    try:
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if time.time() - cached["checked_at"] < CHECK_EVERY_SECONDS:
            return cached["latest"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    url = remote_url()
    if not url:
        return None
    latest = fetch_version(url)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"checked_at": time.time(), "latest": latest}), encoding="utf-8")
    return latest


def update_notice() -> str:
    """Return a one-line notice when a newer version is published, else ''."""
    if any(os.environ.get(name) for name in DISABLING_ENV):
        return ""
    try:
        current, latest = installed_version(), latest_version()
        if latest and parse_version(latest) > parse_version(current):
            return (f"weni {latest} is available (you have {current}). Update: /plugin → Marketplaces → "
                    f"{MARKETPLACE} → Update marketplace, then /reload-plugins.")
    except Exception:  # never break session start over an update check
        pass
    return ""
