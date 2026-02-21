"""Typer CLI entrypoints for jalan-hotel-finder."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from pydantic import ValidationError

from jalan_hotel_finder.application.input_models import (
    KeywordEncoding,
    MealType,
    SearchAreaInput,
    SearchNamesInput,
)
from jalan_hotel_finder.application.search_services import (
    AreaSearchFailedError,
    search_area,
    search_names_local_filter,
)
from jalan_hotel_finder.infrastructure.area_xml_resolver import (
    list_prefecture_names,
    resolve_sml_codes_for_prefecture,
)
from jalan_hotel_finder.infrastructure.crawler import (
    CrawlFetchError,
    PlaywrightCrawler,
    PlaywrightPageFetcher,
)
from jalan_hotel_finder.output.json_formatter import serialize_search_results


app = typer.Typer(help="jalan hotel finder CLI")
search_app = typer.Typer(help="search commands")
app.add_typer(search_app, name="search")
DEFAULT_NAMES_FILE = Path(__file__).resolve().parents[3] / "data" / "candidate_hotels.csv"


@search_app.command("area")
def search_area_command(
    checkin: str = typer.Option(..., "--checkin"),
    pref: list[str] | None = typer.Option(None, "--pref"),
    adults: int = typer.Option(1, "--adults"),
    nights: int = typer.Option(1, "--nights"),
    meal_type: MealType = typer.Option(MealType.TWO_MEALS, "--meal-type"),
    care_kakenagashi: bool = typer.Option(True, "--care-kakenagashi/--no-care-kakenagashi"),
    care_bath_rent: bool = typer.Option(False, "--care-bath-rent/--no-care-bath-rent"),
    care_private_openair: bool = typer.Option(
        False,
        "--care-private-openair/--no-care-private-openair",
    ),
    parallel: int = typer.Option(2, "--parallel"),
) -> None:
    """Run area search and print JSON to stdout."""
    try:
        user_input = SearchAreaInput(
            checkin=checkin,
            pref=pref or [],
            adults=adults,
            nights=nights,
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

    typer.echo(serialize_search_results(records))


@search_app.command("names")
def search_names_command(
    names_file: str | None = typer.Option(None, "--names-file"),
    keyword_encoding: KeywordEncoding = typer.Option(KeywordEncoding.CP932, "--keyword-encoding"),
    checkin: str = typer.Option(..., "--checkin"),
    pref: list[str] | None = typer.Option(None, "--pref"),
    adults: int = typer.Option(1, "--adults"),
    nights: int = typer.Option(1, "--nights"),
    meal_type: MealType = typer.Option(MealType.TWO_MEALS, "--meal-type"),
    parallel: int = typer.Option(2, "--parallel"),
) -> None:
    """Run names search (local-filter mode) and print JSON to stdout."""
    effective_names_file = names_file or str(DEFAULT_NAMES_FILE)
    effective_pref = pref or list_prefecture_names()

    try:
        user_input = SearchNamesInput(
            names_file=effective_names_file,
            keyword_encoding=keyword_encoding,
            checkin=checkin,
            pref=effective_pref,
            adults=adults,
            nights=nights,
            meal_type=meal_type,
            parallel=parallel,
        )
    except ValidationError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    try:
        records = asyncio.run(run_search_names_service(user_input))
    except (AreaSearchFailedError, CrawlFetchError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=3) from error
    except Exception as error:  # unexpected
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(serialize_search_results(records))


@search_app.command("coupon", hidden=True)
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
            area_delay_ms=1_000,
        )
        return await search_area(
            user_input=user_input,
            resolve_sml_codes_for_prefecture=resolve_sml_codes_for_prefecture,
            crawler=crawler,
        )


async def run_search_names_service(user_input: SearchNamesInput) -> list[dict]:
    """Wire production dependencies for `search names`."""
    async with PlaywrightPageFetcher(page_load_timeout_ms=30_000, headless=True) as fetcher:
        crawler = PlaywrightCrawler(
            fetcher=fetcher,
            parallel=user_input.parallel,
            area_delay_ms=1_000,
        )
        return await search_names_local_filter(
            user_input=user_input,
            resolve_sml_codes_for_prefecture=resolve_sml_codes_for_prefecture,
            crawler=crawler,
        )


def main() -> None:
    """Console script entrypoint."""
    app()
