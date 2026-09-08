import sqlite3
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import UNITS, db_session, get_setting, set_setting
from app.i18n import SUPPORTED_LANGUAGES, get_language, make_translator
from app.menu import (
    attach_dates,
    generate_menu,
    get_food_item,
    get_or_create_week_menu,
    get_recipe,
    list_food_items,
    list_recipes,
    search_recipes,
    set_day_recipe,
    week_length,
)
from app.models import (
    NUTRITION_MODE_INGREDIENT,
    NUTRITION_MODE_RECIPE,
    FoodItem,
    Recipe,
    RecipeItem,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def format_number(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "" if value is None else str(value)
    if n.is_integer():
        return str(int(n))
    return f"{n:g}"


templates.env.filters["num"] = format_number


def render(request: Request, name: str, context: dict, status_code: int = 200):
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def _lang(conn) -> str:
    return get_language(get_setting(conn, "ui_language", "en"))


def _ctx(request: Request, conn, **extra):
    lang = _lang(conn)
    t = make_translator(lang)
    ctx = {
        "request": request,
        "lang": lang,
        "t": t,
        "units": UNITS,
        "supported_languages": SUPPORTED_LANGUAGES,
    }
    ctx.update(extra)
    return ctx


def _form_str(form, key: str) -> str:
    value = form.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _parse_list(form, key: str) -> list:
    values = form.getlist(key)
    return list(values) if values else []


def _float_field(value: str | None, default: float = 0.0) -> float:
    try:
        n = float(value) if value not in (None, "") else default
    except ValueError:
        n = default
    return n if n >= 0 else 0.0


def _int_field(value: str | None, default: int = 0, minimum: int | None = None) -> int:
    try:
        n = int(value) if value not in (None, "") else default
    except ValueError:
        n = default
    if minimum is not None and n < minimum:
        n = minimum
    return n


def _nutrition_mode_from_form(form) -> str:
    mode = _form_str(form, "nutrition_mode")
    return NUTRITION_MODE_INGREDIENT if mode == NUTRITION_MODE_INGREDIENT else NUTRITION_MODE_RECIPE


def _parse_recipe_items(form, conn) -> list[RecipeItem]:
    food_ids = _parse_list(form, "food_item_id")
    amounts = _parse_list(form, "ingredient_amount")
    units = _parse_list(form, "ingredient_unit")
    items: list[RecipeItem] = []
    for index, raw_id in enumerate(food_ids):
        try:
            food_item_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        food = get_food_item(conn, food_item_id)
        if food is None:
            continue
        amount = amounts[index] if index < len(amounts) else 0
        unit = units[index] if index < len(units) else food.base_unit
        unit = str(unit) if unit in UNITS else food.base_unit
        items.append(
            RecipeItem(
                food_item_id=food.id,
                food_item=food,
                amount=_float_field(amount),
                unit=unit,
            )
        )
    return items


def _save_recipe_items(conn, recipe_id: int, items: list[RecipeItem]) -> None:
    conn.execute("DELETE FROM recipe_items WHERE recipe_id = ?", (recipe_id,))
    for item in items:
        if not item.food_item_id:
            continue
        conn.execute(
            """
            INSERT INTO recipe_items (recipe_id, food_item_id, amount, unit)
            VALUES (?, ?, ?, ?)
            """,
            (recipe_id, item.food_item_id, item.amount, item.unit),
        )


def _recipe_from_form(form, conn, recipe_id: int | None = None) -> tuple[Recipe, list[RecipeItem]]:
    items = _parse_recipe_items(form, conn)
    recipe = Recipe(
        id=recipe_id,
        name=_form_str(form, "name"),
        instructions=_form_str(form, "instructions"),
        serves=_int_field(_form_str(form, "serves"), 1, minimum=1),
        prep_time_minutes=_int_field(_form_str(form, "prep_time_minutes"), 0, minimum=0),
        energy_kcal=_float_field(_form_str(form, "energy_kcal")),
        protein_g=_float_field(_form_str(form, "protein_g")),
        carbohydrates_g=_float_field(_form_str(form, "carbohydrates_g")),
        fats_g=_float_field(_form_str(form, "fats_g")),
        salt_g=_float_field(_form_str(form, "salt_g")),
        fiber_g=_float_field(_form_str(form, "fiber_g")),
        nutrition_mode=_nutrition_mode_from_form(form),
        ingredients=items,
    )
    if recipe.uses_ingredient_nutrition:
        recipe.apply_per_person_nutrition()
    return recipe, items


def _food_from_form(form, food_id: int | None = None) -> FoodItem:
    unit = _form_str(form, "base_unit")
    if unit not in UNITS:
        unit = "g"
    return FoodItem(
        id=food_id,
        name=_form_str(form, "name"),
        base_amount=_float_field(_form_str(form, "base_amount"), 100) or 100,
        base_unit=unit,
        energy_kcal=_float_field(_form_str(form, "energy_kcal")),
        protein_g=_float_field(_form_str(form, "protein_g")),
        carbohydrates_g=_float_field(_form_str(form, "carbohydrates_g")),
        fats_g=_float_field(_form_str(form, "fats_g")),
        salt_g=_float_field(_form_str(form, "salt_g")),
        fiber_g=_float_field(_form_str(form, "fiber_g")),
        product_link=_form_str(form, "product_link"),
    )


def _find_recipe_by_name(conn, name: str, exclude_id: int | None = None):
    if exclude_id is None:
        return conn.execute(
            "SELECT id FROM recipes WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
    return conn.execute(
        "SELECT id FROM recipes WHERE name = ? COLLATE NOCASE AND id != ?",
        (name, exclude_id),
    ).fetchone()


def _find_food_by_name(conn, name: str, exclude_id: int | None = None):
    if exclude_id is None:
        return conn.execute(
            "SELECT id FROM food_items WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
    return conn.execute(
        "SELECT id FROM food_items WHERE name = ? COLLATE NOCASE AND id != ?",
        (name, exclude_id),
    ).fetchone()


def _blank_recipe_item(food_items: list[FoodItem]) -> RecipeItem:
    food = food_items[0] if food_items else None
    return RecipeItem(
        amount=0,
        unit=food.base_unit if food else "g",
        food_item=food,
        food_item_id=food.id if food else None,
    )


@router.get("/", response_class=HTMLResponse)
def user_week(request: Request):
    with db_session() as conn:
        recipes = list_recipes(conn)
        menu = attach_dates(get_or_create_week_menu(conn)) if recipes else None
        today = date.today().isoformat()
        return render(
            request,
            "user/week.html",
            _ctx(request, conn, menu=menu, today=today, has_recipes=bool(recipes)),
        )


@router.get("/recipes/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(request: Request, recipe_id: int):
    with db_session() as conn:
        recipe = get_recipe(conn, recipe_id)
        if recipe is None:
            return HTMLResponse("Not found", status_code=404)
        partial = request.headers.get("HX-Request") == "true"
        template = "user/recipe_modal.html" if partial else "user/recipe_detail.html"
        return render(request, template, _ctx(request, conn, recipe=recipe))


@router.post("/menu/regenerate")
def regenerate_menu():
    with db_session() as conn:
        recipes = list_recipes(conn)
        if recipes:
            generate_menu(conn)
    return RedirectResponse(url="/", status_code=303)


def _picker_context(request: Request, conn, day_index: int, query: str = ""):
    length = week_length(conn)
    if day_index < 0 or day_index >= length:
        return None
    menu = attach_dates(get_or_create_week_menu(conn))
    current = next((d for d in menu["days"] if d["day_index"] == day_index), None)
    current_id = current["recipe"].id if current and current["recipe"] else None
    recipes = search_recipes(conn, query)
    ctx = _ctx(
        request,
        conn,
        day_index=day_index,
        query=query,
        recipes=recipes,
        current_recipe_id=current_id,
    )
    ctx["day_name"] = ctx["t"](f"days.{day_index}")
    return ctx


@router.get("/menu/days/{day_index}/picker", response_class=HTMLResponse)
def day_picker(request: Request, day_index: int, q: str = ""):
    with db_session() as conn:
        ctx = _picker_context(request, conn, day_index, q)
        if ctx is None:
            return HTMLResponse("Not found", status_code=404)
        return render(request, "user/recipe_picker.html", ctx)


@router.get("/menu/days/{day_index}/picker/results", response_class=HTMLResponse)
def day_picker_results(request: Request, day_index: int, q: str = ""):
    with db_session() as conn:
        ctx = _picker_context(request, conn, day_index, q)
        if ctx is None:
            return HTMLResponse("Not found", status_code=404)
        return render(request, "user/recipe_picker_results.html", ctx)


@router.post("/menu/days/{day_index}")
def assign_day_recipe(day_index: int, recipe_id: Annotated[int, Form()]):
    with db_session() as conn:
        try:
            set_day_recipe(conn, day_index, recipe_id)
        except ValueError:
            return HTMLResponse("Not found", status_code=404)
    return RedirectResponse(url="/", status_code=303)


@router.get("/admin", response_class=HTMLResponse)
@router.get("/admin/recipes", response_class=HTMLResponse)
def admin_recipes(request: Request):
    with db_session() as conn:
        recipes = list_recipes(conn)
        return render(request, "admin/recipes.html", _ctx(request, conn, recipes=recipes))


@router.get("/admin/recipes/new", response_class=HTMLResponse)
def admin_recipe_new(request: Request):
    with db_session() as conn:
        food_items = list_food_items(conn)
        recipe = Recipe(
            name="",
            nutrition_mode=NUTRITION_MODE_INGREDIENT if food_items else NUTRITION_MODE_RECIPE,
            ingredients=[_blank_recipe_item(food_items)] if food_items else [],
        )
        return render(
            request,
            "admin/recipe_form.html",
            _ctx(
                request,
                conn,
                recipe=recipe,
                food_items=food_items,
                editing=False,
                error=None,
            ),
        )


@router.post("/admin/recipes", response_class=HTMLResponse)
async def admin_recipe_create(request: Request):
    form = await request.form()
    with db_session() as conn:
        food_items = list_food_items(conn)
        recipe, items = _recipe_from_form(form, conn)
        if not recipe.ingredients and food_items:
            recipe.ingredients = [_blank_recipe_item(food_items)]
        if not recipe.name:
            return render(
                request,
                "admin/recipe_form.html",
                _ctx(request, conn, recipe=recipe, food_items=food_items, editing=False, error="name"),
                status_code=400,
            )
        if _find_recipe_by_name(conn, recipe.name):
            return render(
                request,
                "admin/recipe_form.html",
                _ctx(request, conn, recipe=recipe, food_items=food_items, editing=False, error="duplicate"),
                status_code=400,
            )
        try:
            cur = conn.execute(
                """
                INSERT INTO recipes (
                    name, instructions, serves, prep_time_minutes,
                    energy_kcal, protein_g, carbohydrates_g, fats_g, salt_g, fiber_g,
                    nutrition_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe.name,
                    recipe.instructions,
                    recipe.serves,
                    recipe.prep_time_minutes,
                    recipe.energy_kcal,
                    recipe.protein_g,
                    recipe.carbohydrates_g,
                    recipe.fats_g,
                    recipe.salt_g,
                    recipe.fiber_g,
                    recipe.nutrition_mode,
                ),
            )
            _save_recipe_items(conn, cur.lastrowid, items)
        except sqlite3.IntegrityError:
            return render(
                request,
                "admin/recipe_form.html",
                _ctx(request, conn, recipe=recipe, food_items=food_items, editing=False, error="duplicate"),
                status_code=400,
            )
    return RedirectResponse(url="/admin/recipes", status_code=303)


@router.get("/admin/recipes/{recipe_id}/edit", response_class=HTMLResponse)
def admin_recipe_edit(request: Request, recipe_id: int):
    with db_session() as conn:
        recipe = get_recipe(conn, recipe_id)
        if recipe is None:
            return HTMLResponse("Not found", status_code=404)
        food_items = list_food_items(conn)
        if not recipe.ingredients and food_items:
            recipe.ingredients = [_blank_recipe_item(food_items)]
        return render(
            request,
            "admin/recipe_form.html",
            _ctx(
                request,
                conn,
                recipe=recipe,
                food_items=food_items,
                editing=True,
                error=None,
            ),
        )


@router.post("/admin/recipes/{recipe_id}", response_class=HTMLResponse)
async def admin_recipe_update(request: Request, recipe_id: int):
    form = await request.form()
    with db_session() as conn:
        existing = get_recipe(conn, recipe_id)
        if existing is None:
            return HTMLResponse("Not found", status_code=404)
        food_items = list_food_items(conn)
        recipe, items = _recipe_from_form(form, conn, recipe_id)
        if not recipe.ingredients and food_items:
            recipe.ingredients = [_blank_recipe_item(food_items)]
        if not recipe.name:
            return render(
                request,
                "admin/recipe_form.html",
                _ctx(request, conn, recipe=recipe, food_items=food_items, editing=True, error="name"),
                status_code=400,
            )
        if _find_recipe_by_name(conn, recipe.name, exclude_id=recipe_id):
            return render(
                request,
                "admin/recipe_form.html",
                _ctx(request, conn, recipe=recipe, food_items=food_items, editing=True, error="duplicate"),
                status_code=400,
            )
        try:
            conn.execute(
                """
                UPDATE recipes SET
                    name = ?, instructions = ?, serves = ?, prep_time_minutes = ?,
                    energy_kcal = ?, protein_g = ?, carbohydrates_g = ?, fats_g = ?, salt_g = ?, fiber_g = ?,
                    nutrition_mode = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    recipe.name,
                    recipe.instructions,
                    recipe.serves,
                    recipe.prep_time_minutes,
                    recipe.energy_kcal,
                    recipe.protein_g,
                    recipe.carbohydrates_g,
                    recipe.fats_g,
                    recipe.salt_g,
                    recipe.fiber_g,
                    recipe.nutrition_mode,
                    recipe_id,
                ),
            )
            _save_recipe_items(conn, recipe_id, items)
        except sqlite3.IntegrityError:
            return render(
                request,
                "admin/recipe_form.html",
                _ctx(request, conn, recipe=recipe, food_items=food_items, editing=True, error="duplicate"),
                status_code=400,
            )
    return RedirectResponse(url="/admin/recipes", status_code=303)


@router.post("/admin/recipes/{recipe_id}/delete")
def admin_recipe_delete(recipe_id: int):
    with db_session() as conn:
        conn.execute("DELETE FROM menu_items WHERE recipe_id = ?", (recipe_id,))
        conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    return RedirectResponse(url="/admin/recipes", status_code=303)


@router.get("/admin/ingredients/row", response_class=HTMLResponse)
def ingredient_row(request: Request, nutrition_mode: str = NUTRITION_MODE_INGREDIENT):
    mode = NUTRITION_MODE_INGREDIENT if nutrition_mode == NUTRITION_MODE_INGREDIENT else NUTRITION_MODE_RECIPE
    with db_session() as conn:
        food_items = list_food_items(conn)
        return render(
            request,
            "admin/ingredient_row.html",
            _ctx(
                request,
                conn,
                ingredient=_blank_recipe_item(food_items),
                food_items=food_items,
                recipe=Recipe(name="", nutrition_mode=mode),
            ),
        )


@router.get("/admin/food-items", response_class=HTMLResponse)
def admin_food_items(request: Request):
    with db_session() as conn:
        food_items = list_food_items(conn)
        return render(
            request,
            "admin/food_items.html",
            _ctx(request, conn, food_items=food_items),
        )


@router.get("/admin/food-items/new", response_class=HTMLResponse)
def admin_food_new(request: Request):
    food = FoodItem(name="", base_amount=100, base_unit="g")
    with db_session() as conn:
        return render(
            request,
            "admin/food_item_form.html",
            _ctx(request, conn, food=food, editing=False, error=None),
        )


@router.post("/admin/food-items", response_class=HTMLResponse)
async def admin_food_create(request: Request):
    form = await request.form()
    food = _food_from_form(form)
    with db_session() as conn:
        if not food.name:
            return render(
                request,
                "admin/food_item_form.html",
                _ctx(request, conn, food=food, editing=False, error="name"),
                status_code=400,
            )
        if food.base_amount <= 0:
            return render(
                request,
                "admin/food_item_form.html",
                _ctx(request, conn, food=food, editing=False, error="base_amount"),
                status_code=400,
            )
        if _find_food_by_name(conn, food.name):
            return render(
                request,
                "admin/food_item_form.html",
                _ctx(request, conn, food=food, editing=False, error="duplicate"),
                status_code=400,
            )
        try:
            conn.execute(
                """
                INSERT INTO food_items (
                    name, base_amount, base_unit,
                    energy_kcal, protein_g, carbohydrates_g, fats_g, salt_g, fiber_g,
                    product_link
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    food.name,
                    food.base_amount,
                    food.base_unit,
                    food.energy_kcal,
                    food.protein_g,
                    food.carbohydrates_g,
                    food.fats_g,
                    food.salt_g,
                    food.fiber_g,
                    food.product_link,
                ),
            )
        except sqlite3.IntegrityError:
            return render(
                request,
                "admin/food_item_form.html",
                _ctx(request, conn, food=food, editing=False, error="duplicate"),
                status_code=400,
            )
    return RedirectResponse(url="/admin/food-items", status_code=303)


@router.get("/admin/food-items/{food_id}/edit", response_class=HTMLResponse)
def admin_food_edit(request: Request, food_id: int):
    with db_session() as conn:
        food = get_food_item(conn, food_id)
        if food is None:
            return HTMLResponse("Not found", status_code=404)
        return render(
            request,
            "admin/food_item_form.html",
            _ctx(request, conn, food=food, editing=True, error=None),
        )


@router.post("/admin/food-items/{food_id}", response_class=HTMLResponse)
async def admin_food_update(request: Request, food_id: int):
    form = await request.form()
    food = _food_from_form(form, food_id)
    with db_session() as conn:
        existing = get_food_item(conn, food_id)
        if existing is None:
            return HTMLResponse("Not found", status_code=404)
        if not food.name:
            return render(
                request,
                "admin/food_item_form.html",
                _ctx(request, conn, food=food, editing=True, error="name"),
                status_code=400,
            )
        if food.base_amount <= 0:
            return render(
                request,
                "admin/food_item_form.html",
                _ctx(request, conn, food=food, editing=True, error="base_amount"),
                status_code=400,
            )
        if _find_food_by_name(conn, food.name, exclude_id=food_id):
            return render(
                request,
                "admin/food_item_form.html",
                _ctx(request, conn, food=food, editing=True, error="duplicate"),
                status_code=400,
            )
        try:
            conn.execute(
                """
                UPDATE food_items SET
                    name = ?, base_amount = ?, base_unit = ?,
                    energy_kcal = ?, protein_g = ?, carbohydrates_g = ?, fats_g = ?, salt_g = ?, fiber_g = ?,
                    product_link = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    food.name,
                    food.base_amount,
                    food.base_unit,
                    food.energy_kcal,
                    food.protein_g,
                    food.carbohydrates_g,
                    food.fats_g,
                    food.salt_g,
                    food.fiber_g,
                    food.product_link,
                    food_id,
                ),
            )
        except sqlite3.IntegrityError:
            return render(
                request,
                "admin/food_item_form.html",
                _ctx(request, conn, food=food, editing=True, error="duplicate"),
                status_code=400,
            )
    return RedirectResponse(url="/admin/food-items", status_code=303)


@router.post("/admin/food-items/{food_id}/delete")
def admin_food_delete(food_id: int):
    with db_session() as conn:
        used = conn.execute(
            "SELECT COUNT(*) AS n FROM recipe_items WHERE food_item_id = ?",
            (food_id,),
        ).fetchone()["n"]
        if used:
            return RedirectResponse(url="/admin/food-items?error=in_use", status_code=303)
        conn.execute("DELETE FROM food_items WHERE id = ?", (food_id,))
    return RedirectResponse(url="/admin/food-items", status_code=303)


@router.get("/admin/settings", response_class=HTMLResponse)
def admin_settings(request: Request, saved: int = 0):
    with db_session() as conn:
        week_length_value = get_setting(conn, "week_length", "5")
        ui_language = get_setting(conn, "ui_language", "en")
        return render(
            request,
            "admin/settings.html",
            _ctx(
                request,
                conn,
                week_length=week_length_value,
                ui_language=ui_language,
                saved=bool(saved),
            ),
        )


@router.post("/admin/settings")
async def admin_settings_save(
    week_length: Annotated[str, Form()] = "5",
    ui_language: Annotated[str, Form()] = "en",
):
    length = "7" if week_length == "7" else "5"
    lang = get_language(ui_language)
    with db_session() as conn:
        set_setting(conn, "week_length", length)
        set_setting(conn, "ui_language", lang)
    return RedirectResponse(url="/admin/settings?saved=1", status_code=303)
