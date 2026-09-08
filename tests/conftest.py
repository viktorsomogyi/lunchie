import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "lunchie.db")
    monkeypatch.setenv("DATABASE_PATH", path)
    monkeypatch.setenv("LUNCHIE_SEED", "0")
    return path


@pytest.fixture
def client(db_path):
    from app.db import init_db
    from app.i18n import load_catalogs
    from app.main import app

    load_catalogs()
    init_db()
    with TestClient(app) as test_client:
        yield test_client


def insert_food(
    conn,
    name="hús",
    base_amount=100,
    base_unit="g",
    energy_kcal=200,
    protein_g=20,
    carbohydrates_g=0,
    fats_g=10,
    salt_g=0.1,
    fiber_g=0,
    product_link="",
):
    cur = conn.execute(
        """
        INSERT INTO food_items (
            name, base_amount, base_unit,
            energy_kcal, protein_g, carbohydrates_g, fats_g, salt_g, fiber_g,
            product_link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            base_amount,
            base_unit,
            energy_kcal,
            protein_g,
            carbohydrates_g,
            fats_g,
            salt_g,
            fiber_g,
            product_link,
        ),
    )
    return cur.lastrowid


def insert_recipe(conn, name="Gulyás", **overrides):
    fields = {
        "name": name,
        "instructions": overrides.get("instructions", "Főzd."),
        "serves": overrides.get("serves", 4),
        "prep_time_minutes": overrides.get("prep_time_minutes", 30),
        "energy_kcal": overrides.get("energy_kcal", 400),
        "protein_g": overrides.get("protein_g", 20),
        "carbohydrates_g": overrides.get("carbohydrates_g", 30),
        "fats_g": overrides.get("fats_g", 10),
        "salt_g": overrides.get("salt_g", 1),
        "fiber_g": overrides.get("fiber_g", 2),
        "nutrition_mode": overrides.get("nutrition_mode", "recipe"),
    }
    cur = conn.execute(
        """
        INSERT INTO recipes (
            name, instructions, serves, prep_time_minutes,
            energy_kcal, protein_g, carbohydrates_g, fats_g, salt_g, fiber_g,
            nutrition_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fields["name"],
            fields["instructions"],
            fields["serves"],
            fields["prep_time_minutes"],
            fields["energy_kcal"],
            fields["protein_g"],
            fields["carbohydrates_g"],
            fields["fats_g"],
            fields["salt_g"],
            fields["fiber_g"],
            fields["nutrition_mode"],
        ),
    )
    recipe_id = cur.lastrowid
    items = overrides.get("items")
    if items is None:
        food_id = insert_food(conn, name=f"{name}-alap")
        items = [{"food_item_id": food_id, "amount": 100, "unit": "g"}]
    for item in items:
        conn.execute(
            """
            INSERT INTO recipe_items (recipe_id, food_item_id, amount, unit)
            VALUES (?, ?, ?, ?)
            """,
            (recipe_id, item["food_item_id"], item["amount"], item.get("unit", "g")),
        )
    return recipe_id
