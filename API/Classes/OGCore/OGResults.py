"""Read-only assembly of run results from the worker's plain JSON.

The worker writes every result the dashboard needs as strict JSON inside each
run directory (results_ss.json, results_tpi.json, results_meta.json). This module
reads only those files: MUIOGO never opens a pickle and never imports ogcore. It
turns the raw variable dumps into the consolidated contract shape the dashboard's
opening screen expects, and offers the granular subset reads behind it.
"""

from __future__ import annotations

import json
from pathlib import Path

_VARS = ("Y", "C", "K", "L", "r", "w")

_LABELS = {
    "Y": "GDP",
    "C": "Consumption",
    "K": "Capital stock",
    "L": "Labor supply",
    "r": "Interest rate",
    "w": "Wage rate",
}

_UNITS = {
    "Y": "level",
    "C": "level",
    "K": "level",
    "L": "level",
    "r": "rate",
    "w": "rate",
}


def read_json(path):
    """Read a JSON object from ``path``, or None if missing or unreadable.

    A dict is expected; anything else (or any read/parse failure, or a missing
    file) collapses to None so callers can treat every not-usable case the same.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


class OGResults:
    """Assembles dashboard-ready results from a run's plain JSON files."""

    @staticmethod
    def load_ss(run_dir):
        """The run's steady-state variables, or None if not readable."""
        return read_json(Path(run_dir) / "results_ss.json")

    @staticmethod
    def load_tpi(run_dir):
        """The run's transition-path variables, or None if not readable."""
        return read_json(Path(run_dir) / "results_tpi.json")

    @staticmethod
    def load_meta(run_dir):
        """The run's results meta (start_year, T, S), or None if not readable."""
        return read_json(Path(run_dir) / "results_meta.json")

    @staticmethod
    def subset(data: dict, var_names) -> dict:
        """The named variables of ``data``; the full dict when var_names is None."""
        if var_names is None:
            return dict(data)
        return {k: data[k] for k in var_names if k in data}

    @staticmethod
    def pct_diff(base_list, reform_list) -> list:
        """Element-wise (reform - base) / base * 100, aligned by index.

        None wherever the baseline is None or zero, or the reform is None; a float
        otherwise. Caller aligns the two lists to equal length beforehand.
        """
        out = []
        for base, reform in zip(base_list, reform_list):
            if base is None or base == 0 or reform is None:
                out.append(None)
            else:
                out.append((reform - base) / base * 100.0)
        return out

    @classmethod
    def consolidated(cls, casename, base_run, reform_run, base_dir, reform_dir):
        """Build the consolidated results object for the dashboard's opening screen.

        Returns (payload, None) on success, or (None, (message, http)) on any
        expected failure. reform_run / reform_dir are None for a baseline-only
        view; when a reform is selected the long-run steady-state panel reflects
        the reform scenario, matching the dashboard's selected-scenario semantics.
        """
        base_meta = cls.load_meta(base_dir)
        base_tpi = cls.load_tpi(base_dir)
        if base_meta is None or base_tpi is None:
            return None, (
                "No transition path results - run the baseline with the full "
                "time path first.",
                404,
            )

        start_year = int(base_meta.get("start_year", 0))
        n = min(30, int(base_meta.get("T", 0)))
        years = [start_year + i for i in range(n)]

        reform_tpi = None
        if reform_dir is not None:
            reform_tpi = cls.load_tpi(reform_dir)
            if reform_tpi is None:
                return None, (
                    "No transition path results for reform run "
                    f"'{reform_run}' - run it with the full time path first.",
                    404,
                )

        series = {}
        for var in _VARS:
            base_series = base_tpi.get(var)
            if not isinstance(base_series, list):
                continue
            baseline = _first_n(base_series, n)
            # Only 1-D numeric paths are plottable; a nested array here (possible
            # in a country variant) must skip the var, never crash the read.
            if not _all_scalar(baseline):
                continue
            entry = {"baseline": baseline}
            if reform_dir is not None:
                reform_full = reform_tpi.get(var)
                reform = _first_n(reform_full, n) if isinstance(reform_full, list) else [None] * n
                if not _all_scalar(reform):
                    reform = [None] * n
                entry["reform"] = reform
                entry["pct_diff"] = cls.pct_diff(baseline, reform)
            series[var] = entry

        if not series:
            return None, ("No plottable variables in the results.", 404)

        # One ss block, showing the selected scenario: the reform run's steady
        # state when a reform is chosen, otherwise the baseline's.
        ss_source = cls.load_ss(reform_dir if reform_dir is not None else base_dir) or {}
        ss = {var: ss_source.get(var) for var in _VARS if var in ss_source}

        included = list(series.keys())
        meta = {
            "default_view": "pct_diff" if reform_dir is not None else "levels",
            "labels": {k: _LABELS[k] for k in included if k in _LABELS},
            "units": {k: _UNITS[k] for k in included if k in _UNITS},
        }

        payload = {
            "status_code": "success",
            "casename": casename,
            "base_run": base_run,
        }
        if reform_run is not None:
            payload["reform_run"] = reform_run
        payload["years"] = years
        payload["series"] = series
        payload["ss"] = ss
        payload["meta"] = meta
        return payload, None


def _first_n(values: list, n: int) -> list:
    """First ``n`` values of ``values``, padded with None if it is shorter."""
    out = list(values[:n])
    if len(out) < n:
        out.extend([None] * (n - len(out)))
    return out


def _all_scalar(values: list) -> bool:
    """True when every entry is a number or None (a plottable 1-D path)."""
    return all(v is None or isinstance(v, int | float) for v in values)
