from dataclasses import dataclass, field


@dataclass
class Ingredient:
    name: str
    amount: float
    unit: str
    id: int | None = None
    recipe_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "name": self.name,
            "amount": self.amount,
            "unit": self.unit,
        }


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
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    ingredients: list[Ingredient] = field(default_factory=list)

    def to_dict(self, include_ingredients: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "instructions": self.instructions,
            "serves": self.serves,
            "prep_time_minutes": self.prep_time_minutes,
            "calories_kcal": self.calories_kcal,
            "protein_g": self.protein_g,
            "carbohydrates_g": self.carbohydrates_g,
            "fats_g": self.fats_g,
            "salt_g": self.salt_g,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_ingredients:
            data["ingredients"] = [i.to_dict() for i in self.ingredients]
        return data


def recipe_from_row(row, ingredients: list | None = None) -> Recipe:
    return Recipe(
        id=row["id"],
        name=row["name"],
        instructions=row["instructions"],
        serves=row["serves"],
        prep_time_minutes=row["prep_time_minutes"],
        calories_kcal=row["calories_kcal"],
        protein_g=row["protein_g"],
        carbohydrates_g=row["carbohydrates_g"],
        fats_g=row["fats_g"],
        salt_g=row["salt_g"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        ingredients=ingredients or [],
    )


def ingredient_from_row(row) -> Ingredient:
    return Ingredient(
        id=row["id"],
        recipe_id=row["recipe_id"],
        name=row["name"],
        amount=row["amount"],
        unit=row["unit"],
    )
