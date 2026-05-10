# Configuration file for the Sphinx documentation builder.
#
# This configuration is adapted for a documentation-oriented repository.
# Most pages are Markdown files parsed through MyST.

import os
import sys
from pathlib import Path

# Make the repository root importable if Python modules are added later.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

project = "HK Software Material"
author = "Alberto Montanelli"
release = "0.1.0"

# --- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "myst_parser",
    "sphinx_copybutton",
]

todo_include_todos = True

autoclass_content = "class"
autodoc_class_signature = "separated"
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "undoc-members": True,
    "private-members": False,
    "special-members": "__init__",
}

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

# Markdown support via MyST.
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
]

# Options for syntax highlighting.
pygments_style = "default"
pygments_dark_style = "default"

# Documentation language.
language = "en"

rst_prolog = """
.. |Python| replace:: `Python <https://www.python.org/>`__
.. |Sphinx| replace:: `Sphinx <https://www.sphinx-doc.org/>`__
.. |GitHub| replace:: `GitHub <https://github.com/>`__
.. |Apptainer| replace:: `Apptainer <https://apptainer.org/>`__
.. |Singularity| replace:: `Singularity <https://docs.sylabs.io/>`__
"""

# --- Options for HTML output -------------------------------------------------

html_theme = "sphinxawesome_theme"
html_theme_options = {
    "awesome_external_links": True,
}

html_title = "HK Software Material"
html_permalinks_icon = "<span>#</span>"
html_static_path = ["_static"]

# Keep generated pages compact and readable.
html_show_sourcelink = True
html_show_sphinx = True
