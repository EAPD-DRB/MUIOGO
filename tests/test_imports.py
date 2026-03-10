import sys
import os

sys.path.append(os.path.abspath("."))

def test_import_api_module():
    import API
    assert API is not None