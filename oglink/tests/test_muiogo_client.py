import io
import json
import urllib.error

import pytest

from oglink.muiogo_client import apply_via_muiogo


class Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def test_success_request_matches_application_contract(monkeypatch):
    calls = []
    result = {'status_code': 'success', 'case_copy': 'copy', 'caserun': 'NEW', 'csv_dir': '/csv'}
    def urlopen(request, timeout):
        calls.append((request, timeout))
        return Response(json.dumps(result).encode())
    monkeypatch.setattr('urllib.request.urlopen', urlopen)
    patch = {'case': 'case', 'changes': [{'group': 'Demand'}]}
    assert apply_via_muiogo(patch, 'REF', base_url='http://localhost:5000/') == result
    request, timeout = calls[0]
    assert request.full_url == 'http://localhost:5000/oglink/applyPatch'
    assert request.method == 'POST'
    assert json.loads(request.data) == {'patch': patch, 'base_caserun': 'REF', 'solver': 'CBC'}
    assert not request.has_header('Origin')
    assert timeout == 21600


@pytest.mark.parametrize('body,detail', [
    ({'message': 'blocked input', 'blocked': [{'change_index': 2, 'reason': 'unknown commodity'}]}, 'unknown commodity'),
    ({'message': 'structure changed', 'finding': 'datafile_structure_changed'}, 'datafile_structure_changed'),
    (['unexpected shape'], 'unexpected shape'), ('upstream failed', 'upstream failed')])
def test_http_failure_keeps_structured_or_raw_reason(monkeypatch, body, detail):
    raw = (json.dumps(body) if not isinstance(body, str) else body).encode()
    def urlopen(*args, **kwargs):
        raise urllib.error.HTTPError('http://localhost', 422, 'blocked', {}, io.BytesIO(raw))
    monkeypatch.setattr('urllib.request.urlopen', urlopen)
    with pytest.raises(RuntimeError, match=detail):
        apply_via_muiogo({}, 'REF', base_url='http://localhost')


@pytest.mark.parametrize('body', [b'not json', b'[]', b'{}', b'{"status_code":"error"}'])
def test_http_200_must_still_describe_success(monkeypatch, body):
    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **k: Response(body))
    with pytest.raises(RuntimeError):
        apply_via_muiogo({}, 'REF', base_url='http://localhost')


@pytest.mark.parametrize('exc', [urllib.error.URLError('refused'), TimeoutError('timed out')])
def test_connection_failure_names_server(monkeypatch, exc):
    def urlopen(*args, **kwargs):
        raise exc
    monkeypatch.setattr('urllib.request.urlopen', urlopen)
    with pytest.raises(RuntimeError, match='http://localhost/oglink/applyPatch'):
        apply_via_muiogo({}, 'REF', base_url='http://localhost')
