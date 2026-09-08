import os

from app.db import db_session


SEED_FOOD_ITEMS = [
    {
        "name": "csirkemell",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 110,
        "protein_g": 23,
        "carbohydrates_g": 0,
        "fats_g": 1.5,
        "salt_g": 0.1,
        "fiber_g": 0,
    },
    {
        "name": "vöröshagyma",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 40,
        "protein_g": 1.1,
        "carbohydrates_g": 9,
        "fats_g": 0.1,
        "salt_g": 0.01,
        "fiber_g": 1.7,
    },
    {
        "name": "piros paprika",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 31,
        "protein_g": 1,
        "carbohydrates_g": 6,
        "fats_g": 0.3,
        "salt_g": 0.01,
        "fiber_g": 2.1,
    },
    {
        "name": "tejföl",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 160,
        "protein_g": 2.5,
        "carbohydrates_g": 3.5,
        "fats_g": 15,
        "salt_g": 0.05,
        "fiber_g": 0,
    },
    {
        "name": "liszt",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 364,
        "protein_g": 10,
        "carbohydrates_g": 76,
        "fats_g": 1,
        "salt_g": 0.01,
        "fiber_g": 2.7,
    },
    {
        "name": "tojás",
        "base_amount": 1,
        "base_unit": "pcs",
        "calories_kcal": 72,
        "protein_g": 6.3,
        "carbohydrates_g": 0.4,
        "fats_g": 4.8,
        "salt_g": 0.14,
        "fiber_g": 0,
    },
    {
        "name": "lencse",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 116,
        "protein_g": 9,
        "carbohydrates_g": 20,
        "fats_g": 0.4,
        "salt_g": 0.02,
        "fiber_g": 7.9,
    },
    {
        "name": "étolaj",
        "base_amount": 100,
        "base_unit": "ml",
        "calories_kcal": 884,
        "protein_g": 0,
        "carbohydrates_g": 0,
        "fats_g": 100,
        "salt_g": 0,
        "fiber_g": 0,
    },
    {
        "name": "ecet",
        "base_amount": 100,
        "base_unit": "ml",
        "calories_kcal": 18,
        "protein_g": 0,
        "carbohydrates_g": 0.4,
        "fats_g": 0,
        "salt_g": 0.01,
        "fiber_g": 0,
    },
    {
        "name": "nyers tök",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 26,
        "protein_g": 1,
        "carbohydrates_g": 6.5,
        "fats_g": 0.1,
        "salt_g": 0.01,
        "fiber_g": 0.5,
    },
    {
        "name": "kapor",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 43,
        "protein_g": 3.5,
        "carbohydrates_g": 7,
        "fats_g": 1.1,
        "salt_g": 0.06,
        "fiber_g": 2.1,
    },
    {
        "name": "trappista sajt",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 350,
        "protein_g": 25,
        "carbohydrates_g": 1.5,
        "fats_g": 27,
        "salt_g": 1.5,
        "fiber_g": 0,
    },
    {
        "name": "zsemlemorzsa",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 395,
        "protein_g": 13,
        "carbohydrates_g": 72,
        "fats_g": 5,
        "salt_g": 1.2,
        "fiber_g": 4,
    },
    {
        "name": "rizs",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 130,
        "protein_g": 2.7,
        "carbohydrates_g": 28,
        "fats_g": 0.3,
        "salt_g": 0.01,
        "fiber_g": 0.4,
    },
    {
        "name": "zöldborsó",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 81,
        "protein_g": 5.4,
        "carbohydrates_g": 14,
        "fats_g": 0.4,
        "salt_g": 0.02,
        "fiber_g": 5.5,
    },
    {
        "name": "vaj",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 717,
        "protein_g": 0.9,
        "carbohydrates_g": 0.1,
        "fats_g": 81,
        "salt_g": 0.01,
        "fiber_g": 0,
    },
    {
        "name": "petrezselyem",
        "base_amount": 100,
        "base_unit": "g",
        "calories_kcal": 36,
        "protein_g": 3,
        "carbohydrates_g": 6,
        "fats_g": 0.8,
        "salt_g": 0.06,
        "fiber_g": 3.3,
    },
]

