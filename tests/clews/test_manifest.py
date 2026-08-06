"""CountryManifest: URL parsing, checksum parsing, validation, selection, gating."""
import pytest

from Classes.Clews import CountryManifest as cm
from Classes.Clews.ClewsInstaller import version_gate


def test_parse_github_url_variants():
    for url in ("https://github.com/EAPD-DRB/CLEWs-PHL",
                "https://github.com/EAPD-DRB/CLEWs-PHL/",
                "https://github.com/EAPD-DRB/CLEWs-PHL.git",
                "http://www.github.com/EAPD-DRB/CLEWs-PHL"):
        assert cm.parse_github_url(url) == ("EAPD-DRB", "CLEWs-PHL"), url
    for url in ("https://gitlab.com/x/y", "not a url", "",
                "https://github.com/only-owner"):
        assert cm.parse_github_url(url) is None, url


def test_parse_sha256sums():
    text = ("# comment\n"
            "8657478a274cc96be44dc8a7ee2a370d0589b71c1f2308610297fe58b8b5ee24  a.zip\n"
            "D1F588F6D4B51BBC105CC071B418FA238DCD43A0F6D7BD916C6CDC97ED898214 *b.zip\n"
            "garbage line\n")
    sums = cm.parse_sha256sums(text)
    assert sums["a.zip"].startswith("8657478a")
    assert sums["b.zip"].startswith("d1f588f6")  # lowercased
    assert len(sums) == 2


def _valid_manifest():
    return {
        "schema_version": 1, "iso3": "TST", "name": "Testland",
        "vintages": [{"id": "v2", "dir": "b/muio", "sha256sums": "SHA256SUMS",
                      "cases": [{"case": "A", "archive": "A.zip"}]}],
    }


def test_validate_manifest_accepts_valid():
    assert cm.validate_manifest(_valid_manifest())["iso3"] == "TST"


@pytest.mark.parametrize("mutate,fragment", [
    (lambda m: m.update(schema_version=2), "schema_version"),
    (lambda m: m.pop("iso3"), "iso3"),
    (lambda m: m.update(vintages=[]), "no vintages"),
    (lambda m: m["vintages"][0].pop("dir"), "dir"),
    (lambda m: m["vintages"][0].update(cases=[]), "no cases"),
    (lambda m: m["vintages"][0]["cases"][0].pop("archive"), "archive"),
    (lambda m: m["vintages"][0].update(dir="../escape"), "unsafe"),
    (lambda m: m["vintages"][0]["cases"][0].update(archive="sub/dir.zip"), "plain filename"),
    (lambda m: m.update(vintages=m["vintages"] * 2), "Duplicate"),
])
def test_validate_manifest_refuses(mutate, fragment):
    manifest = _valid_manifest()
    mutate(manifest)
    with pytest.raises(cm.ManifestError, match=fragment):
        cm.validate_manifest(manifest)


def test_select_vintage_and_cases():
    manifest = {
        "vintages": [
            {"id": "v1", "cases": [{"case": "Old", "archive": "o.zip"}]},
            {"id": "v2", "recommended": True,
             "cases": [{"case": "A", "archive": "a.zip", "recommended": True},
                       {"case": "B", "archive": "b.zip"}]},
        ]
    }
    assert cm.select_vintage(manifest)["id"] == "v2"          # recommended wins
    assert cm.select_vintage(manifest, "v1")["id"] == "v1"    # explicit wins
    with pytest.raises(cm.ManifestError, match="v9"):
        cm.select_vintage(manifest, "v9")

    v2 = cm.select_vintage(manifest)
    assert [c["case"] for c in cm.select_cases(v2)] == ["A"]  # recommended default
    assert [c["case"] for c in cm.select_cases(v2, ["B", "A"])] == ["B", "A"]
    with pytest.raises(cm.ManifestError, match="Nope"):
        cm.select_cases(v2, ["Nope"])
    v1 = cm.select_vintage(manifest, "v1")
    assert [c["case"] for c in cm.select_cases(v1)] == ["Old"]  # no recommended -> all


def test_version_gate():
    assert version_gate({"muio_min_version": "5.6"}) is None
    assert version_gate({}) is None
    assert version_gate({"muio_min_version": "not-a-version"}) is None
    refusal = version_gate({"muio_min_version": "99.0"})
    assert refusal and "99.0" in refusal


def test_source_local_path_requires_dir(tmp_path):
    with pytest.raises(cm.ManifestError):
        cm.CountrySource(source_type="local_path", local_path=str(tmp_path / "nope"))
    with pytest.raises(cm.ManifestError):
        cm.CountrySource(source_type="repo_url", repo_url="https://gitlab.com/x/y")
    with pytest.raises(cm.ManifestError):
        cm.CountrySource(source_type="weird")


def test_repo_url_source_fetches_raw(monkeypatch, tmp_path):
    """URL building + decoding path for a GitHub source, without any network."""
    calls = []

    def fake_fetch(url, timeout=20):
        calls.append(url)
        return b'{"schema_version": 1}'

    monkeypatch.setattr(cm, "fetch_bytes", fake_fetch)
    src = cm.CountrySource(source_type="repo_url",
                           repo_url="https://github.com/EAPD-DRB/CLEWs-PHL",
                           ref="main")
    assert src.read_text("clews-country.json") == '{"schema_version": 1}'
    assert calls == ["https://raw.githubusercontent.com/EAPD-DRB/CLEWs-PHL/main/clews-country.json"]


def test_missing_remote_manifest_reports_not_found(monkeypatch):
    """A 404 must surface as 'not found', not be rewrapped as a JSON complaint
    (ManifestError subclasses ValueError, which load_manifest's parse guard
    would otherwise swallow -- caught live against the real CLEWs-PHL repo)."""
    import urllib.error

    def fake_fetch(url, timeout=20):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(cm, "fetch_bytes", fake_fetch)
    src = cm.CountrySource(source_type="repo_url",
                           repo_url="https://github.com/EAPD-DRB/CLEWs-PHL")
    with pytest.raises(cm.ManifestError) as exc:
        src.load_manifest()
    assert "not found" in str(exc.value)
    assert "not valid JSON" not in str(exc.value)


def test_github_token_header(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok123")
    headers = cm._auth_headers()
    assert headers["Authorization"] == "Bearer tok123"
    monkeypatch.delenv("GITHUB_TOKEN")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert "Authorization" not in cm._auth_headers()
