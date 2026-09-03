"""Run manifest: JSON provenance written next to a coupled run's outputs.

Records what produced a run -- experiment, country, scenario (incl. the CLEWS base/reform
dirs), channels+options, the CLEWS/MUIOGO run dir if one was named, the ogcore version, and
a UTC timestamp -- so a result folder is self-describing and reproducible.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime


def _ogcore_version():
    try:
        import ogcore
        return getattr(ogcore, "__version__", "unknown")
    except Exception:  # noqa: BLE001 (ogcore optional; manifest must never break a run)
        return None


def _json_default(o):
    """Round-trip numpy provenance values (arrays -> lists, scalars -> python) instead of
    stringifying them; fall back to str() for anything else so a manifest never fails to write."""
    import numpy as np
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.generic):
        return o.item()
    return str(o)


def write_run_manifest(out_dir, experiment, country, ctx, clews_run=None, og_model=None,
                       baseline_dir=None, gbd_csv=None, filename="oglink_manifest.json") -> str:
    """Write ``<out_dir>/<filename>`` describing this run; return its path.

    ``experiment`` is the experiment FUNCTION (or its name); its description is the docstring's
    first line, and the channels that ran are read from ``ctx.provenance`` (each record carries
    its own 'channel' id). ``country`` needs .name/.scenario; ``ctx`` needs .provenance. ``og_model``
    is the registry entry's OG-model provenance (package/versions); the link env has no ogcore, so the
    actual solver version comes from the registry, not a local import.

    ``baseline_dir`` (the OG baseline pickle cache, separate from the CLEWS scenario dirs) and
    ``gbd_csv`` (the burden CSV the health channel used) are recorded so a downstream reader (the viz
    deck) can resolve EVERY input from the manifest alone -- no external flags. Both optional and
    additive: absent -> the key is null and readers fall back to discovery, so this never breaks an
    existing manifest consumer.
    """
    import dataclasses
    import inspect
    os.makedirs(out_dir, exist_ok=True)
    sc = country.scenario
    name = getattr(experiment, "__name__", str(experiment))
    desc = (inspect.getdoc(experiment) or "").splitlines()[0] if callable(experiment) else ""
    con = getattr(ctx, "concordance", None)
    manifest = {
        "experiment": {"name": name, "description": desc},
        "country": country.name,
        "un_code": str(getattr(country, "un_code", "")),
        "scenario": {"name": sc.name, "base_dir": sc.base_dir, "reform_dir": sc.reform_dir},
        # input paths the viz needs but can't derive from out_dir: the OG baseline pickle cache
        # (separate dir) and the GBD burden CSV. Recorded so `--coupled-run <dir>` resolves them.
        "baseline_dir": baseline_dir,
        "gbd_csv": gbd_csv,
        # the per-run energy-port concordance the OG runner discovered (None / ports None -> the country
        # could not be coupled on energy, so the energy channels skipped)
        "concordance": dataclasses.asdict(con) if dataclasses.is_dataclass(con) else None,
        "channels": [{"id": pr.get("channel")} for pr in ctx.provenance
                     if not pr.get("provenance_only")],   # e.g. the energy_price_source record
        "clews_run": clews_run,
        "og_model": og_model or {"ogcore_version": _ogcore_version()},
        "timestamp": datetime.now(UTC).isoformat(),
        "provenance": ctx.provenance,
    }
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=_json_default)  # tolerate numpy/Path values
    return path
