"""Guards for the two port-specific changes, so they cannot silently regress:
  1. env isolation -- runtime._run must NOT inject the link env's path onto the OG subprocess;
  2. the cost-push phi source -- an UNEXPECTED failure must be recorded to provenance, not swallowed.
"""
import types

import subprocess

from oglink import experiments, framework, runtime


def test_run_does_not_inject_link_path(monkeypatch):
    captured = {}

    class _FakeProc:
        stdout = iter(())
        def wait(self):
            return 0

    def _fake_popen(cmd, env=None, **kw):
        captured["env"] = env
        captured["cmd"] = cmd
        return _FakeProc()

    monkeypatch.setattr(subprocess, "Popen", _fake_popen)
    entry = types.SimpleNamespace(env_python="python", package="ogx")
    rc = runtime._run(entry, ["export-baseline"], "test")
    assert rc == 0
    # the child's PYTHONPATH is exactly the parent's -- the link source root is never prepended
    import os
    assert captured["env"].get("PYTHONPATH") == os.environ.get("PYTHONPATH")
    # the removed injection constant must stay removed
    assert not hasattr(runtime, "_LINK_ROOT")
    # sanity: it still invokes the runner module by name in the OG env
    assert captured["cmd"][:3] == ["python", "-m", "oglink.og_runner"]


def test_electricity_intensity_logs_unexpected_failure():
    # a country whose OG model is not registered -> registry.lookup raises -> must log, then return None
    ctx = framework.ExperimentContext(
        country=types.SimpleNamespace(og_repo="no-such-model-xyz", og_package="nope"))
    phi = experiments._electricity_intensity(ctx)
    assert phi is None
    recs = [r for r in ctx.provenance if r.get("channel") == "electricity_intensity_unavailable"]
    assert recs, "an unexpected phi-source failure must leave a provenance record"
    assert recs[0].get("provenance_only") is True
    assert "reason" in recs[0]
