import importlib
import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


MODULE_NAMES = [
    "jalan_hotel_finder",
    "jalan_hotel_finder.cli",
    "jalan_hotel_finder.application",
    "jalan_hotel_finder.domain",
    "jalan_hotel_finder.infrastructure",
    "jalan_hotel_finder.output",
]


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_import_smoke(module_name: str) -> None:
    importlib.import_module(module_name)

