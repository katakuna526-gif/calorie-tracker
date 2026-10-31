"""Food database: built-in foods, search, serving sizes and custom foods.

Values are typical averages per 100 g, rounded from common nutrition tables.
Prepared dishes (dosa, poha, pizza...) vary a lot by recipe, so treat them as
estimates and add your own custom food if you know the exact numbers.

No UI code here, so everything can be tested without opening a window.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from calorie_engine import MAX_GRAMS, MEALS, FoodEntry, check_nutrition_values


@dataclass
class FoodItem:
    name: str
    calories_per_100g: float
    protein_per_100g: float = 0.0
    carbs_per_100g: float = 0.0
    fat_per_100g: float = 0.0
    servings: Dict[str, float] = field(default_factory=dict)  # label -> grams, e.g. {"1 roti": 40}
    aliases: List[str] = field(default_factory=list)
    custom: bool = False

    def __post_init__(self):
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValueError("Food name cannot be empty.")
        check_nutrition_values(self.calories_per_100g, self.protein_per_100g,
                               self.carbs_per_100g, self.fat_per_100g)
        for label, grams in self.servings.items():
            if not (0 < grams <= MAX_GRAMS):
                raise ValueError(f"Serving '{label}' must be between 0 and {MAX_GRAMS:g} g.")

    def to_entry(self, grams: float, meal: str) -> FoodEntry:
        return FoodEntry(
            name=self.name, grams=grams,
            calories_per_100g=self.calories_per_100g,
            protein_per_100g=self.protein_per_100g,
            carbs_per_100g=self.carbs_per_100g,
            fat_per_100g=self.fat_per_100g,
            meal=meal,
        )


def _f(name, kcal, protein, carbs, fat, servings=None, aliases=None):
    return FoodItem(name, kcal, protein, carbs, fat, servings or {}, aliases or [])


BUILTIN_FOODS: List[FoodItem] = [
    # Grains and breads
    _f("Roti / chapati (whole wheat)", 297, 9.8, 49.0, 7.5, {"1 roti": 40}, ["chapati", "roti", "phulka"]),
    _f("Rice, white, cooked", 130, 2.7, 28.2, 0.3, {"1 cup": 158, "1 bowl": 150}, ["chawal", "steamed rice"]),
    _f("Rice, brown, cooked", 123, 2.7, 25.6, 1.0, {"1 cup": 195}),
    _f("Pasta, cooked", 158, 5.8, 30.9, 0.9, {"1 cup": 140}, ["noodles", "spaghetti", "macaroni"]),
    _f("Quinoa, cooked", 120, 4.4, 21.3, 1.9, {"1 cup": 185}),
    _f("Oats, dry", 389, 16.9, 66.3, 6.9, {"1 serving": 40}, ["oatmeal", "porridge"]),
    _f("Bread, white", 265, 9.0, 49.0, 3.2, {"1 slice": 25}),
    _f("Bread, whole wheat", 247, 13.0, 41.0, 3.4, {"1 slice": 28}, ["brown bread"]),
    _f("Idli", 148, 4.5, 30.0, 0.4, {"1 idli": 39}),
    _f("Dosa, plain", 168, 3.9, 29.0, 3.7, {"1 dosa": 85}),
    _f("Poha (cooked)", 130, 2.6, 25.0, 2.0, {"1 bowl": 150}, ["flattened rice"]),
    # Protein foods
    _f("Chicken breast, cooked", 165, 31.0, 0.0, 3.6, {"1 breast": 120}, ["chicken"]),
    _f("Egg, whole, boiled", 155, 12.6, 1.1, 10.6, {"1 egg": 50}, ["egg", "anda", "boiled egg"]),
    _f("Paneer", 265, 18.3, 1.2, 20.8, {"1 cube": 25}, ["cottage cheese"]),
    _f("Tofu", 76, 8.1, 1.9, 4.8, {"1 slice": 85}),
    _f("Salmon, cooked", 206, 22.1, 0.0, 12.4, {"1 fillet": 150}, ["fish"]),
    # Lentils and beans
    _f("Dal / lentils, boiled (plain)", 116, 9.0, 20.1, 0.4, {"1 bowl": 150}, ["dal", "daal", "lentils", "toor dal", "moong dal"]),
    _f("Chickpeas, boiled", 164, 8.9, 27.4, 2.6, {"1 cup": 164}, ["chana", "chole", "garbanzo"]),
    _f("Rajma (kidney beans), boiled", 127, 8.7, 22.8, 0.5, {"1 cup": 177}, ["rajma", "kidney beans"]),
    # Dairy
    _f("Milk, whole", 61, 3.2, 4.8, 3.3, {"1 glass (250 ml)": 258}, ["doodh"]),
    _f("Yogurt / curd, plain", 61, 3.5, 4.7, 3.3, {"1 bowl": 150}, ["curd", "dahi", "yoghurt"]),
    _f("Cheese, cheddar", 403, 24.9, 1.3, 33.1, {"1 slice": 28}),
    # Fruit
    _f("Banana", 89, 1.1, 22.8, 0.3, {"1 medium": 118}, ["kela"]),
    _f("Apple", 52, 0.3, 13.8, 0.2, {"1 medium": 182}, ["seb"]),
    _f("Orange", 47, 0.9, 11.8, 0.1, {"1 medium": 131}, ["santra"]),
    _f("Mango", 60, 0.8, 15.0, 0.4, {"1 cup, sliced": 165}, ["aam"]),
    _f("Avocado", 160, 2.0, 8.5, 14.7, {"1 avocado": 150}),
    # Vegetables
    _f("Potato, boiled", 87, 1.9, 20.1, 0.1, {"1 medium": 150}, ["aloo"]),
    _f("Broccoli, boiled", 35, 2.4, 7.2, 0.4, {"1 cup": 156}),
    _f("Spinach, cooked", 23, 3.0, 3.8, 0.3, {"1 cup": 180}, ["palak"]),
    _f("Tomato", 18, 0.9, 3.9, 0.2, {"1 medium": 123}, ["tamatar"]),
    _f("Onion", 40, 1.1, 9.3, 0.1, {"1 medium": 110}, ["pyaaz"]),
    _f("Carrot", 41, 0.9, 9.6, 0.2, {"1 medium": 61}, ["gajar"]),
    _f("Cucumber", 15, 0.7, 3.6, 0.1, {"1 medium": 200}, ["kheera"]),
    # Nuts, fats and sweeteners
    _f("Almonds", 579, 21.2, 21.6, 49.9, {"10 almonds": 12}, ["badam"]),
    _f("Cashews", 553, 18.2, 30.2, 43.9, {"10 cashews": 15}, ["kaju"]),
    _f("Peanuts", 567, 25.8, 16.1, 49.2, {"1 handful": 28}, ["moongfali"]),
    _f("Peanut butter", 588, 25.1, 20.0, 50.4, {"1 tbsp": 16}),
    _f("Olive oil", 884, 0.0, 0.0, 100.0, {"1 tbsp": 13.5, "1 tsp": 4.5}, ["oil", "cooking oil"]),
    _f("Ghee", 876, 0.3, 0.0, 99.5, {"1 tsp": 5, "1 tbsp": 14}, ["clarified butter"]),
    _f("Butter", 717, 0.9, 0.1, 81.1, {"1 tsp": 5, "1 tbsp": 14}),
    _f("Sugar", 387, 0.0, 100.0, 0.0, {"1 tsp": 4}, ["cheeni"]),
    _f("Honey", 304, 0.3, 82.4, 0.0, {"1 tsp": 7, "1 tbsp": 21}, ["shahad"]),
    # Snacks and drinks
    _f("Pizza, cheese", 266, 11.0, 33.0, 10.0, {"1 slice": 107}),
    _f("Chocolate, milk", 535, 7.7, 59.4, 29.7, {"1 bar": 45}),
    _f("Cola", 42, 0.0, 10.6, 0.0, {"1 can (330 ml)": 340}, ["soda", "coke", "soft drink"]),
]


def default_meal(now: Optional[datetime] = None) -> str:
    """Guess the meal from the time of day."""
    hour = (now or datetime.now()).hour
    if hour < 11:
        return "breakfast"
    if hour < 16:
        return "lunch"
    if hour < 21:
        return "dinner"
    return "snacks"


def grams_for(quantity: float, serving_grams: float = 1.0) -> float:
    """quantity x serving size. For plain grams, serving_grams is 1."""
    if not (quantity > 0):
        raise ValueError("Amount must be greater than 0.")
    return quantity * serving_grams


class FoodDatabase:
    """Built-in foods plus the person's own custom foods."""

    def __init__(self, custom: Iterable[FoodItem] = ()):
        self.custom: List[FoodItem] = []
        for item in custom:
            self.custom.append(item)

    @property
    def items(self) -> List[FoodItem]:
        return self.custom + BUILTIN_FOODS

    def get(self, name: str) -> Optional[FoodItem]:
        key = name.strip().lower()
        for item in self.items:
            if item.name.lower() == key:
                return item
        return None

    def add_custom(self, item: FoodItem) -> None:
        if self.get(item.name):
            raise ValueError(f"A food called '{item.name}' already exists.")
        item.custom = True
        self.custom.append(item)

    def search(self, query: str, limit: int = 12) -> List[FoodItem]:
        """Best matches first: exact, then starts-with, then word-starts-with, then contains."""
        q = query.strip().lower()
        if not q:
            return []
        tokens = q.split()
        scored = []
        for position, item in enumerate(self.items):
            best = 0
            for text in [item.name] + item.aliases:
                text = text.lower()
                words = text.replace(",", " ").replace("(", " ").replace(")", " ").replace("/", " ").split()
                if text == q:
                    score = 100
                elif text.startswith(q):
                    score = 80
                elif any(w.startswith(q) for w in words):
                    score = 60
                elif all(t in text for t in tokens):
                    score = 40
                else:
                    score = 0
                best = max(best, score)
            if best:
                scored.append((-(best + (5 if item.custom else 0)), position, item))
        scored.sort(key=lambda row: row[:2])
        return [row[2] for row in scored[:limit]]

    def suggestions(self, favorites: Iterable[str], recents: Iterable[str]) -> List[FoodItem]:
        """What to show before the person types: favorites first, then recent foods."""
        out, seen = [], set()
        for name in list(favorites) + list(recents):
            item = self.get(name)
            if item and item.name not in seen:
                seen.add(item.name)
                out.append(item)
        return out
