# SciQLop Store

The official store for [SciQLop](https://github.com/SciQLop/SciQLop) — browse and install community plugins, workspaces, templates, and examples directly from the app.

**[Browse the store](https://sciqlop.github.io/sciqlop-appstore/)**

---

## Installing from the store

Open SciQLop, go to the **Plugin Store** tab, find what you need, and click **Install**. That's it — no terminal required.

## Submitting an entry

The easiest way to add your plugin, workspace, template, or example to the store is through a GitHub issue:

- [Submit a plugin](https://github.com/SciQLop/sciqlop-appstore/issues/new?template=submit-plugin.yml)
- [Submit a workspace, template, or example](https://github.com/SciQLop/sciqlop-appstore/issues/new?template=submit-entry.yml)
- [Update an existing entry](https://github.com/SciQLop/sciqlop-appstore/issues/new?template=update-entry.yml)

Fill in the form, and a maintainer will review it. Once approved, a PR is created and merged automatically — your entry appears in the store within minutes.

## Entry types

| Type | Directory | Description |
|------|-----------|-------------|
| `plugin` | `plugins/` | Installable Python packages that extend SciQLop |
| `workspace` | `workspaces/` | Pre-configured workspaces for specific missions or workflows |
| `template` | `templates/` | Reusable plot panel templates |
| `example` | `examples/` | Tutorials and example notebooks |

---

## Writing a YAML entry by hand

If you prefer pull requests over issue forms, create a YAML file in the appropriate directory. The file name should be a slug of the entry name (e.g. `my-plugin.yaml`).

### Plugin example

```yaml
name: My Plugin
type: plugin
description: What it does
author: Your Name
license: MIT
github: owner/repo          # optional — displays GitHub star count
tags: [analysis, mms]

versions:
  - version: "0.1.0"
    sciqlop: ">=0.10"
    pip: my-sciqlop-plugin==0.1.0
```

The `pip` field accepts a PyPI package specifier (`my-plugin==0.1.0`) or a direct URL to a wheel.

### Non-plugin example

```yaml
name: MMS Reconnection Events
type: example
description: Catalog of magnetic reconnection events observed by MMS
author: Community
tags: [mms, reconnection, catalog]
url: https://github.com/.../mms-reconnection-example.zip
```

### Field reference

**Common fields (all types):**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Display name |
| `type` | yes | `plugin`, `workspace`, `template`, or `example` |
| `description` | yes | One-line description |
| `author` | yes | Author name or team |
| `tags` | no | List of tags for filtering |
| `github` | no | `owner/repo` — star count is fetched at build time |
| `image` | no | Absolute `https://` URL to a card thumbnail |
| `screenshots` | no | List of absolute `https://` URLs shown in a carousel |

**Plugin-specific fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `license` | yes | SPDX license identifier |
| `versions` | yes | List of version entries (see below) |

**Version entries (plugins only):**

| Field | Required | Description |
|-------|----------|-------------|
| `version` | yes | Plugin version (semver) |
| `sciqlop` | yes | Compatible SciQLop version range (PEP 440) |
| `pip` | yes | pip specifier, PyPI package, or direct wheel URL |

**Non-plugin fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `url` | yes | Download URL |

---

## Plugin images

Entries may include a card thumbnail and screenshots. Both are **optional** and
backwards compatible — older SciQLop versions ignore them.

- `image` — a single absolute `https://` URL used as the card thumbnail.
- `screenshots` — a list of absolute `https://` URLs shown in a carousel.

URLs **must be absolute** (`https://…`). Relative paths fail to load in the in-app
store, and the build rejects them.

### Hosting (recommended: in this repo)

Commit images under `assets/<slug>/` and reference them by their GitHub Pages URL,
so they are versioned alongside the registry:

```
assets/
  <slug>/
    card.png        # card thumbnail
    01.png 02.png   # screenshots, in display order
```

`<slug>` is your entry's YAML filename stem (e.g. `sciqlop-radio.yaml` →
`sciqlop-radio`). Reference them as:

```yaml
image: https://sciqlop.github.io/sciqlop-appstore/assets/<slug>/card.png
screenshots:
  - https://sciqlop.github.io/sciqlop-appstore/assets/<slug>/01.png
  - https://sciqlop.github.io/sciqlop-appstore/assets/<slug>/02.png
```

The build verifies that any `assets/…` Pages URL has a matching committed file. You
may also point `image`/`screenshots` at any external absolute URL.

### Image guidelines

- **Formats:** PNG or WebP preferred; JPEG acceptable. No SVG for screenshots.
- **Card thumbnail:** landscape ~16:10, target ~800×500 (rendered cropped to a
  full-width 100 px cover on the card).
- **Screenshots:** landscape ~16:9, 1280×720–1920×1080.
- **File size:** keep each under ~300 KB.
- **Count:** up to ~5 screenshots.
- **Content:** real SciQLop UI showing the plugin in use, not logos or banners.

---

## Hosting your own store

SciQLop supports multiple store URLs. Any repository following this structure works as an independent store:

1. **Fork or copy this repo** as a starting point.

2. **Add YAML entries** in `plugins/`, `workspaces/`, `templates/`, and/or `examples/`.

3. **Build the index** — the build script merges all YAMLs into `site/index.json` and an HTML browsing page:

   ```bash
   pip install pyyaml jinja2 markupsafe
   python build_index.py
   ```

   If you set a `GITHUB_TOKEN` environment variable, the build fetches GitHub star counts for entries with a `github` field.

4. **Deploy `site/`** to GitHub Pages (or any static host). The included CI workflow (`.github/workflows/publish.yml`) does this automatically on push to `main`.

5. **Point SciQLop at your store** by adding your `index.json` URL to the store URL list in SciQLop's settings.

### Build output

| File | Purpose |
|------|---------|
| `site/index.json` | Machine-readable index consumed by SciQLop |
| `site/index.html` | Human-browsable catalog page |

---

## Development

```bash
# Build locally
pip install pyyaml jinja2 markupsafe
python build_index.py

# Serve locally
cd site && python -m http.server 8765
```

The `examples/` directory contains a CI template (`bundle-ci.yml`) for plugin bundle repos that build and release wheels automatically on tag push.
