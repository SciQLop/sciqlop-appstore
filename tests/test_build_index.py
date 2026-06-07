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
