import csv
import io
import re
import unicodedata
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from app.db import db_session
from app.menu import (
    attach_dates,
    generate_menu,
    get_or_create_week_menu,
    get_recipe,
    list_recipes,
    today_menu_item,
)

router = APIRouter(prefix="/api")

_CSV_FIELDS = (
    "name",
    "amount",
    "unit",
    "product_link",
    "energy_kcal",
    "protein_g",
    "carbohydrates_g",
    "fats_g",
    "salt_g",
    "fiber_g",
)


def _recipe_payload(recipe) -> dict | None:
    if recipe is None:
        return None
    return recipe.to_dict(include_ingredients=True)


def _safe_filename(name: str) -> str:
    # ASCII-only so Content-Disposition stays valid in every browser
    # (Opera chokes on raw non-ASCII filenames, e.g. Hungarian accents).
    normalized = unicodedata.normalize("NFKD", name.strip())
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9\-]+", "_", ascii_name)
    cleaned = cleaned.strip("_") or "recipe"
    return cleaned[:80]


def _content_disposition(filename: str) -> str:
    # RFC 6266 + RFC 5987: ASCII fallback plus percent-encoded UTF-8 name.
    return f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'


def _ingredient_rows(recipe) -> list[dict]:
    rows = []
    for item in recipe.ingredients:
        data = item.to_dict()
        rows.append({field: data.get(field, "") for field in _CSV_FIELDS})
    return rows


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/menu/today")
def menu_today():
    with db_session() as conn:
        item = today_menu_item(conn)
    if item is None:
        return {"date": None, "day": None, "recipe": None}
    recipe = item["recipe"]
    return {
        "date": item["date"],
        "day": item["day_index"],
        "recipe": _recipe_payload(recipe),
    }


@router.get("/menu/current")
def menu_current():
    with db_session() as conn:
        menu = attach_dates(get_or_create_week_menu(conn))
    return {
        "week_start": menu["week_start"],
        "week_length": menu["week_length"],
        "generated_at": menu["generated_at"],
        "days": [
            {
                "day_index": d["day_index"],
                "date": d["date"],
                "recipe": _recipe_payload(d["recipe"]),
            }
            for d in menu["days"]
        ],
    }


@router.post("/menu/regenerate")
def menu_regenerate():
    with db_session() as conn:
        menu = attach_dates(generate_menu(conn))
    return {
        "week_start": menu["week_start"],
        "week_length": menu["week_length"],
        "generated_at": menu["generated_at"],
        "days": [
            {
                "day_index": d["day_index"],
                "date": d["date"],
                "recipe": _recipe_payload(d["recipe"]),
            }
            for d in menu["days"]
        ],
    }


@router.get("/recipes")
def recipes_list():
    with db_session() as conn:
        recipes = list_recipes(conn)
    return [_recipe_payload(r) for r in recipes]


@router.get("/recipes/{recipe_id}")
def recipes_get(recipe_id: int):
    with db_session() as conn:
        recipe = get_recipe(conn, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _recipe_payload(recipe)


@router.get("/recipes/{recipe_id}/ingredients.json")
def recipe_ingredients_json(recipe_id: int):
    with db_session() as conn:
        recipe = get_recipe(conn, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    filename = f"{_safe_filename(recipe.name)}_ingredients.json"
    payload = {
        "recipe_id": recipe.id,
        "recipe_name": recipe.name,
        "serves": recipe.serves,
        "ingredients": _ingredient_rows(recipe),
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/recipes/{recipe_id}/ingredients.csv")
def recipe_ingredients_csv(recipe_id: int):
    with db_session() as conn:
        recipe = get_recipe(conn, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in _ingredient_rows(recipe):
        writer.writerow(row)
    filename = f"{_safe_filename(recipe.name)}_ingredients.csv"
    # BOM so spreadsheet apps detect UTF-8 (Hungarian accents); bytes body
    # instead of str-chunked StreamingResponse, which Opera mishandles.
    content = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(filename)},
    )
