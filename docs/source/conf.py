# Configuration file for the Sphinx documentation builder.
import os, sys
import sphinx_rtd_theme
sys.path.insert(0, os.path.abspath('../../source'))  

# -- Project information

project = 'BatchScan'
aps = 'Argonne National Laboratory'
copyright = '2020 - 2023, ' + aps


release = '0.1'
version = '0.1.0'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']
autodoc_mock_imports = ['epics', 'matplotlib', 'numpy', 'scipy', 'cv2', 'pandas', 'Transform', 'h5py']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_theme_options = {
    'style_nav_header_background': '#4f8fb8ff',
    'collapse_navigation': False,
    'logo_only': False,
}

# Output file base name for HTML help builder.
htmlhelp_basename = project + 'doc'


# -- Options for LaTeX output ---------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('index', project + '.tex', project + u' Documentation', aps,
     'manual'),
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', project, project + u' Documentation', aps, project,
     'BatchScan: Python-based user interface for scan control', 'Miscellaneous'),
]

# -- Options for EPUB output
epub_show_urls = 'footnote'
