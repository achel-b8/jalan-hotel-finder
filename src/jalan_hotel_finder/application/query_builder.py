"""Build Jalan search URLs from validated CLI inputs."""

import re
from urllib.parse import quote_from_bytes, urlencode, urlunsplit

from jalan_hotel_finder.application.input_models import (
    KeywordEncoding,
    MealType,
    SearchAreaInput,
)


_SML_CODE_PATTERN = re.compile(r"^SML_(\d{6})$")
_MEAL_TYPE_TO_PARAM = {
    MealType.NONE: "0",
    MealType.BREAKFAST: "1",
    MealType.DINNER: "2",
    MealType.TWO_MEALS: "3",
}


def build_search_area_url(sml_code: str, user_input: SearchAreaInput) -> str:
    """Build a search URL for one SML area."""
    sml_digits = _extract_sml_digits(sml_code)
    pref_code = f"{sml_digits[:2]}0000"
    lrg_code = f"{sml_digits[:4]}00"

    query_params = {
        "stayYear": f"{user_input.checkin.year:04d}",
        "stayMonth": f"{user_input.checkin.month:02d}",
        "stayDay": f"{user_input.checkin.day:02d}",
        "adultNum": str(user_input.adults),
        "stayCount": str(user_input.nights),
        "roomCount": "1",
        "dateUndecided": "0",
        "careBath": "0",
    }

    if user_input.meal_type is not None:
        query_params["mealType"] = _MEAL_TYPE_TO_PARAM[user_input.meal_type]

    if user_input.care_kakenagashi:
        query_params["careKake"] = "1"
    if user_input.care_bath_rent:
        query_params["careBathRent"] = "1"
    if user_input.care_private_openair:
        query_params["carePribateBath"] = "1"

    path = f"/{pref_code}/LRG_{lrg_code}/SML_{sml_digits}/"
    return urlunsplit(("https", "www.jalan.net", path, urlencode(query_params), ""))


def build_keyword_search_url(keyword: str, encoding: KeywordEncoding) -> str:
    """Build one-shot keyword search URL."""
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        raise ValueError("keyword must not be empty")

    encoded_keyword = _encode_keyword_for_query(normalized_keyword, encoding)
    query = (
        f"keyword={encoded_keyword}"
        "&distCd=06"
        "&rootCd=7701"
        "&screenId=FWPCTOP"
        "&ccnt=button-fw"
        "&image1="
    )
    return urlunsplit(
        ("https", "www.jalan.net", "/uw/uwp2011/uww2011init.do", query, "")
    )


def _extract_sml_digits(sml_code: str) -> str:
    match = _SML_CODE_PATTERN.fullmatch(sml_code)
    if match is None:
        raise ValueError(f"invalid SML code: {sml_code}")
    return match.group(1)


def _encode_keyword_for_query(keyword: str, encoding: KeywordEncoding) -> str:
    # v1 keyword mode is one-shot; auto is treated as cp932.
    codec = "utf-8"
    if encoding in {KeywordEncoding.CP932, KeywordEncoding.AUTO}:
        codec = "cp932"
    return quote_from_bytes(keyword.encode(codec))
