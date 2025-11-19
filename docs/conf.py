from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Ensure the ``src`` directory is on sys.path so Sphinx sees ``pygha``
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

try:
    import pygha

    release = pygha.__version__
except Exception:  # pragma: no cover - docs build fallback
    release = "0.0.0"

project = "pygha"
copyright = f"{datetime.now():%Y}, pygha contributors"
author = "pygha contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx_autodoc_typehints",
    "sphinx.ext.doctest",
    "sphinx.builders.linkcheck",
]

html_css_files = ["css/custom.css"]

autosectionlabel_prefix_document = True

templates_path = ["_templates"]
exclude_patterns: list[str] = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = ["_static"]
html_logo = "_static/images/logo.png"

# Give the logo breathing room on narrow layouts
html_theme_options = {"logo_name": False, "logo_text_align": "center", "description": ""}
