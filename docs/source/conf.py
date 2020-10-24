# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# Modules to document need to be added to sys.path.

import os
import sys
from sphinx.ext import apidoc  # Sphinx >= 1.7

root = os.path.abspath('../../')
module = os.path.join(root, "sc3")
output = os.path.join(root, "docs/source/api")
sys.path.insert(0, root)

try:
    apidoc.main(['-f', '-o', output, module])
except Exception as e:
    print(f"Running `sphinx-apidoc` failed!\n{e}")


# -- Project information -----------------------------------------------------

project = 'sc3'
copyright = '2020, Lucas Samaruga'
author = 'Lucas Samaruga'

# The full version, including alpha/beta/rc tags
release = '1.0.0a'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

master_doc = 'index'

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'default'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# -- Extensions configuration_ -----------------------------------------------

# Autodoc. Join class and __init__ docstring.
# autoclass_content = 'both'

# Autodoc. Sort by member type
autodoc_member_order = 'groupwise'
