from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Ensure the ``src`` directory is on sys.path so Sphinx sees ``pypipe``
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

try:
    import pypipe

    release = pypipe.__version__
except Exception:  # pragma: no cover - docs build fallback
    release = "0.0.0"

project = "pypipe"
copyright = f"{datetime.now():%Y}, PyPipe contributors"
author = "PyPipe contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx_autodoc_typehints",
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
