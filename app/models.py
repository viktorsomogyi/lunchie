from dataclasses import dataclass, field

NUTRITION_FIELDS = ("calories_kcal", "protein_g", "carbohydrates_g", "fats_g", "salt_g", "fiber_g")
NUTRITION_MODE_RECIPE = "recipe"
NUTRITION_MODE_INGREDIENT = "ingredient"

# Convert amount into a comparable base unit within the same family.
_UNIT_TO_BASE = {
    "g": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "ml": ("volume", 1.0),
    "l": ("volume", 1000.0),
    "pcs": ("count", 1.0),
    "tsp": ("spoon", 1.0),
    "tbsp": ("spoon", 3.0),
}


def _nutrition_values(obj) -> dict[str, float]:
    return {name: float(getattr(obj, name) or 0) for name in NUTRITION_FIELDS}


def round_nutrition(value: float) -> float:
    return round(float(value or 0), 2)


def scale_factor(amount: float, unit: str, base_amount: float, base_unit: str) -> float:
    """How many catalog bases fit into the recipe amount."""
    amount = float(amount or 0)
    base_amount = float(base_amount or 0)
    if amount <= 0 or base_amount <= 0:
        return 0.0
    src = _UNIT_TO_BASE.get(unit)
    dst = _UNIT_TO_BASE.get(base_unit)
    if src is None or dst is None:
        return 0.0
    src_family, src_mul = src
    dst_family, dst_mul = dst
    if src_family != dst_family:
        # Incompatible units: only allow exact unit match.
        if unit != base_unit:
            return 0.0
        return amount / base_amount
    amount_base = amount * src_mul
    catalog_base = base_amount * dst_mul
    if catalog_base <= 0:
        return 0.0
    return amount_base / catalog_base


@dataclass
class FoodItem:
    """Shared ingredient catalog entry with nutrition per base_amount of base_unit."""

    name: str
    base_amount: float = 100.0
    base_unit: str = "g"
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbohydrates_g: float = 0.0
    fats_g: float = 0.0
    salt_g: float = 0.0
    fiber_g: float = 0.0
    product_link: str = ""
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def nutrition_for_amount(self, amount: float, unit: str) -> dict[str, float]:
        factor = scale_factor(amount, unit, self.base_amount, self.base_unit)
        return {name: round_nutrition(value * factor) for name, value in _nutrition_values(self).items()}

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "base_amount": self.base_amount,
            "base_unit": self.base_unit,
            "product_link": self.product_link,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        data.update(_nutrition_values(self))
        return data


@dataclass
class RecipeItem:
    """One food item used in a recipe, with recipe-specific amount."""

    amount: float
    unit: str
    food_item: FoodItem | None = None
    food_item_id: int | None = None
    id: int | None = None
    recipe_id: int | None = None

    @property
    def name(self) -> str:
        if self.food_item:
            return self.food_item.name
        return ""

    def line_nutrition(self) -> dict[str, float]:
        if not self.food_item:
            return {name: 0.0 for name in NUTRITION_FIELDS}
        return self.food_item.nutrition_for_amount(self.amount, self.unit)

    def to_dict(self) -> dict:
        nutrition = self.line_nutrition()
        data = {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "food_item_id": self.food_item_id or (self.food_item.id if self.food_item else None),
            "name": self.name,
            "amount": self.amount,
            "unit": self.unit,
            "base_amount": self.food_item.base_amount if self.food_item else None,
            "base_unit": self.food_item.base_unit if self.food_item else None,
            "product_link": self.food_item.product_link if self.food_item else "",
        }
        data.update(nutrition)
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
    fiber_g: float = 0.0
    nutrition_mode: str = NUTRITION_MODE_RECIPE
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    ingredients: list[RecipeItem] = field(default_factory=list)

    @property
    def uses_ingredient_nutrition(self) -> bool:
        return self.nutrition_mode == NUTRITION_MODE_INGREDIENT

    def total_nutrition(self) -> dict[str, float]:
        totals = {name: 0.0 for name in NUTRITION_FIELDS}
        for item in self.ingredients:
            for name, value in item.line_nutrition().items():
                totals[name] += value
        return {name: round_nutrition(value) for name, value in totals.items()}

    def per_person_nutrition(self) -> dict[str, float]:
        if self.uses_ingredient_nutrition:
            serves = max(int(self.serves or 1), 1)
            totals = self.total_nutrition()
            return {name: round_nutrition(value / serves) for name, value in totals.items()}
        return {name: round_nutrition(value) for name, value in _nutrition_values(self).items()}

    def apply_per_person_nutrition(self) -> None:
        for name, value in self.per_person_nutrition().items():
            setattr(self, name, value)

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


def food_item_from_row(row) -> FoodItem:
    return FoodItem(
        id=row["id"],
        name=row["name"],
        base_amount=_row_value(row, "base_amount", 100) or 100,
        base_unit=_row_value(row, "base_unit", "g") or "g",
        calories_kcal=_row_value(row, "calories_kcal", 0) or 0,
        protein_g=_row_value(row, "protein_g", 0) or 0,
        carbohydrates_g=_row_value(row, "carbohydrates_g", 0) or 0,
        fats_g=_row_value(row, "fats_g", 0) or 0,
        salt_g=_row_value(row, "salt_g", 0) or 0,
        fiber_g=_row_value(row, "fiber_g", 0) or 0,
        product_link=_row_value(row, "product_link", "") or "",
        created_at=_row_value(row, "created_at"),
        updated_at=_row_value(row, "updated_at"),
    )


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
        fiber_g=_row_value(row, "fiber_g", 0) or 0,
        nutrition_mode=_row_value(row, "nutrition_mode", NUTRITION_MODE_RECIPE) or NUTRITION_MODE_RECIPE,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        ingredients=ingredients or [],
    )
    if recipe.uses_ingredient_nutrition:
        recipe.apply_per_person_nutrition()
    return recipe


def recipe_item_from_row(row, food_item: FoodItem | None = None) -> RecipeItem:
    item = food_item or food_item_from_row(row)
    return RecipeItem(
        id=_row_value(row, "item_id") or _row_value(row, "id"),
        recipe_id=_row_value(row, "recipe_id"),
        food_item_id=_row_value(row, "food_item_id") or item.id,
        amount=_row_value(row, "amount", 0) or 0,
        unit=_row_value(row, "unit", "g") or "g",
        food_item=item,
    )
