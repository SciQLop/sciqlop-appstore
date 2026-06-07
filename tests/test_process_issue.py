import importlib.util
from pathlib import Path

import yaml

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


def test_handle_submit_maps_image_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fields = {
        "Plugin name": "My Plugin",
        "Description": "d",
        "Author": "a",
        "License": "MIT",
        "Tags": "x, y",
        "Version": "0.1.0",
        "SciQLop compatibility": ">=0.12",
        "pip install target": "my-plugin==0.1.0",
        "Card image URL": "https://example.com/card.png",
        "Screenshot URLs": "https://example.com/01.png\nhttps://example.com/02.png",
    }
    process_issue.handle_submit(fields, ["submit", "plugin"])
    entry = yaml.safe_load((tmp_path / "plugins" / "my-plugin.yaml").read_text())
    assert entry["image"] == "https://example.com/card.png"
    assert entry["screenshots"] == [
        "https://example.com/01.png",
        "https://example.com/02.png",
    ]


def test_handle_submit_omits_absent_image_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fields = {
        "Plugin name": "No Images",
        "Description": "d",
        "Author": "a",
        "License": "MIT",
        "Tags": "x",
        "Version": "0.1.0",
        "SciQLop compatibility": ">=0.12",
        "pip install target": "no-images==0.1.0",
    }
    process_issue.handle_submit(fields, ["submit", "plugin"])
    entry = yaml.safe_load((tmp_path / "plugins" / "no-images.yaml").read_text())
    assert "image" not in entry
    assert "screenshots" not in entry


def test_handle_update_maps_image_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "existing.yaml").write_text(
        "name: Existing\ntype: plugin\nversions: []\n"
    )
    fields = {
        "Entry name": "Existing",
        "What to update": "add images",
        "Card image URL": "https://example.com/card.png",
        "Screenshot URLs": "https://example.com/01.png",
    }
    process_issue.handle_update(fields)
    entry = yaml.safe_load((tmp_path / "plugins" / "existing.yaml").read_text())
    assert entry["image"] == "https://example.com/card.png"
    assert entry["screenshots"] == ["https://example.com/01.png"]
