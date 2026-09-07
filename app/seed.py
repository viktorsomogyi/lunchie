import os

from app.db import db_session


SEED_RECIPES = [
    {
        "name": "Csirkepaprikás nokedlivel",
        "serves": 4,
        "prep_time_minutes": 60,
        "calories_kcal": 520,
        "protein_g": 38,
        "carbohydrates_g": 48,
        "fats_g": 18,
        "salt_g": 1.8,
        "instructions": (
            "1. A csirkét felkockázod, sózod.\n"
            "2. Hagymát dinszteled, hozzáadod a paprikát, majd a húst.\n"
            "3. Felöntöd vízzel, puhára főzöd.\n"
            "4. Habarásszal sűríted, tejfölt kevered bele.\n"
            "5. Nokedlit főzöl mellé."
        ),
        "ingredients": [
            {"name": "csirkemell", "amount": 150, "unit": "g"},
            {"name": "vöröshagyma", "amount": 50, "unit": "g"},
            {"name": "piros paprika", "amount": 5, "unit": "g"},
            {"name": "tejföl", "amount": 40, "unit": "g"},
            {"name": "liszt (nokedlihez)", "amount": 80, "unit": "g"},
            {"name": "tojás", "amount": 0.5, "unit": "pcs"},
        ],
    },
    {
        "name": "Lencsefőzelék",
        "serves": 4,
        "prep_time_minutes": 50,
        "calories_kcal": 380,
        "protein_g": 22,
        "carbohydrates_g": 55,
        "fats_g": 8,
        "salt_g": 1.2,
        "instructions": (
            "1. A lencsét beáztatod, majd puhára főzöd.\n"
            "2. Hagymát dinszteled, rászórod a lisztet, felöntöd a főzővízzel.\n"
            "3. Hozzáadod a lencsét, fűszerezed.\n"
            "4. Habarásszal sűríted, ízesíted ecettel."
        ),
        "ingredients": [
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
        "calories_kcal": 220,
        "protein_g": 6,
        "carbohydrates_g": 28,
        "fats_g": 9,
        "salt_g": 1.0,
        "instructions": (
            "1. A tököt lereszeled.\n"
            "2. Hagymát dinszteled, rátöltöd a tököt, párolod.\n"
            "3. Kaprot, sót adsz hozzá.\n"
            "4. Habarásszal sűríted, tejfölt kevered bele."
        ),
        "ingredients": [
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
        "calories_kcal": 610,
        "protein_g": 28,
        "carbohydrates_g": 52,
        "fats_g": 32,
        "salt_g": 1.5,
        "instructions": (
            "1. A sajtot panírozod (liszt, tojás, zsemlemorzsa).\n"
            "2. Forró olajban aranybarnára sütöd.\n"
            "3. Rizst főzöl köretnek.\n"
            "4. Tálalod citrommal."
        ),
        "ingredients": [
            {"name": "trappista sajt", "amount": 100, "unit": "g"},
            {"name": "liszt", "amount": 20, "unit": "g"},
            {"name": "tojás", "amount": 1, "unit": "pcs"},
            {"name": "zsemlemorzsa", "amount": 30, "unit": "g"},
            {"name": "rizs", "amount": 70, "unit": "g"},
            {"name": "étolaj (sütéshez)", "amount": 30, "unit": "ml"},
        ],
    },
    {
        "name": "Zöldborsófőzelék",
        "serves": 4,
        "prep_time_minutes": 35,
        "calories_kcal": 290,
        "protein_g": 12,
        "carbohydrates_g": 42,
        "fats_g": 8,
        "salt_g": 1.1,
        "instructions": (
            "1. Hagymát dinszteled vajon vagy olajon.\n"
            "2. Hozzáadod a borsót, felöntöd vízzel, puhára főzöd.\n"
            "3. Petrezselymet szórsz rá.\n"
            "4. Habarásszal sűríted."
        ),
        "ingredients": [
            {"name": "zöldborsó", "amount": 150, "unit": "g"},
            {"name": "vöröshagyma", "amount": 30, "unit": "g"},
            {"name": "liszt", "amount": 10, "unit": "g"},
            {"name": "vaj", "amount": 10, "unit": "g"},
            {"name": "petrezselyem", "amount": 3, "unit": "g"},
        ],
    },
]


def seed_if_empty() -> None:
    if os.environ.get("LUNCHIE_SEED", "1").lower() in ("0", "false", "no"):
        return
    with db_session() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM recipes").fetchone()["n"]
        if count:
            return
        for recipe in SEED_RECIPES:
            cur = conn.execute(
                """
                INSERT INTO recipes (
                    name, instructions, serves, prep_time_minutes,
                    calories_kcal, protein_g, carbohydrates_g, fats_g, salt_g
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe["name"],
                    recipe["instructions"],
                    recipe["serves"],
                    recipe["prep_time_minutes"],
                    recipe["calories_kcal"],
                    recipe["protein_g"],
                    recipe["carbohydrates_g"],
                    recipe["fats_g"],
                    recipe["salt_g"],
                ),
            )
            recipe_id = cur.lastrowid
            for ing in recipe["ingredients"]:
                conn.execute(
                    "INSERT INTO ingredients (recipe_id, name, amount, unit) VALUES (?, ?, ?, ?)",
                    (recipe_id, ing["name"], ing["amount"], ing["unit"]),
                )
