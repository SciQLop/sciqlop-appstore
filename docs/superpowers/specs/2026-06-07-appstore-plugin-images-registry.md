# Spec: Plugin images in the SciQLop appstore registry

**Date:** 2026-06-07
**Repo:** `sciqlop-appstore` (published to https://sciqlop.github.io/sciqlop-appstore/)
**Companion handoff:** `../SciQLop/docs/appstore-plugin-images-registry-handoff.md`
**Client design (consumer):** SciQLop-side `docs/superpowers/specs/2026-06-07-appstore-plugin-images-design.md`

## Goal

Let store entries carry a card thumbnail and a set of screenshots, surfaced both in
the in-app SciQLop Plugin Store and on the public Pages catalog. Backwards
compatible: entries without the fields render exactly as today.

## Schema

Two new **optional** fields on any entry (plugin or non-plugin):

| Field         | Type            | Meaning                              |
|---------------|-----------------|--------------------------------------|
| `image`       | string (URL)    | card thumbnail                       |
| `screenshots` | list of strings | gallery, in display order            |

Both are **absolute** `http(s)://…` URLs. Relative paths are rejected: the SciQLop
client renders the store via `setHtml(html, base_url)` with a `file://` base, so a
relative `assets/…` path would resolve against the local filesystem and fail.

Client resolution rules (the registry mirrors these on the web page):
- **Card thumbnail** = `image` → else `screenshots[0]` → else placeholder/none.
- **Gallery** = `screenshots` → else `[image]` if only `image` is set → else none.

Pass-through to `index.json` already works today — `build_index.py` loads each YAML
and appends the whole dict — so no transport code is required. The work is
validation plus the surrounding tooling and docs.

## Components

### 1. `build_index.py` — hard-fail validation

Fold an image check into `validate_entry` so failures join the existing `errors`
list and trigger `sys.exit(1)`. A new helper `validate_images(entry, path) -> list[str]`:

- If `image` present: must be a `str` starting with `http://` or `https://`.
- If `screenshots` present: must be a `list`; every element a `str` starting with
  `http://` or `https://`.
- **In-repo file check:** for any URL beginning with
  `https://sciqlop.github.io/sciqlop-appstore/assets/`, strip that prefix and assert
  the remaining path exists under the repo's `assets/` directory. Catches typos in
  self-hosted image references. External URLs are accepted without a reachability
  check.

The build does not download or size-check external images.

### 2. Hosting convention (advocate in-repo, allow external)

Recommended: host images in this repo under `assets/<slug>/` and serve from Pages.

```
assets/
  <slug>/
    card.png        # card thumbnail
    01.png 02.png   # screenshots, in display order
```

`<slug>` = the entry's YAML filename stem (e.g. `sciqlop-radio.yaml` → `sciqlop-radio`).
Referenced as absolute Pages URLs:

```
https://sciqlop.github.io/sciqlop-appstore/assets/<slug>/card.png
```

Authors may instead point `image`/`screenshots` at any absolute external URL (e.g.
their own repo's raw content). The in-repo file check only applies to URLs under the
Pages `assets/` prefix.

### 3. Issue forms

Add two optional inputs, with image guidelines as help text, to:
- `.github/ISSUE_TEMPLATE/submit-plugin.yml`
- `.github/ISSUE_TEMPLATE/submit-entry.yml`
- `.github/ISSUE_TEMPLATE/update-entry.yml`

| Form control | Label              | Maps to       |
|--------------|--------------------|---------------|
| input        | `Card image URL`   | `image`       |
| textarea     | `Screenshot URLs`  | `screenshots` (one URL per line) |

### 4. `.github/scripts/process_issue.py`

- `handle_submit`: read `Card image URL` → `entry["image"]` (only if non-empty);
  read `Screenshot URLs` → `entry["screenshots"]` as a list (split on newlines,
  strip, drop blanks; only set if non-empty).
- `handle_update`: same — if provided, set/replace `image` and/or `screenshots` on
  the loaded entry. Existing version-append behavior is unchanged.
- A small shared helper parses the screenshots textarea into a clean list.

### 5. `templates/index.html.j2` — thumbnail + lightbox

Mirror the app on the public page:

- **Card cover:** when a card has `image` (else `screenshots[0]`), render a
  full-width cover `<img>` ~100 px tall at the top of the card. A failed image load
  removes the cover (emoji/none fallback), matching the client.
- **Lightbox carousel:** a single hidden modal overlay added to the page body.
  Cards that have a gallery (`screenshots`, else `[image]`) become clickable and
  open the modal at slide 0. The modal shows the current screenshot full-size with:
  - **‹ / ›** previous / next controls,
  - a counter (`2 / 4`),
  - close on **✕**, click-outside, or **Esc**; ←/→ keys navigate.
  Implemented in vanilla JS/CSS inside the existing template — no new dependencies.

### 6. README

- Add `image` and `screenshots` to the common-field reference table.
- Add a "Plugin images" section documenting the hosting convention and the
  guidelines: PNG/WebP preferred (JPEG ok, no SVG for screenshots); card ~16:10
  ~800×500; screenshots ~16:9 (1280×720–1920×1080); keep each under ~300 KB; up to
  ~5 screenshots; show real SciQLop UI, not logos/banners.

(There is no CONTRIBUTING file; README is the canonical contributor doc.)

### 7. Placeholder example (end-to-end proof)

Attach images to `plugins/sciqlop-radio.yaml`:
- Commit generated placeholder PNGs at `assets/sciqlop-radio/card.png` and
  `assets/sciqlop-radio/01.png` (dependency-free generation; small solid-color PNGs
  with a label are fine).
- Add `image:` and `screenshots:` pointing at the Pages URLs.

This exercises: the in-repo file-exists check, JSON pass-through, the card cover,
and the lightbox.

## Testing

The repo currently has no tests. Add a minimal `pytest` module
(`tests/test_build_index.py` or similar) covering `validate_entry`'s image rules:

- valid `image` + `screenshots` (external URLs) → no errors;
- non-string `image` → error;
- relative / non-`http(s)` URL → error;
- in-repo Pages `assets/` URL with a missing file → error;
- in-repo Pages `assets/` URL with an existing file (the placeholder) → no error.

Plus a manual `python build_index.py` run confirming the example builds clean and
`site/index.json` carries the new fields.

## Out of scope

- Downloading or size/format-validating external images at build time.
- Any change to existing fields or their types (would break client compatibility).
- Image optimization/compression tooling.

## Compatibility

`image`/`screenshots` are additive and optional. Older SciQLop clients ignore
unknown keys; newer clients fall back gracefully when the fields are absent. The
only breaking changes would be altering or removing an existing field — explicitly
out of scope.