SEED_RECIPES = [
    {
        "name": "Csirkepaprikás nokedlivel",
        "serves": 4,
        "prep_time_minutes": 60,
        "nutrition_mode": "ingredient",
        "instructions": (
            "1. A csirkét felkockázod, sózod.\n"
            "2. Hagymát dinszteled, hozzáadod a paprikát, majd a húst.\n"
            "3. Felöntöd vízzel, puhára főzöd.\n"
            "4. Habarásszal sűríted, tejfölt kevered bele.\n"
            "5. Nokedlit főzöl mellé."
        ),
        "items": [
            {"name": "csirkemell", "amount": 150, "unit": "g"},
            {"name": "vöröshagyma", "amount": 50, "unit": "g"},
            {"name": "piros paprika", "amount": 5, "unit": "g"},
            {"name": "tejföl", "amount": 40, "unit": "g"},
            {"name": "liszt", "amount": 80, "unit": "g"},
            {"name": "tojás", "amount": 0.5, "unit": "pcs"},
        ],
    },
    {
        "name": "Lencsefőzelék",
        "serves": 4,
        "prep_time_minutes": 50,
        "nutrition_mode": "ingredient",
        "instructions": (
            "1. A lencsét beáztatod, majd puhára főzöd.\n"
            "2. Hagymát dinszteled, rászórod a lisztet, felöntöd a főzővízzel.\n"
            "3. Hozzáadod a lencsét, fűszerezed.\n"
            "4. Habarásszal sűríted, ízesíted ecettel."
        ),
        "items": [
            {"name": "lencse", "amount": 80, "unit": "g"},
            {"name": "vöröshagyma", "amount": 40, "unit": "g"},
            {"name": "liszt", "amount": 10, "unit": "g"},
            {"name": "étolaj", "amount": 10, "unit": "ml"},
            {"name": "ecet", "amount": 5, "unit": "ml"},
        ],
    },
    {
        "name": "Tökfőzelék",
        "serves": 4,
        "prep_time_minutes": 40,
        "nutrition_mode": "ingredient",
        "instructions": (
            "1. A tököt lereszeled.\n"
            "2. Hagymát dinszteled, rátöltöd a tököt, párolod.\n"
            "3. Kaprot, sót adsz hozzá.\n"
            "4. Habarásszal sűríted, tejfölt kevered bele."
        ),
        "items": [
            {"name": "nyers tök", "amount": 250, "unit": "g"},
            {"name": "vöröshagyma", "amount": 30, "unit": "g"},
            {"name": "tejföl", "amount": 30, "unit": "g"},
            {"name": "liszt", "amount": 8, "unit": "g"},
            {"name": "kapor", "amount": 2, "unit": "g"},
        ],
    },
    {
        "name": "Rántott sajt rizzsel",
        "serves": 2,
        "prep_time_minutes": 35,
        "nutrition_mode": "ingredient",
        "instructions": (
            "1. A sajtot panírozod (liszt, tojás, zsemlemorzsa).\n"
            "2. Forró olajban aranybarnára sütöd.\n"
            "3. Rizst főzöl köretnek.\n"
            "4. Tálalod citrommal."
        ),
        "items": [
            {"name": "trappista sajt", "amount": 100, "unit": "g"},
            {"name": "liszt", "amount": 20, "unit": "g"},
            {"name": "tojás", "amount": 1, "unit": "pcs"},
            {"name": "zsemlemorzsa", "amount": 30, "unit": "g"},
            {"name": "rizs", "amount": 70, "unit": "g"},
            {"name": "étolaj", "amount": 30, "unit": "ml"},
        ],
    },
    {
        "name": "Zöldborsófőzelék",
        "serves": 4,
        "prep_time_minutes": 35,
        "nutrition_mode": "ingredient",
        "instructions": (
            "1. Hagymát dinszteled vajon vagy olajon.\n"
            "2. Hozzáadod a borsót, felöntöd vízzel, puhára főzöd.\n"
            "3. Petrezselymet szórsz rá.\n"
            "4. Habarásszal sűríted."
        ),
        "items": [
            {"name": "zöldborsó", "amount": 150, "unit": "g"},
            {"name": "vöröshagyma", "amount": 30, "unit": "g"},
            {"name": "liszt", "amount": 10, "unit": "g"},
            {"name": "vaj", "amount": 10, "unit": "g"},
            {"name": "petrezselyem", "amount": 3, "unit": "g"},
        ],
    },
]


def _insert_food(conn, food: dict) -> int:
    cur = conn.execute(
        """
        INSERT INTO food_items (
            name, base_amount, base_unit,
            calories_kcal, protein_g, carbohydrates_g, fats_g, salt_g, fiber_g,
            product_link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            food["name"],
            food["base_amount"],
            food["base_unit"],
            food["calories_kcal"],
            food["protein_g"],
            food["carbohydrates_g"],
            food["fats_g"],
            food["salt_g"],
            food["fiber_g"],
            food.get("product_link", ""),
        ),
    )
    return cur.lastrowid


def seed_if_empty() -> None:
    if os.environ.get("LUNCHIE_SEED", "1").lower() in ("0", "false", "no"):
        return
    with db_session() as conn:
        recipe_count = conn.execute("SELECT COUNT(*) AS n FROM recipes").fetchone()["n"]
        food_count = conn.execute("SELECT COUNT(*) AS n FROM food_items").fetchone()["n"]
        food_ids: dict[str, int] = {}
        if food_count == 0:
            for food in SEED_FOOD_ITEMS:
                food_ids[food["name"]] = _insert_food(conn, food)
        else:
            rows = conn.execute("SELECT id, name FROM food_items").fetchall()
            food_ids = {row["name"]: row["id"] for row in rows}

        if recipe_count:
            return

        for recipe in SEED_RECIPES:
            cur = conn.execute(
                """
                INSERT INTO recipes (
                    name, instructions, serves, prep_time_minutes,
                    calories_kcal, protein_g, carbohydrates_g, fats_g, salt_g, fiber_g,
                    nutrition_mode
                ) VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0, 0, ?)
                """,
                (
                    recipe["name"],
                    recipe["instructions"],
                    recipe["serves"],
                    recipe["prep_time_minutes"],
                    recipe.get("nutrition_mode", "ingredient"),
                ),
            )
            recipe_id = cur.lastrowid
            for item in recipe["items"]:
                food_id = food_ids.get(item["name"])
                if food_id is None:
                    continue
                conn.execute(
                    """
                    INSERT INTO recipe_items (recipe_id, food_item_id, amount, unit)
                    VALUES (?, ?, ?, ?)
                    """,
                    (recipe_id, food_id, item["amount"], item["unit"]),
                )
