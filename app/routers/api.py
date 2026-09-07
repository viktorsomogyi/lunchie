from fastapi import APIRouter, HTTPException

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


def _recipe_payload(recipe) -> dict | None:
    if recipe is None:
        return None
    return recipe.to_dict(include_ingredients=True)


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
