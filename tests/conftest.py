"""Test configuration.

Makes the repository root importable and stubs out heavy optional
dependencies (`together`, `fitz`) when they are not installed, so the
pure-Python logic can be tested in isolation.
"""

import sys
import types
from pathlib import Path

# Make the repository root importable regardless of where pytest is invoked.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import together  # noqa: F401
except ImportError:
    stub = types.ModuleType("together")

    class _Together:  # pragma: no cover - only instantiated at request time
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "The 'together' package is not installed; install it to make API calls."
            )

    stub.Together = _Together
    sys.modules["together"] = stub

try:
    import fitz  # noqa: F401
except ImportError:
    stub = types.ModuleType("fitz")

    def _open(*args, **kwargs):  # pragma: no cover - PDF tests need real PyMuPDF
        raise RuntimeError("PyMuPDF (fitz) is not installed.")

    stub.open = _open
    sys.modules["fitz"] = stub
