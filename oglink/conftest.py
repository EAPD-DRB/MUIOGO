import os
import sys

# make `import oglink` resolve when running pytest from anywhere without an editable install
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
