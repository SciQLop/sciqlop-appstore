# Plugin Images in the Appstore Registry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let store entries carry an `image` (card thumbnail) and `screenshots` (gallery), validated at build time, surfaced on the public Pages catalog, and submittable via issue forms — backwards compatible.

**Architecture:** Two optional URL fields flow through the existing YAML → `build_index.py` → `index.json` pipeline (pass-through already works). We add hard-fail validation, render a card cover + lightbox carousel in the HTML template, extend the issue forms and their parser, document the hosting convention, and prove it end-to-end with a placeholder example on `sciqlop-radio`.

**Tech Stack:** Python 3.12+ (PyYAML, Jinja2, markupsafe, Pillow for placeholder images), pytest, vanilla JS/CSS, GitHub issue-form YAML.

---

## File Structure

- `build_index.py` — add `validate_images` + in-repo asset check; thread a `root` arg through `validate_entry`. (Modify)
- `tests/test_build_index.py` — new pytest module for validation rules. (Create)
- `tests/test_process_issue.py` — new pytest module for the screenshots parser. (Create)
- `.github/scripts/process_issue.py` — parse `Card image URL` / `Screenshot URLs` into `image`/`screenshots`. (Modify)
- `.github/ISSUE_TEMPLATE/submit-plugin.yml`, `submit-entry.yml`, `update-entry.yml` — add the two optional inputs. (Modify)
- `templates/index.html.j2` — card cover image + lightbox carousel. (Modify)
- `README.md` — field reference + "Plugin images" section. (Modify)
- `assets/sciqlop-radio/card.png`, `assets/sciqlop-radio/01.png` — committed placeholder images. (Create)
- `plugins/sciqlop-radio.yaml` — add `image` + `screenshots`. (Modify)

