"""Visualization subpackage -- the editorial figure deck for a coupled OG-Core x CLEWS run.

`build_figures(country, run_dir, ...)` is the single entry point (the orchestrator): it composes
the chart functions in `plots`, the cover/summary tables in `tables`, and the index/HTML in
`report`, all on the shared house theme in `style`. Run the whole deck with
`python -m oglink.viz`.
"""
from .build import build_figures  # noqa: F401
