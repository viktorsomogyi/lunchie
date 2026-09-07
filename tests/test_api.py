from app.db import db_session
from tests.conftest import insert_recipe


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_recipes_empty(client):
    assert client.get("/api/recipes").json() == []
    assert client.get("/api/recipes/1").status_code == 404


def test_recipe_crud_and_menu(client):
    with db_session() as conn:
        rid = insert_recipe(
            conn,
            name="Lencsefőzelék",
            ingredients=[{"name": "lencse", "amount": 80, "unit": "g"}],
        )

    recipes = client.get("/api/recipes").json()
    assert len(recipes) == 1
    assert recipes[0]["name"] == "Lencsefőzelék"
    assert recipes[0]["serves"] == 4
    assert recipes[0]["ingredients"][0]["name"] == "lencse"

    one = client.get(f"/api/recipes/{rid}").json()
    assert one["id"] == rid

    regenerated = client.post("/api/menu/regenerate").json()
    assert regenerated["week_length"] == 5
    assert len(regenerated["days"]) == 5
    assert all(day["recipe"]["name"] == "Lencsefőzelék" for day in regenerated["days"])

    current = client.get("/api/menu/current").json()
    assert current["week_start"] == regenerated["week_start"]
    assert len(current["days"]) == 5

    today = client.get("/api/menu/today").json()
    assert "date" in today
    assert "day" in today
    assert "recipe" in today


def test_settings_language_and_week_length(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Weekly menu" in page.text

    response = client.post(
        "/admin/settings",
        data={"week_length": "7", "ui_language": "hu"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    hu = client.get("/")
    assert "Heti menü" in hu.text

    current = client.get("/api/menu/current").json()
    assert current["week_length"] == 7
