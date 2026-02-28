import sys
import os
from pathlib import Path

# Add the API folder to sys.path so that 'import app' 
# and 'from Classes.Base import Config' work exactly as they do in production
api_path = Path(__file__).parent.parent / "API"
sys.path.insert(0, str(api_path.resolve()))
