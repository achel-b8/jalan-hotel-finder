from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def _load_script_module():
    script_path = Path("scripts/detect_area_xml_route_drift.py")
    spec = spec_from_file_location("detect_area_xml_route_drift", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load script module spec")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_collect_local_routes_reads_pref_lrg_sml_structure() -> None:
    module = _load_script_module()
    fixture = Path("tests/fixtures/xml/area_with_duplicates.xml")

    routes, source_map = module._collect_local_routes(fixture)

    assert len(routes) == 1
    route = routes[0]
    assert route.pref_code == "990000"
    assert route.lrg_code == "LRG_990100"
    assert route.sml_codes == {"SML_990101", "SML_990102"}
    assert source_map["SML_990101"] == ("990000", "LRG_990100")


def test_build_expected_adjustments_applies_relocated_and_excluded_rules() -> None:
    module = _load_script_module()
    source_map = {
        "SML_013508": ("010000", "LRG_013500"),
        "SML_212910": ("210000", "LRG_212900"),
        "SML_251105": ("250000", "LRG_251100"),
    }

    expected_missing, expected_extra = module._build_expected_adjustments(source_map)

    assert "SML_013508" in expected_missing[("010000", "LRG_013500")]
    assert "SML_013508" in expected_extra[("010000", "LRG_011400")]
    assert "SML_212910" in expected_missing[("210000", "LRG_212900")]
    assert "SML_212910" in expected_extra[("210000", "LRG_213700")]
    assert "SML_251105" in expected_missing[("250000", "LRG_251100")]