`tests/` are import-based and run from the repo root (`python -m pytest`). `build_index.py` is imported directly by tests (it's a top-level module).

---

## Task 1: Build-time image validation (hard-fail)

**Files:**
- Modify: `build_index.py`
- Create: `tests/test_build_index.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_build_index.py`:

```python
from pathlib import Path

import build_index


def _entry(**kw):
    base = {"name": "X", "description": "d", "author": "a"}
    base.update(kw)
    return base


def test_no_image_fields_pass(tmp_path):
    assert build_index.validate_images(_entry(), Path("x.yaml"), tmp_path) == []


def test_valid_external_images_pass(tmp_path):
    entry = _entry(
        image="https://example.com/c.png",
        screenshots=["https://example.com/1.png", "https://example.com/2.png"],
    )
    assert build_index.validate_images(entry, Path("x.yaml"), tmp_path) == []


def test_non_string_image_fails(tmp_path):
    errors = build_index.validate_images(_entry(image=123), Path("x.yaml"), tmp_path)
    assert any("image" in e for e in errors)


def test_relative_image_url_fails(tmp_path):
    errors = build_index.validate_images(
        _entry(image="assets/c.png"), Path("x.yaml"), tmp_path
    )
    assert any("image" in e for e in errors)


def test_screenshots_must_be_list(tmp_path):
    errors = build_index.validate_images(
        _entry(screenshots="https://example.com/1.png"), Path("x.yaml"), tmp_path
    )
    assert any("screenshots" in e for e in errors)


def test_screenshot_element_must_be_abs_url(tmp_path):
    errors = build_index.validate_images(
        _entry(screenshots=["assets/1.png"]), Path("x.yaml"), tmp_path
    )
    assert any("screenshots[0]" in e for e in errors)


def test_in_repo_missing_file_fails(tmp_path):
    url = "https://sciqlop.github.io/sciqlop-appstore/assets/foo/card.png"
    errors = build_index.validate_images(_entry(image=url), Path("x.yaml"), tmp_path)
    assert any("does not exist" in e for e in errors)


def test_in_repo_existing_file_passes(tmp_path):
    asset = tmp_path / "assets" / "foo" / "card.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"x")
    url = "https://sciqlop.github.io/sciqlop-appstore/assets/foo/card.png"
    assert build_index.validate_images(_entry(image=url), Path("x.yaml"), tmp_path) == []


def test_validate_entry_includes_image_errors(tmp_path):
    entry = _entry(type="example", image=123)
    errors = build_index.validate_entry(entry, Path("x.yaml"), tmp_path)
    assert any("image" in e for e in errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_build_index.py -v`
Expected: FAIL — `AttributeError: module 'build_index' has no attribute 'validate_images'` (and `validate_entry` takes 2 args, not 3).

- [ ] **Step 3: Implement the validation in `build_index.py`**

Add this constant near the top (after `PLUGIN_REQUIRED_VERSION_FIELDS`):

```python
ASSETS_URL_PREFIX = "https://sciqlop.github.io/sciqlop-appstore/assets/"
```

Add these helpers above `validate_entry`:

```python
def _is_abs_url(value) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _check_in_repo_asset(url: str, path: Path, root: Path) -> list[str]:
    """If *url* points at this repo's Pages assets, assert the local file exists."""
    if not url.startswith(ASSETS_URL_PREFIX):
        return []
    rel = url[len(ASSETS_URL_PREFIX):]
    asset_path = root / "assets" / rel
    if not asset_path.is_file():
        return [f"{path.name}: image URL '{url}' but {asset_path} does not exist"]
    return []


def validate_images(entry: dict, path: Path, root: Path) -> list[str]:
    errors: list[str] = []
    image = entry.get("image")
    if image is not None:
        if not _is_abs_url(image):
            errors.append(f"{path.name}: 'image' must be an absolute http(s) URL string")
        else:
            errors.extend(_check_in_repo_asset(image, path, root))
    screenshots = entry.get("screenshots")
    if screenshots is not None:
        if not isinstance(screenshots, list):
            errors.append(
                f"{path.name}: 'screenshots' must be a list of absolute http(s) URL strings"
            )
        else:
            for i, shot in enumerate(screenshots):
                if not _is_abs_url(shot):
                    errors.append(
                        f"{path.name}: screenshots[{i}] must be an absolute http(s) URL string"
                    )
                else:
                    errors.extend(_check_in_repo_asset(shot, path, root))
    return errors
```

Change `validate_entry` to accept `root` and call `validate_images`. Replace the
existing `def validate_entry(entry: dict, path: Path) -> list[str]:` signature line
with:

```python
def validate_entry(entry: dict, path: Path, root: Path) -> list[str]:
```

and immediately before its `return errors` line, add:

```python
    errors.extend(validate_images(entry, path, root))
```

Update the call site inside `load_entries` — replace
`errors.extend(validate_entry(entry, path))` with:

```python
            errors.extend(validate_entry(entry, path, base))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_build_index.py -v`
Expected: PASS (9 passed).

- [ ] **Step 5: Commit**

```bash
git add build_index.py tests/test_build_index.py
git commit -m "feat: validate image/screenshots fields at build time

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Issue-body parser handles image fields

**Files:**
- Modify: `.github/scripts/process_issue.py`
- Create: `tests/test_process_issue.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_process_issue.py`:

```python
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "process_issue", Path(".github/scripts/process_issue.py")
)
process_issue = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(process_issue)


def test_parse_screenshots_splits_and_strips():
    text = "https://a/1.png\n  https://a/2.png  \n\nhttps://a/3.png"
    assert process_issue.parse_screenshots(text) == [
        "https://a/1.png",
        "https://a/2.png",
        "https://a/3.png",
    ]


def test_parse_screenshots_empty_is_empty_list():
    assert process_issue.parse_screenshots("") == []
    assert process_issue.parse_screenshots("   \n  ") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_process_issue.py -v`
Expected: FAIL — `AttributeError: module 'process_issue' has no attribute 'parse_screenshots'`.

- [ ] **Step 3: Implement in `.github/scripts/process_issue.py`**

Add this helper after `slugify`:

```python
def parse_screenshots(value: str) -> list[str]:
    """One URL per line; strip blanks."""
    return [line.strip() for line in value.splitlines() if line.strip()]
