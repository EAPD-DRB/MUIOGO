"""Build the user manual without importing the application or models."""

import os

project = "MUIOGO"
author = "UN DESA"
copyright = "2026, UN DESA"

extensions = ["sphinx.ext.mathjax"]
source_suffix = ".rst"
root_doc = "index"
language = "en"
exclude_patterns = ["_build", "_includes/**", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_book_theme"
html_theme_options = {
    "repository_url": "https://github.com/EAPD-DRB/MUIOGO",
    "repository_branch": os.environ.get("MUIOGO_DOCS_BRANCH", "main"),
    "use_repository_button": True,
    "use_edit_page_button": True,
    "path_to_docs": "docs/source",
    "home_page_in_toc": True,
    "show_navbar_depth": 2,
    "footer_content_items": ["copyright.html", "last-updated.html", "extra-footer.html"],
    "extra_footer": (
        'Licensed under the <a href="https://www.apache.org/licenses/LICENSE-2.0">'
        'Apache License, Version 2.0</a>.'
    ),
}
html_title = "MUIOGO user manual"
html_short_title = "MUIOGO"
html_static_path = ["_static"]
html_css_files = ["manual.css"]
html_logo = "_static/muiogo-logo.png"

latex_documents = [
    (root_doc, "MUIOGO.tex", "MUIOGO user manual", author, "manual"),
]
