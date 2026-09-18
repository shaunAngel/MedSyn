"""Backend package alias for shift module."""

import sys
from pathlib import Path

# Ensure root directory is on sys.path for direct imports
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from shift import *  # noqa: F401, F403
import shift as _shift

# Re-export all public symbols
__all__ = [name for name in dir(_shift) if not name.startswith("_")]
