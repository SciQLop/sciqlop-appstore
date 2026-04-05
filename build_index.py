"""Merge per-plugin YAML files into a single index.json and HTML page for GitHub Pages."""

import json
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup


def validate_plugin(plugin: dict, path: Path) -> list[str]:
    errors = []
    for field in ("name", "description", "author", "license", "versions"):
        if field not in plugin:
            errors.append(f"{path.name}: missing required field '{field}'")
    for i, v in enumerate(plugin.get("versions", [])):
        for field in ("version", "sciqlop"):
            if field not in v:
                errors.append(f"{path.name}: versions[{i}] missing '{field}'")
        if "pip" not in v:
            errors.append(f"{path.name}: versions[{i}] missing 'pip'")
    return errors


def load_plugins(plugins_dir: Path) -> list[dict]:
    plugins = []
    errors = []
    for path in sorted(plugins_dir.glob("*.yaml")):
        plugin = yaml.safe_load(path.read_text())
        errors.extend(validate_plugin(plugin, path))
        plugins.append(plugin)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    return plugins


def main():
    plugins = load_plugins(Path("plugins"))

    site = Path("site")
    site.mkdir(exist_ok=True)

    (site / "index.json").write_text(json.dumps(plugins, indent=2))

    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    html = env.get_template("index.html.j2").render(
        plugins=plugins,
        plugins_json=Markup(json.dumps(plugins)),
    )
    (site / "index.html").write_text(html)

    print(f"Built index.json + index.html with {len(plugins)} plugins")


if __name__ == "__main__":
    main()
