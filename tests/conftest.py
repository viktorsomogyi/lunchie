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


def insert_recipe(conn, name="Gulyás", **overrides):
    fields = {
        "name": name,
        "instructions": overrides.get("instructions", "Főzd."),
        "serves": overrides.get("serves", 4),
        "prep_time_minutes": overrides.get("prep_time_minutes", 30),
        "calories_kcal": overrides.get("calories_kcal", 400),
        "protein_g": overrides.get("protein_g", 20),
        "carbohydrates_g": overrides.get("carbohydrates_g", 30),
        "fats_g": overrides.get("fats_g", 10),
        "salt_g": overrides.get("salt_g", 1),
    }
    cur = conn.execute(
        """
        INSERT INTO recipes (
            name, instructions, serves, prep_time_minutes,
            calories_kcal, protein_g, carbohydrates_g, fats_g, salt_g
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fields["name"],
            fields["instructions"],
            fields["serves"],
            fields["prep_time_minutes"],
            fields["calories_kcal"],
            fields["protein_g"],
            fields["carbohydrates_g"],
            fields["fats_g"],
            fields["salt_g"],
        ),
    )
    recipe_id = cur.lastrowid
    for ing in overrides.get("ingredients", [{"name": "hús", "amount": 100, "unit": "g"}]):
        conn.execute(
            "INSERT INTO ingredients (recipe_id, name, amount, unit) VALUES (?, ?, ?, ?)",
            (recipe_id, ing["name"], ing["amount"], ing["unit"]),
        )
    return recipe_id
