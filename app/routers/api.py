import csv
import io
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

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
    "calories_kcal",
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
    cleaned = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("_") or "recipe"
    return cleaned[:80]


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
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/recipes/{recipe_id}/ingredients.csv")
def recipe_ingredients_csv(recipe_id: int):
    with db_session() as conn:
        recipe = get_recipe(conn, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in _ingredient_rows(recipe):
        writer.writerow(row)
    buffer.seek(0)
    filename = f"{_safe_filename(recipe.name)}_ingredients.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
