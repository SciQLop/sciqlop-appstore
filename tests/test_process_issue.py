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
