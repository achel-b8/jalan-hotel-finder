#!/usr/bin/env python3
"""Detect drift between bundled area.xml routes and live Jalan LRG pages."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from lxml import etree


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jalan_hotel_finder.infrastructure.area_xml_resolver import (  # noqa: E402
    DEFAULT_AREA_XML_PATH,
    EXCLUDED_SML_CODES_V1,
    RELOCATED_SML_TO_LRG_OVERRIDES_V1,
)


_SML_CODE_PATTERN = re.compile(r"SML_\d{6}")


@dataclass(frozen=True, slots=True)
class LocalLrgRoute:
    pref_code: str
    pref_name: str
    lrg_code: str
    lrg_name: str
    sml_codes: set[str]


@dataclass(frozen=True, slots=True)
class LrgDriftEntry:
    pref_code: str
    pref_name: str
    lrg_code: str
    lrg_name: str
    url: str
    missing_local_codes: list[str]
    extra_live_codes: list[str]
    unexpected_missing_codes: list[str]
    unexpected_extra_codes: list[str]
    fetch_error: str | None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect route drift between bundled area.xml and live Jalan pages.",
    )
    parser.add_argument(
        "--area-xml-path",
        type=Path,
        default=DEFAULT_AREA_XML_PATH,
        help="Path to bundled area.xml snapshot.",
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=20.0,
        help="HTTP timeout (seconds) per LRG page fetch.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="Optional JSON output path.",
    )
    parser.add_argument(
        "--fail-on-unexpected",
        action="store_true",
        help="Exit 1 when unexpected drifts are detected.",
    )
    return parser.parse_args()


def _collect_local_routes(area_xml_path: Path) -> tuple[list[LocalLrgRoute], dict[str, tuple[str, str]]]:
    root = etree.parse(str(area_xml_path)).getroot()
    lrg_routes: list[LocalLrgRoute] = []
    sml_to_source_pref_lrg: dict[str, tuple[str, str]] = {}

    for prefecture in root.findall("./Prefecture"):
        pref_code = (prefecture.get("cd") or "").strip()
        pref_name = (prefecture.get("name") or "").strip()
        if len(pref_code) != 6 or not pref_code.isdigit() or not pref_name:
            continue

        for large_area in prefecture.findall("./LargeArea"):
            lrg_digits = (large_area.get("cd") or "").strip()
            if len(lrg_digits) != 6 or not lrg_digits.isdigit():
                continue

            lrg_code = f"LRG_{lrg_digits}"
            lrg_name = (large_area.get("name") or "").strip()
            sml_codes: set[str] = set()

            for small_area in large_area.findall("./SmallArea"):
                sml_digits = (small_area.get("cd") or "").strip()
                if len(sml_digits) != 6 or not sml_digits.isdigit():
                    continue
                sml_code = f"SML_{sml_digits}"
                sml_codes.add(sml_code)
                sml_to_source_pref_lrg[sml_code] = (pref_code, lrg_code)

            lrg_routes.append(
                LocalLrgRoute(
                    pref_code=pref_code,
                    pref_name=pref_name,
                    lrg_code=lrg_code,
                    lrg_name=lrg_name,
                    sml_codes=sml_codes,
                )
            )

    return lrg_routes, sml_to_source_pref_lrg


def _extract_live_sml_codes(url: str, timeout_sec: float) -> set[str]:
    request = Request(
        url=url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=timeout_sec) as response:
        body_bytes = response.read()

    body_text = body_bytes.decode("cp932", errors="ignore")
    return set(_SML_CODE_PATTERN.findall(body_text))


def _build_expected_adjustments(
    sml_to_source_pref_lrg: dict[str, tuple[str, str]],
) -> tuple[dict[tuple[str, str], set[str]], dict[tuple[str, str], set[str]]]:
    expected_missing_by_pref_lrg: dict[tuple[str, str], set[str]] = defaultdict(set)
    expected_extra_by_pref_lrg: dict[tuple[str, str], set[str]] = defaultdict(set)

    for sml_code, target_lrg_code in RELOCATED_SML_TO_LRG_OVERRIDES_V1.items():
        source = sml_to_source_pref_lrg.get(sml_code)
        if source is None:
            continue
        pref_code, source_lrg_code = source
        expected_missing_by_pref_lrg[(pref_code, source_lrg_code)].add(sml_code)
        expected_extra_by_pref_lrg[(pref_code, target_lrg_code)].add(sml_code)

    for sml_code in EXCLUDED_SML_CODES_V1:
        source = sml_to_source_pref_lrg.get(sml_code)
        if source is None:
            continue
        expected_missing_by_pref_lrg[source].add(sml_code)

    return expected_missing_by_pref_lrg, expected_extra_by_pref_lrg


def _build_report(args: argparse.Namespace) -> dict[str, Any]:
    lrg_routes, sml_to_source_pref_lrg = _collect_local_routes(args.area_xml_path)
    expected_missing, expected_extra = _build_expected_adjustments(sml_to_source_pref_lrg)
    entries: list[LrgDriftEntry] = []
    fetch_error_count = 0
    unexpected_drift_count = 0

    for local in lrg_routes:
        url = f"https://www.jalan.net/{local.pref_code}/{local.lrg_code}/"
        key = (local.pref_code, local.lrg_code)

        try:
            live_sml_codes = _extract_live_sml_codes(url, args.timeout_sec)
            fetch_error: str | None = None
        except URLError as error:
            live_sml_codes = set()
            fetch_error = f"fetch error: {error}"
            fetch_error_count += 1

        missing_local = sorted(local.sml_codes - live_sml_codes)
        extra_live = sorted(live_sml_codes - local.sml_codes)
        unexpected_missing = sorted(set(missing_local) - expected_missing.get(key, set()))
        unexpected_extra = sorted(set(extra_live) - expected_extra.get(key, set()))

        if unexpected_missing or unexpected_extra:
            unexpected_drift_count += 1

        if fetch_error or missing_local or extra_live:
            entries.append(
                LrgDriftEntry(
                    pref_code=local.pref_code,
                    pref_name=local.pref_name,
                    lrg_code=local.lrg_code,
                    lrg_name=local.lrg_name,
                    url=url,
                    missing_local_codes=missing_local,
                    extra_live_codes=extra_live,
                    unexpected_missing_codes=unexpected_missing,
                    unexpected_extra_codes=unexpected_extra,
                    fetch_error=fetch_error,
                )
            )

    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "area_xml_path": str(args.area_xml_path),
        "checked_lrg_count": len(lrg_routes),
        "drift_lrg_count": len(entries),
        "fetch_error_count": fetch_error_count,
        "unexpected_drift_lrg_count": unexpected_drift_count,
        "entries": [asdict(entry) for entry in entries],
    }
    return report


def main() -> None:
    args = _parse_args()
    report = _build_report(args)
    report_text = json.dumps(report, ensure_ascii=False, indent=2)
    print(report_text)

    if args.output_file is not None:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(report_text, encoding="utf-8")

    if args.fail_on_unexpected and report["unexpected_drift_lrg_count"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
