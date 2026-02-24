from jalan_hotel_finder.output.json_formatter import (
    format_search_results,
    serialize_search_results,
)


def test_formats_search_area_records_as_human_readable_list() -> None:
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

    actual = serialize_search_results(records)

    assert "検索結果: 1件" in actual
    assert "[1] 宿名: 札幌温泉ホテル" in actual
    assert "URL: https://www.jalan.net/yad123456/" in actual
    assert "  - プラン1: 夕朝食付き / 12,000円" in actual
    assert "matched_name" not in actual
    assert "search_type" not in actual
    assert "area" not in actual


def test_formats_none_price_as_unavailable() -> None:
    records = [
        {
            "hotel_name": "函館シティホテル",
            "hotel_url": "https://www.jalan.net/yad222222/",
            "hotel_url_normalized": "/yad222222",
            "plan_name": "素泊まり",
            "price": None,
        }
    ]

    actual = serialize_search_results(records)

    assert "  - プラン1: 素泊まり / 価格未取得" in actual


def test_limits_plans_to_three_per_hotel_in_recommendation_order() -> None:
    records = [
        {
            "hotel_name": "札幌温泉ホテル",
            "hotel_url": f"https://www.jalan.net/yad123456/?plan={index}",
            "hotel_url_normalized": "/yad123456",
            "plan_name": f"プラン{index}",
            "price": 9000 + (index * 1000),
        }
        for index in range(1, 7)
    ]

    actual = format_search_results(records)

    plan1 = "  - プラン1: プラン1 / 10,000円"
    plan2 = "  - プラン2: プラン2 / 11,000円"
    plan3 = "  - プラン3: プラン3 / 12,000円"
    assert plan1 in actual
    assert plan2 in actual
    assert plan3 in actual
    assert "プラン4" not in actual
    assert "プラン5" not in actual
    assert "プラン6" not in actual
    assert actual.index(plan1) < actual.index(plan2)
    assert actual.index(plan2) < actual.index(plan3)


def test_shows_message_when_no_records() -> None:
    assert serialize_search_results([]) == "該当する宿はありませんでした。"
