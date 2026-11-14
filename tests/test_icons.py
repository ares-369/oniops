"""The UI ships a subset of the icon font: every icon it names must be in the subset."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "static/mdi/css/icons.css"


def test_every_used_icon_is_in_the_subset():
    html = "".join((ROOT / "templates" / n).read_text(encoding="utf-8") for n in ("index.html", "login.html"))
    named = set(re.findall(r"mdi-([a-z0-9-]+)", html)) - {"set"}
    have = set(re.findall(r"\.mdi-([a-z0-9-]+)::before", CSS.read_text()))
    missing = sorted(named - have)
    assert not missing, f"icons missing from the subset, run scripts/build_icons.py: {missing}"


def test_font_is_small():
    fonts = list((ROOT / "static/mdi/fonts").iterdir())
    assert [f.name for f in fonts] == ["icons.woff2"]
    assert fonts[0].stat().st_size < 50_000
