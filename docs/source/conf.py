import sys
import os
from sphinx.ext import apidoc


root = os.path.abspath('../../')
module = os.path.join(root, "sc3")
output = os.path.join(root, "docs/source/api")
sys.path.insert(0, root)

apidoc.main(['-fMe', '-o', output, module])

project = 'sc3 - SuperCollider client for Python'
copyright = '2025, SuperCollider 3 documentation contributors'
author = 'Lucas Samaruga'

templates_path = ['_templates']
exclude_patterns = []
language = 'en'

root_doc = 'index'

html_theme = 'sphinx_rtd_theme'
html_static_path = ['images']

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode'
]
