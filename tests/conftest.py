"""conftest.py — make extracted logic modules importable for unit tests."""

import sys
from pathlib import Path

# Add test helpers to path
sys.path.insert(0, str(Path(__file__).parent / "unit_logic"))
