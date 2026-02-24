"""Typer CLI entrypoints for jalan-hotel-finder."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from pydantic import ValidationError

from jalan_hotel_finder.application.input_models import (
    MealType,
    SearchAreaInput,
    SearchNamesInput,
)
from jalan_hotel_finder.application.search_services import (
    AreaSearchFailedError,
    NameSearchFailedError,
    search_area,
    search_names_keyword_one_shot,
)
from jalan_hotel_finder.domain.name_matching import InvalidPreferredOptionError
from jalan_hotel_finder.infrastructure.area_xml_resolver import (
    list_prefecture_names,
    resolve_sml_codes_for_prefecture,
)
from jalan_hotel_finder.infrastructure.crawler import (
    CrawlFetchError,
    PlaywrightCrawler,
    PlaywrightPageFetcher,
)
from jalan_hotel_finder.output.json_formatter import (
    DEFAULT_MAX_PLANS_PER_HOTEL,
    format_search_results,
)


app = typer.Typer(help="jalan hotel finder CLI")
DEFAULT_NAMES_FILE = Path(__file__).resolve().parents[3] / "data" / "candidate_hotels.csv"


def _normalize_prefecture_options(pref: list[str] | None) -> list[str]:
    """Normalize prefecture options from repeated and comma-separated input."""
    if not pref:
        return []

    normalized: list[str] = []
    for raw_pref in pref:
        for item in raw_pref.split(","):
            value = item.strip()
            if value:
                normalized.append(value)
    return normalized


@app.command("area")
def search_area_command(
    checkin: str = typer.Option(..., "--checkin"),
    pref: list[str] | None = typer.Option(None, "--pref"),
    adults: int = typer.Option(1, "--adults"),
    nights: int = typer.Option(1, "--nights"),
    max_price: int | None = typer.Option(None, "--maxPrice"),
    meal_type: MealType | None = typer.Option(None, "--meal-type"),
    care_kakenagashi: bool = typer.Option(True, "--care-kakenagashi/--no-care-kakenagashi"),
    care_bath_rent: bool = typer.Option(False, "--care-bath-rent/--no-care-bath-rent"),
    care_private_openair: bool = typer.Option(
        False,
        "--care-private-openair/--no-care-private-openair",
    ),
    parallel: int = typer.Option(2, "--parallel"),
) -> None:
    """Run area search and print a human-readable list to stdout."""
    normalized_pref = _normalize_prefecture_options(pref)

    try:
        user_input = SearchAreaInput(
            checkin=checkin,
            pref=normalized_pref,
            adults=adults,
            nights=nights,
            max_price=max_price,
            meal_type=meal_type,
            care_kakenagashi=care_kakenagashi,
            care_bath_rent=care_bath_rent,
            care_private_openair=care_private_openair,
            parallel=parallel,
        )
    except ValidationError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    try:
        records = asyncio.run(run_search_area_service(user_input))
    except (AreaSearchFailedError, CrawlFetchError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=3) from error
    except Exception as error:  # unexpected
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(
        format_search_results(
            records,
            max_plans_per_hotel=DEFAULT_MAX_PLANS_PER_HOTEL,
        )
    )


@app.command("list")
def search_list_command(
    checkin: str = typer.Option(..., "--checkin"),
    pref: list[str] | None = typer.Option(None, "--pref"),
    adults: int = typer.Option(1, "--adults"),
    nights: int = typer.Option(1, "--nights"),
    max_price: int | None = typer.Option(None, "--maxPrice"),
    meal_type: MealType | None = typer.Option(None, "--meal-type"),
    parallel: int = typer.Option(2, "--parallel"),
) -> None:
    """Run candidate-list search and print a human-readable list to stdout."""
    normalized_pref = _normalize_prefecture_options(pref)
    effective_pref = normalized_pref or list_prefecture_names()

    try:
        user_input = SearchNamesInput(
            names_file=DEFAULT_NAMES_FILE,
            checkin=checkin,
            pref=effective_pref,
            adults=adults,
            nights=nights,
            max_price=max_price,
            meal_type=meal_type,
            parallel=parallel,
        )
    except ValidationError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    try:
        records = asyncio.run(run_search_names_service(user_input))
    except InvalidPreferredOptionError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error
    except (AreaSearchFailedError, NameSearchFailedError, CrawlFetchError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=3) from error
    except Exception as error:  # unexpected
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(
        format_search_results(
            records,
            max_plans_per_hotel=DEFAULT_MAX_PLANS_PER_HOTEL,
        )
    )


@app.command("coupon", hidden=True)
def search_coupon_command() -> None:
    """Unsupported command reserved for future release."""
    typer.echo("coupon search is not supported in v1", err=True)
    raise typer.Exit(code=2)


async def run_search_area_service(user_input: SearchAreaInput) -> list[dict]:
    """Wire production dependencies for `search area`."""
    async with PlaywrightPageFetcher(page_load_timeout_ms=30_000, headless=True) as fetcher:
        crawler = PlaywrightCrawler(
            fetcher=fetcher,
            parallel=user_input.parallel,
            area_delay_ms=100,
        )
        return await search_area(
            user_input=user_input,
            resolve_sml_codes_for_prefecture=resolve_sml_codes_for_prefecture,
            crawler=crawler,
        )


async def run_search_names_service(user_input: SearchNamesInput) -> list[dict]:
    """Wire production dependencies for `list` command."""
    async with PlaywrightPageFetcher(page_load_timeout_ms=30_000, headless=True) as fetcher:
        crawler = PlaywrightCrawler(
            fetcher=fetcher,
            parallel=user_input.parallel,
            area_delay_ms=100,
        )
        return await search_names_keyword_one_shot(
            user_input=user_input,
            crawler=crawler,
        )


def main() -> None:
    """Console script entrypoint."""
    app()


if __name__ == "__main__":
    main()
