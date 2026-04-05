"""Merge per-entry YAML files into a single index.json and HTML page for GitHub Pages.

Supports multiple entry types (plugins, workspaces, templates, examples) stored
in separate directories.  Each entry may optionally include a ``github`` field
(owner/repo) — when present the build fetches the repo's star count from the
GitHub API and injects it as ``stars`` into the output.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

CATEGORIES = {
    "plugins": "plugin",
    "workspaces": "workspace",
    "templates": "template",
    "examples": "example",
}

REQUIRED_FIELDS = ("name", "description", "author")

PLUGIN_REQUIRED_VERSION_FIELDS = ("version", "sciqlop", "pip")


def _fetch_stars(github_slug: str) -> int | None:
    """Fetch star count for *owner/repo* from the GitHub API.  Returns None on failure."""
    url = f"https://api.github.com/repos/{github_slug}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data.get("stargazers_count")
    except Exception as exc:
        print(f"  WARNING: could not fetch stars for {github_slug}: {exc}", file=sys.stderr)
        return None


def validate_entry(entry: dict, path: Path) -> list[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"{path.name}: missing required field '{field}'")
    entry_type = entry.get("type", "plugin")
    if entry_type == "plugin":
        for field in ("license", "versions"):
            if field not in entry:
                errors.append(f"{path.name}: missing required field '{field}'")
        for i, v in enumerate(entry.get("versions", [])):
            for field in PLUGIN_REQUIRED_VERSION_FIELDS:
                if field not in v:
                    errors.append(f"{path.name}: versions[{i}] missing '{field}'")
    return errors


def load_entries(base: Path) -> list[dict]:
    entries: list[dict] = []
    errors: list[str] = []
    for dirname, default_type in CATEGORIES.items():
        directory = base / dirname
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            entry = yaml.safe_load(path.read_text())
            entry.setdefault("type", default_type)
            errors.extend(validate_entry(entry, path))
            entries.append(entry)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    return entries


def enrich_with_stars(entries: list[dict]) -> None:
    """Fetch GitHub stars for entries that declare a ``github`` field."""
    cache: dict[str, int | None] = {}
    for entry in entries:
        slug = entry.get("github")
        if not slug:
            continue
        if slug not in cache:
            print(f"  Fetching stars for {slug}...")
            cache[slug] = _fetch_stars(slug)
        stars = cache[slug]
        if stars is not None:
            entry["stars"] = stars


def main():
    entries = load_entries(Path("."))

    enrich_with_stars(entries)

    site = Path("site")
    site.mkdir(exist_ok=True)

    (site / "index.json").write_text(json.dumps(entries, indent=2))

    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    html = env.get_template("index.html.j2").render(
        entries=entries,
        entries_json=Markup(json.dumps(entries)),
    )
    (site / "index.html").write_text(html)

    type_counts = {}
    for e in entries:
        t = e.get("type", "plugin")
        type_counts[t] = type_counts.get(t, 0) + 1
    summary = ", ".join(f"{c} {t}s" for t, c in sorted(type_counts.items()))
    print(f"Built index with {summary}")


if __name__ == "__main__":
    main()
