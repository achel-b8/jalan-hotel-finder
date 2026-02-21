import json

from jalan_hotel_finder.output.json_formatter import serialize_search_results


def test_serialize_search_area_records() -> None:
    records = [
        {
            "hotel_name": "札幌温泉ホテル",
            "hotel_url": "https://www.jalan.net/yad123456/",
            "hotel_url_normalized": "/yad123456",
            "plan_name": "夕朝食付き",
            "price": 12000,
            "search_type": "area",
            "area": "SML_010202",
            "matched_name": "札幌",
        }
    ]

    actual = json.loads(serialize_search_results(records))

    assert actual[0]["search_type"] == "area"
    assert actual[0]["area"] == "SML_010202"
    assert "matched_name" not in actual[0]


def test_serialize_search_names_records() -> None:
    records = [
        {
            "hotel_name": "札幌温泉ホテル",
            "hotel_url": "https://www.jalan.net/yad123456/",
            "hotel_url_normalized": "/yad123456",
            "plan_name": "夕朝食付き",
            "price": 12000,
            "search_type": "name",
            "area": "SML_010202",
            "matched_name": "札幌",
        }
    ]

    actual = json.loads(serialize_search_results(records))

    assert actual[0]["search_type"] == "name"
    assert actual[0]["matched_name"] == "札幌"


def test_serialize_empty_records() -> None:
    assert serialize_search_results([]) == "[]"
