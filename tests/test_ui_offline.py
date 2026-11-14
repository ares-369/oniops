"""The web UI loads nothing from the internet: fonts, icons and scripts are served by OniOps itself."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_ui_loads_nothing_from_outside():
    for p in [*(ROOT / "templates").glob("*.html"), ROOT / "static/mdi/css/icons.css"]:
        text = p.read_text(encoding="utf-8")
        assert not re.search(r"<(link|script|img)\b[^>]*(src|href)\s*=\s*[\"']https?://", text), p
        assert not re.search(r"url\(\s*[\"']?https?://", text), p
        assert not re.search(r"@import\s+[\"']?https?://", text), p
