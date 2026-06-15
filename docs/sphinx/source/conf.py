# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html#configuration

import os
import sys

# Add project root so autodoc can import the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

# -- Auto-generate module RST stubs with sphinx-apidoc -----------------------
# This replaces manual maintenance of modules/*.rst files. Runs once per build.


def run_apidoc(_app):
    """Generate RST stubs for all Python packages under src/."""
    from sphinx.ext.apidoc import main as apidoc_main

    out_dir = os.path.join(os.path.dirname(__file__), "modules")
    src_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "src")
    apidoc_main([
        "-o", out_dir,
        src_dir,
        "--separate",
        "--force",
        "-d", "2",
        "test*",             # Exclude test packages
        "*/test*",           # Exclude test subdirs (fnmatch, depth-insensitive)
        "*/resources*",      # Exclude data file directories
    ])
    # Remove unwanted stubs post-generation (fnmatch patterns in apidoc
    # are unreliable for top-level package names)
    unwanted_prefixes = ["stargazingplacefinder"]
    for f in os.listdir(out_dir):
        if any(f.startswith(prefix) for prefix in unwanted_prefixes):
            os.remove(os.path.join(out_dir, f))

    # Also strip unwanted entries from the auto-generated modules.rst TOC
    modules_rst = os.path.join(out_dir, "modules.rst")
    if os.path.exists(modules_rst):
        with open(modules_rst, "r") as f:
            lines = f.readlines()
        with open(modules_rst, "w") as f:
            for line in lines:
                stripped = line.strip()
                # Skip lines that reference unwanted packages
                if any(stripped.startswith(prefix) for prefix in unwanted_prefixes):
                    continue
                f.write(line)


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Stargazing Place Finder'
copyright = '2026, StarGazer1995'
author = 'StarGazer1995'
release = '0.6.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosummary',
]

# autodoc: document __init__ methods and show type hints
autoclass_content = 'both'
autodoc_typehints = 'description'
napoleon_google_docstring = True
napoleon_numpy_docstring = False
autosummary_generate = False  # We use sphinx-apidoc instead for stub generation

templates_path = ['_templates']
exclude_patterns = []

language = 'zh_CN'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']


# -- Connect apidoc to run before each build ---------------------------------
def setup(app):
    app.connect('builder-inited', run_apidoc)
