"""Parse a GitHub issue form body and create/update a store YAML entry.

Issue form bodies use a predictable format:
    ### Field label\n\nvalue\n\n### Next label\n\n...

Sets BRANCH_NAME and COMMIT_MSG env vars for the calling workflow.
"""

import json
import os
import re
from pathlib import Path

import yaml

CATEGORY_DIRS = {
    "plugin": "plugins",
    "workspace": "workspaces",
    "template": "templates",
    "example": "examples",
}


def parse_issue_body(body: str) -> dict[str, str]:
    """Extract field→value pairs from a GitHub issue form body."""
    sections = re.split(r"^### +", body, flags=re.MULTILINE)
    fields = {}
    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().split("\n", 1)
        label = lines[0].strip()
        value = lines[1].strip() if len(lines) > 1 else ""
        if value == "_No response_":
            value = ""
        fields[label] = value
    return fields


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def set_env(key: str, value: str) -> None:
    env_file = os.environ.get("GITHUB_ENV")
    if env_file:
        with open(env_file, "a") as f:
            f.write(f"{key}={value}\n")
    os.environ[key] = value


def handle_submit(fields: dict[str, str], labels: list[str]) -> None:
    is_plugin = "plugin" in labels
    entry_type = "plugin" if is_plugin else fields.get("Entry type", "plugin").lower()

    name = fields.get("Plugin name") or fields.get("Name", "")
    if not name:
        raise ValueError("Missing name")

    tags_raw = fields.get("Tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    entry: dict = {"name": name, "type": entry_type}
    entry["description"] = fields.get("Description", "")
    entry["author"] = fields.get("Author", "")

    license_val = fields.get("License", "")
    if license_val:
        entry["license"] = license_val

    github = fields.get("GitHub repository", "")
    if github:
        entry["github"] = github

    entry["tags"] = tags

    if is_plugin:
        version_entry = {
            "version": fields.get("Version", "0.1.0"),
            "sciqlop": fields.get("SciQLop compatibility", ">=0.10"),
            "pip": fields.get("pip install target", ""),
        }
        entry["versions"] = [version_entry]

    url = fields.get("Download URL", "")
    if url and not is_plugin:
        entry["url"] = url

    slug = slugify(name)
    directory = CATEGORY_DIRS.get(entry_type, "plugins")
    out_dir = Path(directory)
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{slug}.yaml"

    out_path.write_text(yaml.dump(entry, default_flow_style=False, sort_keys=False))

    issue_number = os.environ.get("ISSUE_NUMBER", "0")
    set_env("BRANCH_NAME", f"submit/{slug}-{issue_number}")
    set_env("COMMIT_MSG", f"Add {entry_type}: {name}")


def handle_update(fields: dict[str, str]) -> None:
    name = fields.get("Entry name", "")
    if not name:
        raise ValueError("Missing entry name")

    slug = slugify(name)
    found = None
    for directory in CATEGORY_DIRS.values():
        candidate = Path(directory) / f"{slug}.yaml"
        if candidate.exists():
            found = candidate
            break

    if not found:
        raise FileNotFoundError(f"No entry found for '{name}' (tried {slug}.yaml)")

    entry = yaml.safe_load(found.read_text())

    version = fields.get("New version (if adding a release)", "")
    if version:
        new_version = {
            "version": version,
            "sciqlop": fields.get("SciQLop compatibility", ">=0.10"),
            "pip": fields.get("pip install target", ""),
        }
        entry.setdefault("versions", []).append(new_version)

    found.write_text(yaml.dump(entry, default_flow_style=False, sort_keys=False))

    issue_number = os.environ.get("ISSUE_NUMBER", "0")
    set_env("BRANCH_NAME", f"update/{slug}-{issue_number}")
    msg = f"Update {name}: add v{version}" if version else f"Update {name}"
    set_env("COMMIT_MSG", msg)


def main() -> None:
    body = os.environ.get("ISSUE_BODY", "")
    labels = json.loads(os.environ.get("ISSUE_LABELS", "[]"))

    fields = parse_issue_body(body)

    if "update" in labels:
        handle_update(fields)
    elif "submit" in labels:
        handle_submit(fields, labels)
    else:
        print("No actionable labels found, skipping.")
        return


if __name__ == "__main__":
    main()
