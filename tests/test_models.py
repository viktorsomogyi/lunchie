from app.models import FoodItem, Recipe, RecipeItem, scale_factor


def test_scale_factor_mass_and_volume():
    assert scale_factor(200, "g", 100, "g") == 2
    assert scale_factor(1, "kg", 100, "g") == 10
    assert scale_factor(10, "ml", 100, "ml") == 0.1
    assert scale_factor(1, "l", 100, "ml") == 10
    assert scale_factor(2, "tbsp", 1, "tsp") == 6
    assert scale_factor(100, "g", 100, "ml") == 0


def test_food_item_nutrition_for_amount():
    pasta = FoodItem(
        name="pasta",
        base_amount=100,
        base_unit="g",
        calories_kcal=465,
        protein_g=8,
        carbohydrates_g=45,
        fats_g=4,
        salt_g=0.01,
        fiber_g=1,
    )
    n = pasta.nutrition_for_amount(200, "g")
    assert n["calories_kcal"] == 930
    assert n["carbohydrates_g"] == 90
    assert n["fiber_g"] == 2


def test_recipe_per_person_from_catalog():
    pasta = FoodItem(name="pasta", base_amount=100, base_unit="g", calories_kcal=465, carbohydrates_g=45, protein_g=8, fats_g=4, fiber_g=1)
    oil = FoodItem(name="oil", base_amount=100, base_unit="ml", calories_kcal=884, fats_g=100)
    recipe = Recipe(
        name="dish",
        serves=2,
        nutrition_mode="ingredient",
        ingredients=[
            RecipeItem(amount=200, unit="g", food_item=pasta),
            RecipeItem(amount=10, unit="ml", food_item=oil),
        ],
    )
    per = recipe.per_person_nutrition()
    assert per["calories_kcal"] == 509.2
    assert per["fats_g"] == 9