```

In `handle_submit`, immediately after the line `entry["tags"] = tags`, insert:

```python
    image = fields.get("Card image URL", "")
    if image:
        entry["image"] = image
    screenshots = parse_screenshots(fields.get("Screenshot URLs", ""))
    if screenshots:
        entry["screenshots"] = screenshots
```

In `handle_update`, immediately after the line `entry = yaml.safe_load(found.read_text())`, insert:

```python
    image = fields.get("Card image URL", "")
    if image:
        entry["image"] = image
    screenshots = parse_screenshots(fields.get("Screenshot URLs", ""))
    if screenshots:
        entry["screenshots"] = screenshots
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_process_issue.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add .github/scripts/process_issue.py tests/test_process_issue.py
git commit -m "feat: parse image/screenshots from submission issue forms

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Add image inputs to the issue forms

**Files:**
- Modify: `.github/ISSUE_TEMPLATE/submit-plugin.yml`
- Modify: `.github/ISSUE_TEMPLATE/submit-entry.yml`
- Modify: `.github/ISSUE_TEMPLATE/update-entry.yml`

- [ ] **Step 1: Edit `submit-plugin.yml`**

Insert the following two blocks **after** the `github` input block (the one whose
`id: github`, ending at its `placeholder: "SciQLop/sciqlop-plugins"` line) and
**before** the `version` input block:

```yaml
  - type: input
    id: image
    attributes:
      label: Card image URL
      description: "Optional. Absolute https URL to a landscape card thumbnail (~16:10, ~800x500, PNG/WebP/JPEG, <300 KB)."
      placeholder: "https://sciqlop.github.io/sciqlop-appstore/assets/my-plugin/card.png"

  - type: textarea
    id: screenshots
    attributes:
      label: Screenshot URLs
      description: "Optional. One absolute https URL per line, up to ~5. Landscape ~16:9, <300 KB each, showing real SciQLop UI."
      placeholder: |
        https://sciqlop.github.io/sciqlop-appstore/assets/my-plugin/01.png
        https://sciqlop.github.io/sciqlop-appstore/assets/my-plugin/02.png
```

- [ ] **Step 2: Edit `submit-entry.yml`**

Insert the same two blocks (identical YAML as Step 1) **after** the `github` input
block and **before** the `url` input block.

- [ ] **Step 3: Edit `update-entry.yml`**

Append the same two blocks (identical YAML as Step 1) at the **end** of the `body:`
list, after the `pip` input block.

- [ ] **Step 4: Verify all three forms still parse as YAML**

Run:

```bash
python -c "import yaml, glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/ISSUE_TEMPLATE/*.yml')]; print('forms OK')"
```

Expected: `forms OK`

- [ ] **Step 5: Commit**

