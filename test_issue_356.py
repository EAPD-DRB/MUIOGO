"""
Test for Issue #356: Download endpoints crash with TypeError when no case session is set.
Verifies that all 5 download endpoints return 400 JSON instead of crashing with TypeError.
"""
import sys
import os

# Add project root so imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'API'))

from API.app import app


def run_tests():
    app.config['TESTING'] = True
    client = app.test_client()

    endpoints = [
        ('/downloadDataFile', 'GET', {'caserunname': 'test'}),
        ('/downloadFile', 'GET', {'file': 'test.csv'}),
        ('/downloadCSVFile', 'GET', {'file': 'test.csv', 'caserunname': 'test'}),
        ('/downloadResultsFile', 'GET', {'caserunname': 'test'}),
        ('/downloadCSV', 'GET', {}),
    ]

    passed = 0
    failed = 0

    for path, method, params in endpoints:
        resp = client.get(path, query_string=params)

        if resp.status_code == 400:
            data = resp.get_json()
            if data and data.get('status_code') == 'error':
                print(f"PASS: {path} -> 400 JSON error")
                passed += 1
            else:
                print(f"FAIL: {path} -> 400 but unexpected body: {data}")
                failed += 1
        elif resp.status_code == 500:
            print(f"FAIL: {path} -> 500 (TypeError not fixed!)")
            failed += 1
        else:
            print(f"FAIL: {path} -> unexpected {resp.status_code}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed out of {len(endpoints)}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_tests()
