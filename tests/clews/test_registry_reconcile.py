"""CountryRegistry.reconcile: the index follows DataStorage, never the other way.

Covers the launch-time verification: cases added by hand get indexed (unmanaged),
cases installed through a tracked path get adopted from their sidecar, and index
entries whose directory was removed by hand get dropped.
"""
import json

from Classes.Case.CaseImporter import CaseImporter
from Classes.Clews.CountryRegistry import CountryRegistry
from Classes.Clews.Provenance import Provenance

from .conftest import make_case_zip, minimal_gendata


def _hand_made_case(storage, name, version="5.0"):
    """A case dir dropped into DataStorage outside any tracked path."""
    case = storage / name
    case.mkdir()
    (case / "genData.json").write_text(json.dumps(minimal_gendata(name, version)))
    return case


def test_hand_added_case_is_indexed_as_unmanaged(clews_storage):
    _hand_made_case(clews_storage, "HandMade", version="5.0")
    summary = CountryRegistry.reconcile()
    assert summary["unmanaged"] == ["HandMade"]
    record = CountryRegistry.get("HandMade")
    assert record["managed"] is False
    assert record["install_state"] == "unmanaged"
    assert record["case_version"] == "5.0"
    assert record["first_seen_at"]


def test_imported_case_is_adopted_from_sidecar(clews_storage, tmp_path):
    zip_path = make_case_zip(tmp_path, "Tracked", version="5.6")
    CaseImporter.import_zip(str(zip_path), source={"type": "repo_url", "iso3": "PHL"})
    summary = CountryRegistry.reconcile()
    assert summary["adopted"] == ["Tracked"]
    record = CountryRegistry.get("Tracked")
    assert record["managed"] is True
    assert record["install_state"] == "installed"
    assert record["source"]["iso3"] == "PHL"


def test_removed_case_is_dropped_from_index(clews_storage):
    case = _hand_made_case(clews_storage, "Gone")
    CountryRegistry.reconcile()
    assert CountryRegistry.get("Gone") is not None

    # The user deletes the directory by hand.
    import shutil
    shutil.rmtree(case)
    summary = CountryRegistry.reconcile()
    assert summary["removed"] == ["Gone"]
    assert CountryRegistry.get("Gone") is None


def test_reconcile_is_idempotent(clews_storage, tmp_path):
    _hand_made_case(clews_storage, "Stable")
    zip_path = make_case_zip(tmp_path, "AlsoStable", version="5.6")
    CaseImporter.import_zip(str(zip_path))
    first = CountryRegistry.reconcile()
    assert first["adopted"] == ["AlsoStable"] and first["unmanaged"] == ["Stable"]

    second = CountryRegistry.reconcile()
    assert second == {"adopted": [], "unmanaged": [], "removed": [], "total": 2}
    # first_seen_at survives re-runs.
    assert CountryRegistry.get("Stable")["first_seen_at"]


def test_non_case_dirs_and_files_are_ignored(clews_storage):
    (clews_storage / "_chunks").mkdir()               # upload staging
    (clews_storage / "not_a_case").mkdir()            # dir without genData.json
    summary = CountryRegistry.reconcile()
    assert summary["total"] == 0


def test_sidecar_appearing_later_upgrades_unmanaged_to_managed(clews_storage):
    _hand_made_case(clews_storage, "Adopted")
    CountryRegistry.reconcile()
    assert CountryRegistry.get("Adopted")["managed"] is False

    Provenance.write("Adopted", {"source": {"type": "local_path"}, "iso3": "FJI"})
    summary = CountryRegistry.reconcile()
    assert summary["adopted"] == ["Adopted"]
    assert CountryRegistry.get("Adopted")["managed"] is True


def test_reconcile_safe_never_raises(clews_storage, monkeypatch):
    def boom():
        raise RuntimeError("disk on fire")
    monkeypatch.setattr(CountryRegistry, "reconcile", boom)
    assert CountryRegistry.reconcile_safe() is None  # logged, not raised


def test_corrupt_registry_file_recovers(clews_storage):
    _hand_made_case(clews_storage, "Survivor")
    from Classes.Base import Config
    (clews_storage / Config.CLEWS_REGISTRY_BASENAME).write_text("{ broken json")
    summary = CountryRegistry.reconcile()
    assert summary["total"] == 1
    assert CountryRegistry.get("Survivor") is not None


def test_registry_lives_inside_datastorage(clews_storage):
    """Per-storage index: two checkouts on one machine must not share it."""
    from Classes.Base import Config
    _hand_made_case(clews_storage, "Local")
    CountryRegistry.reconcile()
    assert (clews_storage / Config.CLEWS_REGISTRY_BASENAME).is_file()
