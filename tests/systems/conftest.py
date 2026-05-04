"""
conftest.py for tests/systems/ — adds the tests root to sys.path so that
`from test_utils import make_configured_world` works in all system tests.
"""
import sys
import os

# Ensure the tests root directory is on sys.path so test_utils is importable.
_tests_root = os.path.dirname(os.path.dirname(__file__))
if _tests_root not in sys.path:
    sys.path.insert(0, _tests_root)
