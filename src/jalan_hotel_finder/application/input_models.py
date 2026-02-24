"""Input models and validation for CLI use cases."""

from datetime import date
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class MealType(StrEnum):
    """CLI meal type enum."""

    NONE = "none"
    BREAKFAST = "breakfast"
    DINNER = "dinner"
    TWO_MEALS = "two_meals"


class KeywordEncoding(StrEnum):
    """Keyword encoding option for `list` keyword mode."""

    AUTO = "auto"
    UTF8 = "utf8"
    CP932 = "cp932"


class SearchAreaInput(BaseModel):
    """Validated input for `area`."""

    checkin: date
    pref: list[str] = Field(default_factory=list)
    adults: int = Field(default=1, ge=1)
    nights: int = Field(default=1, ge=1)
    max_price: int | None = Field(default=None, ge=0)
    meal_type: MealType | None = None
    care_kakenagashi: bool = True
    care_bath_rent: bool = False
    care_private_openair: bool = False
    parallel: int = Field(default=2, ge=1, le=10)


class SearchNamesInput(BaseModel):
    """Validated input for `list`."""

    names_file: Path
    keyword_encoding: KeywordEncoding = KeywordEncoding.CP932
    checkin: date
    pref: list[str] = Field(min_length=1)
    adults: int = Field(default=1, ge=1)
    nights: int = Field(default=1, ge=1)
    max_price: int | None = Field(default=None, ge=0)
    meal_type: MealType | None = None
    parallel: int = Field(default=2, ge=1, le=10)
