from dataclasses import dataclass, field

NUTRITION_FIELDS = ("calories_kcal", "protein_g", "carbohydrates_g", "fats_g", "salt_g")
NUTRITION_MODE_RECIPE = "recipe"
NUTRITION_MODE_INGREDIENT = "ingredient"


def _nutrition_values(obj) -> dict[str, float]:
    return {field: float(getattr(obj, field) or 0) for field in NUTRITION_FIELDS}


def round_nutrition(value: float) -> float:
    return round(float(value or 0), 2)


@dataclass
class Ingredient:
    name: str
    amount: float
    unit: str
    id: int | None = None
    recipe_id: int | None = None
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbohydrates_g: float = 0.0
    fats_g: float = 0.0
    salt_g: float = 0.0

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "name": self.name,
            "amount": self.amount,
            "unit": self.unit,
        }
        data.update(_nutrition_values(self))
        return data


@dataclass
class Recipe:
    name: str
    instructions: str = ""
    serves: int = 1
    prep_time_minutes: int = 0
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbohydrates_g: float = 0.0
    fats_g: float = 0.0
    salt_g: float = 0.0
    nutrition_mode: str = NUTRITION_MODE_RECIPE
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    ingredients: list[Ingredient] = field(default_factory=list)

    @property
    def uses_ingredient_nutrition(self) -> bool:
        return self.nutrition_mode == NUTRITION_MODE_INGREDIENT

    def per_person_nutrition(self) -> dict[str, float]:
        if self.uses_ingredient_nutrition:
            totals = {field: 0.0 for field in NUTRITION_FIELDS}
            for ingredient in self.ingredients:
                for field_name, value in _nutrition_values(ingredient).items():
                    totals[field_name] += value
            serves = max(int(self.serves or 1), 1)
            return {field: round_nutrition(total / serves) for field, total in totals.items()}
        return {field: round_nutrition(value) for field, value in _nutrition_values(self).items()}

    def apply_per_person_nutrition(self) -> None:
        for field_name, value in self.per_person_nutrition().items():
            setattr(self, field_name, value)

    def to_dict(self, include_ingredients: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "instructions": self.instructions,
            "serves": self.serves,
            "prep_time_minutes": self.prep_time_minutes,
            "nutrition_mode": self.nutrition_mode,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        data.update(self.per_person_nutrition())
        if include_ingredients:
            data["ingredients"] = [i.to_dict() for i in self.ingredients]
        return data


def _row_value(row, key, default=None):
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else value


def recipe_from_row(row, ingredients: list | None = None) -> Recipe:
    recipe = Recipe(
        id=row["id"],
        name=row["name"],
        instructions=row["instructions"],
        serves=row["serves"],
        prep_time_minutes=row["prep_time_minutes"],
        calories_kcal=_row_value(row, "calories_kcal", 0) or 0,
        protein_g=_row_value(row, "protein_g", 0) or 0,
        carbohydrates_g=_row_value(row, "carbohydrates_g", 0) or 0,
        fats_g=_row_value(row, "fats_g", 0) or 0,
        salt_g=_row_value(row, "salt_g", 0) or 0,
        nutrition_mode=_row_value(row, "nutrition_mode", NUTRITION_MODE_RECIPE) or NUTRITION_MODE_RECIPE,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        ingredients=ingredients or [],
    )
    if recipe.uses_ingredient_nutrition:
        recipe.apply_per_person_nutrition()
    return recipe


def ingredient_from_row(row) -> Ingredient:
    return Ingredient(
        id=row["id"],
        recipe_id=row["recipe_id"],
        name=row["name"],
        amount=row["amount"],
        unit=row["unit"],
        calories_kcal=_row_value(row, "calories_kcal", 0) or 0,
        protein_g=_row_value(row, "protein_g", 0) or 0,
        carbohydrates_g=_row_value(row, "carbohydrates_g", 0) or 0,
        fats_g=_row_value(row, "fats_g", 0) or 0,
        salt_g=_row_value(row, "salt_g", 0) or 0,
    )
