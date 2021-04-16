from pallets_sphinx_themes import get_version
from pallets_sphinx_themes import ProjectLink

# Project --------------------------------------------------------------

project = "MarkupSafe"
copyright = "2010 Pallets"
author = "Pallets"
release, version = get_version("MarkupSafe")

# General --------------------------------------------------------------

master_doc = "index"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "pallets_sphinx_themes",
    "sphinxcontrib.log_cabinet",
    "sphinx_issues",
]
autodoc_typehints = "description"
intersphinx_mapping = {"python": ("https://docs.python.org/3/", None)}
issues_github_path = "pallets/markupsafe"

# HTML -----------------------------------------------------------------

html_theme = "jinja"
html_theme_options = {"index_sidebar_logo": False}
html_context = {
    "project_links": [
        ProjectLink("Donate", "https://palletsprojects.com/donate"),
        ProjectLink("PyPI Releases", "https://pypi.org/project/MarkupSafe/"),
        ProjectLink("Source Code", "https://github.com/pallets/markupsafe/"),
        ProjectLink("Issue Tracker", "https://github.com/pallets/markupsafe/issues/"),
        ProjectLink("Website", "https://palletsprojects.com/p/markupsafe/"),
        ProjectLink("Twitter", "https://twitter.com/PalletsTeam"),
        ProjectLink("Chat", "https://discord.gg/pallets"),
    ]
}
html_sidebars = {
    "index": ["project.html", "localtoc.html", "searchbox.html"],
    "**": ["localtoc.html", "relations.html", "searchbox.html"],
}
singlehtml_sidebars = {"index": ["project.html", "localtoc.html"]}
html_title = f"MarkupSafe Documentation ({version})"
html_show_sourcelink = False

# LaTeX ----------------------------------------------------------------

latex_documents = [
    (master_doc, f"MarkupSafe-{version}.tex", html_title, author, "manual")
]
