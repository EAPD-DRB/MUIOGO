"""Tests for oglink.solve_log -- distilling a persisted solve log into a failure verdict.
Synthetic logs modelled on the real OG-Core / og_runner stream; no model solves."""
from oglink import solve_log


def _write(tmp_path, text):
    p = tmp_path / "solve.log"
    p.write_text(text)
    return str(p)


# a continuation reform: an SS step that converges to ~1e-15, then a TPI that hits the iteration cap.
_TPI_CAP = """[og_runner] reform: gamma shift 0.09 -> solving SS by continuation from the baseline
Iteration: 1
Distance: 3.4e-09
Iteration: 2
Distance: 1.392e-15
[og_runner]   reform continuation t=1.000 (dt=0.250) solved
Iteration: 1
Distance: 2.700929
Iteration: 2
Distance: 0.999998
Iteration: 130
Distance: 0.830918
Iteration: 250
Distance: 0.858434
Max absolute value resource constraint error: 0.0058
Max Euler error, savings: 2.89e-13
Traceback (most recent call last):
  File "ogcore/TPI.py", line 1692, in run_TPI
    raise RuntimeError(
RuntimeError: Transition path equlibrium not found (TPIdist)
"""

_CONVERGED = """Iteration: 1
Distance: 0.512
Dask computation failed with error: solve_for_j cancelled. Falling back to serial computation.
Iteration: 126
Distance: 9.759e-06
[og_runner] solved reform -> /x/reform
"""

_SS_FAIL = """Iteration: 1
Distance: 3.2
Iteration: 40
Distance: 1.7
RuntimeError: Steady state could not be found (SS_dist)
"""

_STALL = """[og_runner]   reform continuation t=0.250 (dt=0.125) solved
RuntimeError: reform gamma continuation stalled at t=0.250 (dt<0.01): the reform steady state could not be reached -- the requested capital share may be infeasible.
"""


def test_tpi_iteration_cap(tmp_path):
    d = solve_log.summarize(_write(tmp_path, _TPI_CAP))
    assert d["phase"] == "reform TPI"
    assert "did not converge" in d["outcome"]
    assert d["iters"] == 250
    # phase-scoped: the SS step's 1e-15 must NOT leak into the TPI's min distance
    assert d["min_distance"] == 0.8309
    assert d["last_distances"][-1] == 0.8584
    assert d["error"].startswith("RuntimeError: Transition path")


def test_converged_ignores_dask_warning(tmp_path):
    # a benign "Dask ... Falling back to serial" line must NOT be read as the failure error
    d = solve_log.summarize(_write(tmp_path, _CONVERGED))
    assert d["outcome"] == "converged"
    assert d["error"] == ""
    assert d["min_distance"] == 9.759e-06


def test_steady_state_failure(tmp_path):
    d = solve_log.summarize(_write(tmp_path, _SS_FAIL))
    assert d["phase"] == "steady state"
    assert "did not converge" in d["outcome"]


def test_continuation_stall_not_misread_as_ss(tmp_path):
    # the stall message also matches the steady-state pattern; the specific verdict must win
    d = solve_log.summarize(_write(tmp_path, _STALL))
    assert d["phase"] == "gamma continuation"
    assert "stalled at t=0.250" in d["outcome"]


def test_why_one_liner(tmp_path):
    d = solve_log.summarize(_write(tmp_path, _TPI_CAP))
    line = solve_log.why(d)
    assert "reform TPI" in line and "250 iters" in line and "0.8584" in line and "min 0.8309" in line


def test_missing_log_is_empty():
    assert solve_log.summarize("/no/such/solve.log") == {}
    assert solve_log.why({}) == "failed (no solve log found)"
