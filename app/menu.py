import random
from datetime import date, timedelta

from app.db import get_setting
from app.models import Ingredient, Recipe, ingredient_from_row, recipe_from_row


def current_week_start(today: date | None = None) -> date:
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def week_length(conn) -> int:
    raw = get_setting(conn, "week_length", "5") or "5"
    try:
        value = int(raw)
    except ValueError:
        value = 5
    return 7 if value == 7 else 5


def list_recipe_ids(conn) -> list[int]:
    rows = conn.execute("SELECT id FROM recipes ORDER BY id").fetchall()
    return [row["id"] for row in rows]


def pick_recipe_ids(recipe_ids: list[int], count: int) -> list[int]:
    if not recipe_ids:
        return []
    pool = list(recipe_ids)
    random.shuffle(pool)
    result: list[int] = []
    while len(result) < count:
        if not pool:
            pool = list(recipe_ids)
            random.shuffle(pool)
        result.append(pool.pop())
    return result


def get_ingredients(conn, recipe_id: int) -> list[Ingredient]:
    rows = conn.execute(
        "SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY id",
        (recipe_id,),
    ).fetchall()
    return [ingredient_from_row(r) for r in rows]


def get_recipe(conn, recipe_id: int, with_ingredients: bool = True) -> Recipe | None:
    row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        return None
    ingredients = get_ingredients(conn, recipe_id) if with_ingredients else []
    return recipe_from_row(row, ingredients)


def list_recipes(conn) -> list[Recipe]:
    rows = conn.execute("SELECT * FROM recipes ORDER BY name COLLATE NOCASE").fetchall()
    return [recipe_from_row(r, get_ingredients(conn, r["id"])) for r in rows]


def _like_pattern(query: str) -> str:
    escaped = query.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escaped}%"


def search_recipes(conn, query: str = "") -> list[Recipe]:
    q = (query or "").strip()
    if not q:
        return list_recipes(conn)
    rows = conn.execute(
        """
        SELECT * FROM recipes
        WHERE name LIKE ? ESCAPE '!' COLLATE NOCASE
        ORDER BY name COLLATE NOCASE
        """,
        (_like_pattern(q),),
    ).fetchall()
    return [recipe_from_row(r, get_ingredients(conn, r["id"])) for r in rows]


def set_day_recipe(conn, day_index: int, recipe_id: int, week_start: date | None = None) -> dict:
    menu = get_or_create_week_menu(conn, week_start)
    if day_index < 0 or day_index >= menu["week_length"]:
        raise ValueError("invalid day")
    recipe = get_recipe(conn, recipe_id, with_ingredients=False)
    if recipe is None:
        raise ValueError("recipe not found")
    existing = conn.execute(
        "SELECT id FROM menu_items WHERE weekly_menu_id = ? AND day_index = ?",
        (menu["id"], day_index),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE menu_items SET recipe_id = ? WHERE id = ?",
            (recipe_id, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO menu_items (weekly_menu_id, day_index, recipe_id) VALUES (?, ?, ?)",
            (menu["id"], day_index, recipe_id),
        )
    return attach_dates(get_or_create_week_menu(conn, week_start))


def get_or_create_week_menu(conn, week_start: date | None = None) -> dict:
    start = week_start or current_week_start()
    start_str = start.isoformat()
    length = week_length(conn)
    row = conn.execute(
        "SELECT * FROM weekly_menus WHERE week_start = ?",
        (start_str,),
    ).fetchone()
    if row is None:
        return generate_menu(conn, start)
    items = _load_menu_items(conn, row["id"], length)
    return {
        "id": row["id"],
        "week_start": start_str,
        "generated_at": row["generated_at"],
        "week_length": length,
        "days": items,
    }


def generate_menu(conn, week_start: date | None = None) -> dict:
    start = week_start or current_week_start()
    start_str = start.isoformat()
    length = week_length(conn)
    recipe_ids = list_recipe_ids(conn)

    existing = conn.execute(
        "SELECT id FROM weekly_menus WHERE week_start = ?",
        (start_str,),
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM weekly_menus WHERE id = ?", (existing["id"],))

    if not recipe_ids:
        cur = conn.execute(
            "INSERT INTO weekly_menus (week_start) VALUES (?)",
            (start_str,),
        )
        menu_id = cur.lastrowid
        row = conn.execute("SELECT * FROM weekly_menus WHERE id = ?", (menu_id,)).fetchone()
        return {
            "id": menu_id,
            "week_start": start_str,
            "generated_at": row["generated_at"],
            "week_length": length,
            "days": [],
        }

    chosen = pick_recipe_ids(recipe_ids, length)
    cur = conn.execute(
        "INSERT INTO weekly_menus (week_start) VALUES (?)",
        (start_str,),
    )
    menu_id = cur.lastrowid
    for day_index, recipe_id in enumerate(chosen):
        conn.execute(
            "INSERT INTO menu_items (weekly_menu_id, day_index, recipe_id) VALUES (?, ?, ?)",
            (menu_id, day_index, recipe_id),
        )
    row = conn.execute("SELECT * FROM weekly_menus WHERE id = ?", (menu_id,)).fetchone()
    return {
        "id": menu_id,
        "week_start": start_str,
        "generated_at": row["generated_at"],
        "week_length": length,
        "days": _load_menu_items(conn, menu_id, length),
    }


def _load_menu_items(conn, menu_id: int, length: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT mi.day_index, r.*
        FROM menu_items mi
        JOIN recipes r ON r.id = mi.recipe_id
        WHERE mi.weekly_menu_id = ?
        ORDER BY mi.day_index
        """,
        (menu_id,),
    ).fetchall()
    days: list[dict] = []
    for row in rows:
        if row["day_index"] >= length:
            continue
        recipe = recipe_from_row(row, get_ingredients(conn, row["id"]))
        days.append(
            {
                "day_index": row["day_index"],
                "date": None,
                "recipe": recipe,
            }
        )
    return days


def attach_dates(menu: dict) -> dict:
    start = date.fromisoformat(menu["week_start"])
    by_index = {d["day_index"]: d for d in menu["days"]}
    days: list[dict] = []
    for i in range(menu["week_length"]):
        day_date = (start + timedelta(days=i)).isoformat()
        existing = by_index.get(i)
        if existing:
            existing["date"] = day_date
            days.append(existing)
        else:
            days.append({"day_index": i, "date": day_date, "recipe": None})
    menu["days"] = days
    return menu


def today_menu_item(conn, today: date | None = None) -> dict | None:
    today = today or date.today()
    start = current_week_start(today)
    menu = attach_dates(get_or_create_week_menu(conn, start))
    day_index = today.weekday()
    if day_index >= menu["week_length"]:
        return None
    for day in menu["days"]:
        if day["day_index"] == day_index:
            return {
                "date": day["date"],
                "day_index": day_index,
                "recipe": day["recipe"],
            }
    return {
        "date": today.isoformat(),
        "day_index": day_index,
        "recipe": None,
    }
