"""Cut a plugin release from the CHANGELOG's `## Unreleased` section.

    dev/harness release            bump inferred from the entries (Breaking > New > rest)
    dev/harness release minor      force the bump type

Moves the Unreleased entries under a new version heading, writes the version to
plugin.json (users only receive updates when it changes), commits, and tags
`v<version>` locally. Pushing stays a manual step.
"""

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "plugin" / "CHANGELOG.md"
MANIFEST = ROOT / "plugin" / ".claude-plugin" / "plugin.json"
UNRELEASED = "## Unreleased\n"


def unreleased_entries(text):
    """Return the body of the Unreleased section (without its heading)."""
    start = text.index(UNRELEASED) + len(UNRELEASED)
    end = text.find("\n## ", start)
    return text[start:end if end != -1 else len(text)].strip()


def released_version(text):
    """Return the newest version heading in the changelog."""
    match = re.search(r"^## (\d+\.\d+\.\d+) ", text, re.MULTILINE)
    return match.group(1) if match else None


def bump(version, kind):
    major, minor, patch = (int(part) for part in version.split("."))
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def inferred_kind(entries):
    if "### Breaking" in entries:
        return "major"
    if "### New" in entries:
        return "minor"
    return "patch"


def main():
    text = CHANGELOG.read_text(encoding="utf-8")
    entries = unreleased_entries(text)
    if not entries:
        print("Nothing to release: `## Unreleased` is empty.")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    kind = sys.argv[1] if len(sys.argv) > 1 else inferred_kind(entries)
    if kind not in ("major", "minor", "patch"):
        print("Bump type must be major, minor, or patch.")
        return 2
    version = bump(manifest["version"], kind)

    start = text.index(UNRELEASED) + len(UNRELEASED)
    end = text.find("\n## ", start)
    rest = text[end:] if end != -1 else ""
    CHANGELOG.write_text(
        text[:start] + f"\n## {version} — {date.today().isoformat()}\n\n{entries}\n" + rest, encoding="utf-8"
    )
    manifest["version"] = version
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    subprocess.check_call(["git", "add", str(CHANGELOG), str(MANIFEST)], cwd=str(ROOT))
    subprocess.check_call(["git", "commit", "-qm", f"release: v{version}"], cwd=str(ROOT))
    subprocess.check_call(["git", "tag", f"v{version}"], cwd=str(ROOT))
    print(f"Released v{version} ({kind}). Publish with: git push && git push origin v{version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
