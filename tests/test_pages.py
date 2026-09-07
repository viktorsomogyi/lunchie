from app.db import db_session
from tests.conftest import insert_recipe


def test_user_week_empty(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "No recipes yet" in response.text


def test_admin_create_edit_delete_recipe(client):
    form = {
        "name": "Tökfőzelék",
        "serves": "4",
        "prep_time_minutes": "40",
        "calories_kcal": "220",
        "protein_g": "6",
        "carbohydrates_g": "28",
        "fats_g": "9",
        "salt_g": "1",
        "instructions": "Főzd a tököt.",
        "ingredient_name": ["tök", "tejföl"],
        "ingredient_amount": ["250", "30"],
        "ingredient_unit": ["g", "g"],
    }
    created = client.post("/admin/recipes", data=form, follow_redirects=False)
    assert created.status_code == 303

    listing = client.get("/admin/recipes")
    assert "Tökfőzelék" in listing.text

    duplicate = client.post("/admin/recipes", data=form)
    assert duplicate.status_code == 400
    assert "already exists" in duplicate.text

    case_dup = dict(form)
    case_dup["name"] = "tökfőzelék"
    assert client.post("/admin/recipes", data=case_dup).status_code == 400

    recipes = client.get("/api/recipes").json()
    recipe_id = recipes[0]["id"]

    detail = client.get(f"/recipes/{recipe_id}")
    assert detail.status_code == 200
    assert "Főzd a tököt." in detail.text
    assert "tök — 250 g" in detail.text

    modal = client.get(f"/recipes/{recipe_id}", headers={"HX-Request": "true"})
    assert "recipe-dialog" in modal.text

    edit_form = dict(form)
    edit_form["name"] = "Tökfőzelék kaporral"
    edit_form["serves"] = "3"
    updated = client.post(f"/admin/recipes/{recipe_id}", data=edit_form, follow_redirects=False)
    assert updated.status_code == 303
    assert client.get("/api/recipes").json()[0]["serves"] == 3

    deleted = client.post(f"/admin/recipes/{recipe_id}/delete", follow_redirects=False)
    assert deleted.status_code == 303
    assert client.get("/api/recipes").json() == []


def test_create_requires_name(client):
    response = client.post(
        "/admin/recipes",
        data={"name": "  ", "serves": "1", "prep_time_minutes": "10"},
    )
    assert response.status_code == 400


def test_regenerate_page(client):
    with db_session() as conn:
        insert_recipe(conn, name="Gulyás")
    response = client.post("/menu/regenerate", follow_redirects=True)
    assert response.status_code == 200
    assert "Gulyás" in response.text


def test_ingredient_row_partial(client):
    response = client.get("/admin/ingredients/row")
    assert response.status_code == 200
    assert 'name="ingredient_name"' in response.text


def test_day_recipe_picker_and_assign(client):
    with db_session() as conn:
        insert_recipe(conn, name="Gulyás")
        insert_recipe(conn, name="Lencsefőzelék")
        insert_recipe(conn, name="Tökfőzelék")

    week = client.get("/")
    assert week.status_code == 200
    assert "Change" in week.text
    assert "/menu/days/0/picker" in week.text

    picker = client.get("/menu/days/0/picker")
    assert picker.status_code == 200
    assert "Choose a recipe" in picker.text
    assert "Gulyás" in picker.text
    assert "Lencsefőzelék" in picker.text

    filtered = client.get("/menu/days/0/picker/results", params={"q": "lencse"})
    assert filtered.status_code == 200
    assert "Lencsefőzelék" in filtered.text
    assert "Gulyás" not in filtered.text

    none = client.get("/menu/days/0/picker/results", params={"q": "xyzzy"})
    assert "No matching recipes." in none.text

    recipes = {r["name"]: r["id"] for r in client.get("/api/recipes").json()}
    assigned = client.post(
        "/menu/days/0",
        data={"recipe_id": recipes["Tökfőzelék"]},
        follow_redirects=False,
    )
    assert assigned.status_code == 303
    current = client.get("/api/menu/current").json()
    assert current["days"][0]["recipe"]["name"] == "Tökfőzelék"

    assert client.get("/menu/days/9/picker").status_code == 404
    assert client.post("/menu/days/0", data={"recipe_id": 9999}).status_code == 404


def test_ingredient_nutrition_totals_per_serving(client):
    form = {
        "name": "Gulyás",
        "serves": "2",
        "prep_time_minutes": "30",
        "nutrition_mode": "ingredient",
        "instructions": "Főzd.",
        "ingredient_name": ["hús", "hagyma"],
        "ingredient_amount": ["200", "50"],
        "ingredient_unit": ["g", "g"],
        "ingredient_calories_kcal": ["400", "40"],
        "ingredient_protein_g": ["40", "2"],
        "ingredient_carbohydrates_g": ["0", "8"],
        "ingredient_fats_g": ["20", "0"],
        "ingredient_salt_g": ["1", "0.2"],
    }
    created = client.post("/admin/recipes", data=form, follow_redirects=False)
    assert created.status_code == 303
    recipe = client.get("/api/recipes").json()[0]
    assert recipe["nutrition_mode"] == "ingredient"
    assert recipe["calories_kcal"] == 220
    assert recipe["protein_g"] == 21
    assert recipe["carbohydrates_g"] == 4
    assert recipe["fats_g"] == 10
    assert recipe["salt_g"] == 0.6
    assert recipe["ingredients"][0]["calories_kcal"] == 400

    week = client.get("/")
    assert "220 kcal" in week.text
    assert "Serves 2" in week.text
