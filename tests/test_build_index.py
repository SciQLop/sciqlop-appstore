import json
import zipfile
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
    # type="example" avoids plugin-only required-field errors, isolating image checks
    entry = _entry(type="example", image=123)
    errors = build_index.validate_entry(entry, Path("x.yaml"), tmp_path)
    assert any("image" in e for e in errors)


def _wheel(tmp_path, manifest):
    path = tmp_path / "demo-1.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("demo/__init__.py", "")
        if manifest is not None:
            wheel.writestr("demo/plugin.json", json.dumps(manifest))
    return path.as_uri()


def test_wheel_provides_reads_the_plugin_manifest(tmp_path):
    url = _wheel(tmp_path, {"name": "demo", "provides": {"sciqlop.panel_kinds": ["demo.viewer"]}})
    assert build_index.wheel_provides(url) == {"sciqlop.panel_kinds": ["demo.viewer"]}


def test_a_wheel_without_manifest_or_provides_provides_nothing(tmp_path):
    assert build_index.wheel_provides(_wheel(tmp_path, None)) == {}
    assert build_index.wheel_provides(_wheel(tmp_path, {"name": "demo"})) == {}


def test_an_unreadable_wheel_gives_none(tmp_path):
    assert build_index.wheel_provides((tmp_path / "missing.whl").as_uri()) is None


def test_enrich_copies_provides_into_wheel_versions_only():
    entries = [
        _entry(versions=[{"version": "1", "pip": "https://x/demo-1-py3-none-any.whl"},
                         {"version": "2", "pip": "demo==2"},
                         {"version": "3", "pip": "https://x/demo-3-py3-none-any.whl",
                          "provides": {"sciqlop.panel_kinds": ["kept"]}}]),
        _entry(type="workspace", versions=[{"version": "1", "pip": "https://x/w-1-py3-none-any.whl"}]),
    ]
    read = []

    def fake(url):
        read.append(url)
        return {"sciqlop.panel_kinds": ["demo.viewer"]}

    build_index.enrich_with_provides(entries, read=fake)
    versions = entries[0]["versions"]
    assert versions[0]["provides"] == {"sciqlop.panel_kinds": ["demo.viewer"]}
    assert "provides" not in versions[1]
    assert versions[2]["provides"] == {"sciqlop.panel_kinds": ["kept"]}
    assert read == ["https://x/demo-1-py3-none-any.whl"]


def test_enrich_leaves_out_empty_or_unreadable_provides():
    entries = [_entry(versions=[{"version": "1", "pip": "https://x/a.whl"},
                                {"version": "2", "pip": "https://x/b.whl"}])]
    build_index.enrich_with_provides(entries, read=lambda url: {} if url.endswith("a.whl") else None)
    assert all("provides" not in v for v in entries[0]["versions"])
