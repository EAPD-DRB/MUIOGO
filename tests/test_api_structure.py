import os

def test_api_directory_exists():
    assert os.path.isdir("API")

def test_routes_directory_exists():
    assert os.path.isdir("API/Routes")

def test_classes_directory_exists():
    assert os.path.isdir("API/Classes")