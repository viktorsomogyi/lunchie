from app.db import db_session
from tests.conftest import insert_food, insert_recipe


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_recipes_empty(client):
    assert client.get("/api/recipes").json() == []
    assert client.get("/api/recipes/1").status_code == 404


def test_recipe_crud_and_menu(client):
    with db_session() as conn:
        lencse = insert_food(conn, name="lencse")
        rid = insert_recipe(
            conn,
            name="Lencsefőzelék",
            items=[{"food_item_id": lencse, "amount": 80, "unit": "g"}],
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


def test_recipe_ingredients_export_json_and_csv(client):
    with db_session() as conn:
        pasta = insert_food(
            conn,
            name="pasta",
            energy_kcal=465,
            protein_g=8,
            carbohydrates_g=45,
            fats_g=4,
            salt_g=0.01,
            fiber_g=1,
            product_link="https://shop.example.com/pasta",
        )
        rid = insert_recipe(
            conn,
            name="Pasta dish",
            nutrition_mode="ingredient",
            serves=2,
            items=[{"food_item_id": pasta, "amount": 200, "unit": "g"}],
        )

    json_resp = client.get(f"/api/recipes/{rid}/ingredients.json")
    assert json_resp.status_code == 200
    assert "attachment" in json_resp.headers.get("content-disposition", "")
    assert "ingredients.json" in json_resp.headers.get("content-disposition", "")
    payload = json_resp.json()
    assert payload["recipe_name"] == "Pasta dish"
    assert payload["serves"] == 2
    assert len(payload["ingredients"]) == 1
    assert payload["ingredients"][0]["name"] == "pasta"
    assert payload["ingredients"][0]["amount"] == 200
    assert payload["ingredients"][0]["unit"] == "g"
    assert payload["ingredients"][0]["energy_kcal"] == 930
    assert payload["ingredients"][0]["product_link"] == "https://shop.example.com/pasta"

    csv_resp = client.get(f"/api/recipes/{rid}/ingredients.csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("content-type", "")
    assert "attachment" in csv_resp.headers.get("content-disposition", "")
    assert "ingredients.csv" in csv_resp.headers.get("content-disposition", "")
    text = csv_resp.text
    assert "name,amount,unit,product_link" in text
    assert "pasta,200.0,g,https://shop.example.com/pasta" in text
    assert "930.0" in text

    assert client.get("/api/recipes/9999/ingredients.json").status_code == 404
    assert client.get("/api/recipes/9999/ingredients.csv").status_code == 404


def test_ingredients_export_accented_name_download_headers(client):
    import csv as csv_module
    import io as io_module

    with db_session() as conn:
        tok = insert_food(conn, name="tök")
        rid = insert_recipe(
            conn,
            name="Tökfőzelék kaporral",
            items=[{"food_item_id": tok, "amount": 250, "unit": "g"}],
        )

    for suffix in ("json", "csv"):
        resp = client.get(f"/api/recipes/{rid}/ingredients.{suffix}")
        assert resp.status_code == 200
        disposition = resp.headers.get("content-disposition", "")
        assert "attachment" in disposition
        # Header must be pure ASCII (Opera rejects raw non-ASCII filenames).
        disposition.encode("ascii")
        assert "filename*=" in disposition
        assert f"ingredients.{suffix}" in disposition

    # CSV has a UTF-8 BOM so spreadsheet apps keep Hungarian accents.
    csv_resp = client.get(f"/api/recipes/{rid}/ingredients.csv")
    assert csv_resp.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv_module.DictReader(io_module.StringIO(csv_resp.text.lstrip("\ufeff"))))
    assert len(rows) == 1
    assert rows[0]["name"] == "tök"
    assert rows[0]["amount"] == "250.0"

    json_resp = client.get(f"/api/recipes/{rid}/ingredients.json")
    assert "application/json" in json_resp.headers.get("content-type", "")
    assert json_resp.json()["ingredients"][0]["name"] == "tök"


def test_weekly_menu_export_json_and_csv(client):
    import csv as csv_module
    import io as io_module

    with db_session() as conn:
        pasta = insert_food(conn, name="pasta", energy_kcal=465)
        insert_recipe(
            conn,
            name="Pasta dish",
            nutrition_mode="ingredient",
            serves=2,
            items=[{"food_item_id": pasta, "amount": 200, "unit": "g"}],
        )

    json_resp = client.get("/api/menu/export.json")
    assert json_resp.status_code == 200
    disposition = json_resp.headers.get("content-disposition", "")
    assert "attachment" in disposition
    disposition.encode("ascii")
    assert "filename*=" in disposition
    assert "menu.json" in disposition
    payload = json_resp.json()
    assert payload["week_length"] == 5
    assert len(payload["days"]) == 5
    assert all(day["recipe"]["name"] == "Pasta dish" for day in payload["days"])
    assert payload["days"][0]["recipe"]["energy_kcal"] == 465

    csv_resp = client.get("/api/menu/export.csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("content-type", "")
    csv_disposition = csv_resp.headers.get("content-disposition", "")
    assert "attachment" in csv_disposition
    csv_disposition.encode("ascii")
    assert "menu.csv" in csv_disposition
    assert csv_resp.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv_module.DictReader(io_module.StringIO(csv_resp.text.lstrip("\ufeff"))))
    assert len(rows) == 5
    assert rows[0]["recipe"] == "Pasta dish"
    assert rows[0]["serves"] == "2"
    assert rows[0]["energy_kcal"] == "465.0"
    assert rows[0]["date"]

    week_page = client.get("/")
    assert "/api/menu/export.json" in week_page.text
    assert "/api/menu/export.csv" in week_page.text


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
