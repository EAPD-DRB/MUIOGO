"""The SS-phase solves must run IN-PROCESS (client=None); the dask client is TPI-only.

Measured 2026-08-14 (same machine, same calibration, same solvers): routing SS evaluations
through the dask client costs ~30x per evaluation — anchor 866 s via client (the v16 record)
vs 26.5 s in-process; the whole M=8 SS continuation 89.8 s in-process vs ~42 min via client.
The example script (OG-PHL run_og_phl_multi_industry_calibrated.py) has always done it this
way: SS with client=None, the Client created only for the TPI. This guard exists because the
divergence sat unnoticed in the runner through every blessed coupled run — a config-level
audit ("same Client(), same runner() call") passed while the per-phase behavior differed.
"""
import ast
import os

RUNNER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "oglink", "og_runner.py")


def _runner_calls(tree):
    """Every `runner(...)` call in og_runner, with its keyword args as {name: ast node}."""
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "runner"):
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            out.append((node.lineno, kw))
    return out


def test_ss_phase_runner_calls_have_no_client():
    with open(RUNNER, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    offenders = []
    for lineno, kw in _runner_calls(tree):
        tp, cl = kw.get("time_path"), kw.get("client")
        # SS-only call: time_path=False literally. It must pass client=None literally.
        if isinstance(tp, ast.Constant) and tp.value is False:
            if not (isinstance(cl, ast.Constant) and cl.value is None):
                offenders.append(lineno)
    assert not offenders, (
        f"og_runner.py line(s) {offenders}: SS-phase runner(time_path=False) call passes a "
        "dask client — a measured ~30x per-evaluation slowdown. SS solves run in-process; "
        "the client is for TPI only (see this test's docstring).")


def test_at_least_three_ss_call_sites_guarded():
    # The guard must actually be looking at something: baseline anchor, baseline morph,
    # reform gamma continuation (and _solve's ss branch) all solve SS-only.
    with open(RUNNER, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    ss_calls = [ln for ln, kw in _runner_calls(tree)
                if isinstance(kw.get("time_path"), ast.Constant)
                and kw["time_path"].value is False]
    assert len(ss_calls) >= 3, (
        f"expected >=3 SS-only runner() call sites, found {len(ss_calls)} — "
        "if the runner was restructured, update this guard rather than deleting it.")