```bash
git add .github/ISSUE_TEMPLATE/
git commit -m "feat: add optional image/screenshot inputs to issue forms

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Card cover image + lightbox carousel in the HTML page

**Files:**
- Modify: `templates/index.html.j2`

- [ ] **Step 1: Add CSS**

In the `<style>` block, immediately after the `.card .versions-row code { ... }`
rule, add:

```css
  .card-thumb {
    width: calc(100% + 2.5rem);
    height: 100px;
    margin: -1.25rem -1.25rem 0.75rem -1.25rem;
    object-fit: cover;
    border-radius: 10px 10px 0 0;
    display: block;
  }

  .card.has-gallery { cursor: pointer; }

  .lightbox {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: rgba(0, 0, 0, 0.85);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .lb-img {
    max-width: 90vw;
    max-height: 85vh;
    border-radius: 8px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
  }

  .lb-close, .lb-prev, .lb-next {
    position: absolute;
    background: rgba(0, 0, 0, 0.4);
    color: #fff;
    border: none;
    cursor: pointer;
    border-radius: 8px;
    font-size: 2rem;
    line-height: 1;
    padding: 0.4rem 0.85rem;
  }

  .lb-close { top: 1rem; right: 1rem; font-size: 1.6rem; }
  .lb-prev { left: 1rem; top: 50%; transform: translateY(-50%); }
  .lb-next { right: 1rem; top: 50%; transform: translateY(-50%); }
  .lb-close:hover, .lb-prev:hover, .lb-next:hover { background: rgba(0, 0, 0, 0.7); }

  .lb-counter {
    position: absolute;
    bottom: 1rem;
    left: 50%;
    transform: translateX(-50%);
    color: var(--text-muted);
    font-size: 0.9rem;
  }
```

- [ ] **Step 2: Add the lightbox markup**

Immediately after the closing `</div>` of `<div class="container">` (the line right
before `<footer>`), insert:

```html
<div class="lightbox" id="lightbox" style="display:none">
  <button class="lb-close" id="lb-close" aria-label="Close">&times;</button>
  <button class="lb-prev" id="lb-prev" aria-label="Previous">&#8249;</button>
  <img class="lb-img" id="lb-img" src="" alt="Screenshot">
  <button class="lb-next" id="lb-next" aria-label="Next">&#8250;</button>
  <div class="lb-counter" id="lb-counter"></div>
</div>
```

- [ ] **Step 3: Render the card cover and mark gallery cards**

In the `render()` function, inside the `grid.innerHTML = filtered.map(p => { ... })`
callback, immediately after `const type = p.type || "plugin";`, add:

```javascript
    const cover = p.image || (p.screenshots && p.screenshots[0]) || "";
    const coverHtml = cover
      ? `<img class="card-thumb" src="${cover}" alt="" onerror="this.remove()">`
      : "";
    const gallery = (p.screenshots && p.screenshots.length)
      ? p.screenshots
      : (p.image ? [p.image] : []);
    const galleryAttrs = gallery.length
      ? ` has-gallery" data-gallery='${JSON.stringify(gallery)}'`
      : `"`;
```

Then change the card template's opening line. Replace:

```javascript
    return `<div class="card">
      <span class="type-badge">${type}</span>
```

with:

```javascript
    return `<div class="card${galleryAttrs}>
      ${coverHtml}
      <span class="type-badge">${type}</span>
```

(Note: `galleryAttrs` already supplies the closing quote of the `class` attribute,
so the literal becomes `class="card has-gallery" data-gallery='...'` or just
`class="card"`.)

- [ ] **Step 4: Add the lightbox JavaScript**

At the very end of the `<script>` block, immediately before `renderTags();`, add:

```javascript
const lb = document.getElementById("lightbox");
const lbImg = document.getElementById("lb-img");
const lbCounter = document.getElementById("lb-counter");
let lbGallery = [];
let lbIndex = 0;

function showSlide() {
  lbImg.src = lbGallery[lbIndex];
  lbCounter.textContent = `${lbIndex + 1} / ${lbGallery.length}`;
  const multi = lbGallery.length > 1 ? "" : "none";
  document.getElementById("lb-prev").style.display = multi;
  document.getElementById("lb-next").style.display = multi;
}

function openLightbox(gallery) {
  if (!gallery || !gallery.length) return;
  lbGallery = gallery;
  lbIndex = 0;
  showSlide();
  lb.style.display = "flex";
}

function closeLightbox() {
  lb.style.display = "none";
  lbImg.src = "";
}

function step(delta) {
  lbIndex = (lbIndex + delta + lbGallery.length) % lbGallery.length;
  showSlide();
}

document.getElementById("grid").addEventListener("click", e => {
  const card = e.target.closest(".card.has-gallery");
  if (!card) return;
  openLightbox(JSON.parse(card.dataset.gallery));
});

document.getElementById("lb-close").addEventListener("click", closeLightbox);
document.getElementById("lb-prev").addEventListener("click", e => { e.stopPropagation(); step(-1); });
document.getElementById("lb-next").addEventListener("click", e => { e.stopPropagation(); step(1); });
lb.addEventListener("click", e => { if (e.target === lb) closeLightbox(); });
document.addEventListener("keydown", e => {
  if (lb.style.display === "none") return;
  if (e.key === "Escape") closeLightbox();
  else if (e.key === "ArrowLeft") step(-1);
  else if (e.key === "ArrowRight") step(1);
});
```

- [ ] **Step 5: Build and verify the markup is emitted**

Run:

```bash
python build_index.py && grep -c 'id="lightbox"' site/index.html && grep -c 'openLightbox' site/index.html
```

Expected: build prints its summary line, then `1` and `1` (counts > 0). No traceback.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html.j2
git commit -m "feat: card thumbnails and lightbox carousel on store page

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Document image fields and hosting convention

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add fields to the common-field reference table**

In the "Common fields (all types)" table, after the `github` row, add these two rows:

```markdown
| `image` | no | Absolute `https://` URL to a card thumbnail |
| `screenshots` | no | List of absolute `https://` URLs shown in a carousel |
```

- [ ] **Step 2: Add a "Plugin images" section**

Immediately before the `## Hosting your own store` heading, insert:

```markdown
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
```

- [ ] **Step 3: Verify**

Run: `grep -c "Plugin images" README.md`
Expected: `1`

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document image/screenshots fields and hosting convention

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Placeholder example on sciqlop-radio (end-to-end proof)

**Files:**
- Create: `assets/sciqlop-radio/card.png`, `assets/sciqlop-radio/01.png`
- Modify: `plugins/sciqlop-radio.yaml`

- [ ] **Step 1: Generate the placeholder PNGs**

Run:

```bash
python - <<'PY'
from pathlib import Path
from PIL import Image, ImageDraw

out = Path("assets/sciqlop-radio")
out.mkdir(parents=True, exist_ok=True)


def make(path, size, label, color):
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), label, fill="white")
    img.save(path)


make(out / "card.png", (800, 500), "Radio Dynamic Spectra\n(card placeholder)", (28, 35, 70))
make(out / "01.png", (1280, 720), "Radio Dynamic Spectra\n(screenshot placeholder)", (20, 24, 39))
print("placeholders written:", sorted(p.name for p in out.glob("*.png")))
PY
```

Expected: `placeholders written: ['01.png', 'card.png']`

- [ ] **Step 2: Add the image fields to `plugins/sciqlop-radio.yaml`**

Insert these lines immediately after the `tags:` list (the line `- heliophysics`)
and before `versions:`:

```yaml
image: https://sciqlop.github.io/sciqlop-appstore/assets/sciqlop-radio/card.png
screenshots:
- https://sciqlop.github.io/sciqlop-appstore/assets/sciqlop-radio/01.png
```

- [ ] **Step 3: Build and verify end-to-end**

Run:

```bash
python build_index.py && python -c "import json; e=[x for x in json.load(open('site/index.json')) if x['name']=='Radio Dynamic Spectra'][0]; print('image:', e['image']); print('screenshots:', e['screenshots'])"
```

Expected: build prints its summary line (no validation error — the in-repo asset
check passes because the files exist), then the `image:` and `screenshots:` values.

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: PASS (all tests from Tasks 1–2).

- [ ] **Step 5: Commit**

```bash
git add assets/sciqlop-radio/ plugins/sciqlop-radio.yaml
git commit -m "feat: add placeholder images to sciqlop-radio entry

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] `python -m pytest tests/ -v` — all pass.
- [ ] `python build_index.py` — exits 0, no validation errors.
- [ ] `grep -c 'id="lightbox"' site/index.html` — returns `1`.
- [ ] `cd site && python -m http.server 8765` — open http://localhost:8765, confirm
      the Radio Dynamic Spectra card shows a cover image and clicking it opens the
      lightbox with prev/next + counter, closing on ✕/Esc/click-outside.
