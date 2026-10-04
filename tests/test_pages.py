from app.db import db_session
from tests.conftest import insert_food, insert_recipe


def test_user_week_empty(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "No recipes yet" in response.text


def test_admin_create_edit_delete_recipe(client):
    with db_session() as conn:
        tok = insert_food(conn, name="tök", energy_kcal=26, protein_g=1, carbohydrates_g=6.5, fats_g=0.1, salt_g=0.01, fiber_g=0.5)
        tejfol = insert_food(conn, name="tejföl", energy_kcal=160, protein_g=2.5, carbohydrates_g=3.5, fats_g=15, salt_g=0.05, fiber_g=0)

    form = {
        "name": "Tökfőzelék",
        "serves": "4",
        "prep_time_minutes": "40",
        "nutrition_mode": "recipe",
        "energy_kcal": "220",
        "protein_g": "6",
        "carbohydrates_g": "28",
        "fats_g": "9",
        "salt_g": "1",
        "fiber_g": "4",
        "instructions": "Főzd a tököt.",
        "food_item_id": [str(tok), str(tejfol)],
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
    assert "tök" in detail.text
    assert "250 g" in detail.text

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
        data={"name": "  ", "serves": "1", "prep_time_minutes": "10", "nutrition_mode": "recipe"},
    )
    assert response.status_code == 400


def test_regenerate_page(client):
    with db_session() as conn:
        insert_recipe(conn, name="Gulyás")
    response = client.post("/menu/regenerate", follow_redirects=True)
    assert response.status_code == 200
    assert "Gulyás" in response.text


def test_ingredient_row_partial(client):
    with db_session() as conn:
        insert_food(conn, name="liszt")
    response = client.get("/admin/ingredients/row")
    assert response.status_code == 200
    assert 'name="food_item_id"' in response.text
    assert "/admin/food-items/picker" in response.text
    assert 'id="ing-row-' in response.text

    custom = client.get("/admin/ingredients/row", params={"row_id": "ing-row-7"})
    assert 'id="ing-row-7"' in custom.text


def test_food_picker_modal_and_search(client):
    with db_session() as conn:
        insert_food(conn, name="liszt")
        insert_food(conn, name="tök")

    picker = client.get("/admin/food-items/picker", params={"target": "ing-row-1"})
    assert picker.status_code == 200
    assert "ing-row-1" in picker.text
    assert "liszt" in picker.text
    assert "tök" in picker.text

    filtered = client.get(
        "/admin/food-items/picker/results",
        params={"target": "ing-row-1", "q": "liszt"},
    )
    assert filtered.status_code == 200
    assert "liszt" in filtered.text
    assert "tök" not in filtered.text
    assert "pickFoodItem" in filtered.text

    none = client.get(
        "/admin/food-items/picker/results",
        params={"target": "ing-row-1", "q": "xyzzy"},
    )
    assert "No matching" in none.text


def test_food_picker_select_handler_is_valid_html(client):
    from html.parser import HTMLParser

    with db_session() as conn:
        insert_food(conn, name="liszt")
        insert_food(conn, name="d'Artagnan \"finom\"")

    response = client.get(
        "/admin/food-items/picker/results",
        params={"target": "ing-row-1", "q": ""},
    )
    assert response.status_code == 200

    class Buttons(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.handlers = []

        def handle_starttag(self, tag, attrs):
            if tag == "button":
                attrs_dict = dict(attrs)
                if "onclick" in attrs_dict:
                    self.handlers.append(attrs_dict["onclick"])

    parser = Buttons()
    parser.feed(response.text)
    assert len(parser.handlers) == 2
    for handler in parser.handlers:
        # The whole JS call must survive as one attribute value.
        assert handler.startswith('pickFoodItem("ing-row-1", ')
        assert handler.endswith(')')
    assert any('"liszt"' in handler for handler in parser.handlers)
    assert any("finom" in handler for handler in parser.handlers)


def test_confirm_dialogs_are_valid_html(client):
    with db_session() as conn:
        insert_recipe(conn, name="Gulyás")
        insert_food(conn, name="liszt")

    for url in ("/", "/admin/recipes", "/admin/food-items"):
        page = client.get(url)
        assert page.status_code == 200
        # tojson output contains double quotes, so the attribute must be
        # single-quoted; a double-quoted attribute would truncate the handler.
        assert 'onsubmit="return confirm(' not in page.text
    assert "return confirm(" in client.get("/").text


def test_recipe_form_uses_food_picker(client):
    with db_session() as conn:
        insert_food(conn, name="liszt")
    form_page = client.get("/admin/recipes/new")
    assert form_page.status_code == 200
    assert "pickFoodItem" in form_page.text
    assert "/admin/food-items/picker" in form_page.text
    assert 'name="food_item_id" type="hidden"' in form_page.text or 'type="hidden" name="food_item_id"' in form_page.text


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


def test_catalog_nutrition_scaled_by_amount(client):
    with db_session() as conn:
        pasta = insert_food(
            conn,
            name="pasta",
            base_amount=100,
            base_unit="g",
            energy_kcal=465,
            protein_g=8,
            carbohydrates_g=45,
            fats_g=4,
            salt_g=0.01,
            fiber_g=1,
        )
        oil = insert_food(
            conn,
            name="oil",
            base_amount=100,
            base_unit="ml",
            energy_kcal=884,
            protein_g=0,
            carbohydrates_g=0,
            fats_g=100,
            salt_g=0,
            fiber_g=0,
        )

    form = {
        "name": "Pasta dish",
        "serves": "2",
        "prep_time_minutes": "20",
        "nutrition_mode": "ingredient",
        "instructions": "Cook.",
        "food_item_id": [str(pasta), str(oil)],
        "ingredient_amount": ["200", "10"],
        "ingredient_unit": ["g", "ml"],
    }
    created = client.post("/admin/recipes", data=form, follow_redirects=False)
    assert created.status_code == 303
    recipe = client.get("/api/recipes").json()[0]
    assert recipe["nutrition_mode"] == "ingredient"
    # pasta 200g => 2x base; oil 10ml => 0.1x base; then / serves 2
    # pasta total kcal 930, oil 88.4, sum 1018.4 / 2 = 509.2
    assert recipe["energy_kcal"] == 509.2
    assert recipe["protein_g"] == 8
    assert recipe["carbohydrates_g"] == 45
    assert recipe["fats_g"] == 9
    assert recipe["fiber_g"] == 1
    assert recipe["ingredients"][0]["energy_kcal"] == 930

    week = client.get("/")
    assert "509.2 kcal" in week.text
    assert "Serves 2" in week.text


def test_food_item_crud(client):
    form = {
        "name": "pasta",
        "base_amount": "100",
        "base_unit": "g",
        "energy_kcal": "465",
        "protein_g": "8",
        "carbohydrates_g": "45",
        "fats_g": "4",
        "salt_g": "0.01",
        "fiber_g": "1",
        "product_link": "https://shop.example.com/pasta",
    }
    created = client.post("/admin/food-items", data=form, follow_redirects=False)
    assert created.status_code == 303
    listing = client.get("/admin/food-items")
    assert "pasta" in listing.text
    assert "100 g" in listing.text
    assert "https://shop.example.com/pasta" in listing.text

    dup = client.post("/admin/food-items", data=form)
    assert dup.status_code == 400

    with db_session() as conn:
        food_id = conn.execute("SELECT id FROM food_items WHERE name = ?", ("pasta",)).fetchone()["id"]

    edit = dict(form)
    edit["energy_kcal"] = "470"
    edit["product_link"] = "https://shop.example.com/pasta-v2"
    updated = client.post(f"/admin/food-items/{food_id}", data=edit, follow_redirects=False)
    assert updated.status_code == 303
    with db_session() as conn:
        link = conn.execute("SELECT product_link FROM food_items WHERE id = ?", (food_id,)).fetchone()["product_link"]
        assert link == "https://shop.example.com/pasta-v2"

    deleted = client.post(f"/admin/food-items/{food_id}/delete", follow_redirects=False)
    assert deleted.status_code == 303
