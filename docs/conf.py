# -*- coding: utf-8 -*-
from __future__ import print_function

from pallets_sphinx_themes import ProjectLink, get_version

# Project --------------------------------------------------------------

project = 'MarkupSafe'
copyright = '2010 Pallets team'
author = 'Pallets team'
release, version = get_version('MarkupSafe')

# General --------------------------------------------------------------

master_doc = 'index'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
}

# HTML -----------------------------------------------------------------

html_theme = 'flask'
html_context = {
    'project_links': [
        ProjectLink(
            'Donate to Pallets',
            'https://psfmember.org/civicrm/contribute/transact?reset=1&id=20'),
        ProjectLink(
            'MarkupSafe Website', 'https://palletsprojects.com/p/markupsafe/'),
        ProjectLink('PyPI Releases', 'https://pypi.org/project/MarkupSafe/'),
        ProjectLink('Source Code', 'https://github.com/pallets/markupsafe/'),
        ProjectLink(
            'Issue Tracker', 'https://github.com/pallets/MarkupSafe/issues/'),
    ],
}
html_sidebars = {
    'index': [
        'project.html',
        'searchbox.html',
    ],
    '**': [
        'localtoc.html',
        'relations.html',
        'searchbox.html',
    ]
}
html_show_sourcelink = False

# LaTeX ----------------------------------------------------------------

latex_documents = [
    (
        master_doc, 'MarkupSafe.tex', 'MarkupSafe Documentation',
        'Pallets team', 'manual'
    ),
]
latex_use_modindex = False
latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '12pt',
}
latex_use_parts = True

# linkcheck ------------------------------------------------------------

linkcheck_anchors = False
