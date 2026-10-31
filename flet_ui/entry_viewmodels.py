"""Input parsing and previews for the Flet food and activity forms."""

from calorie_engine import ExerciseEntry, FoodEntry
from exercises import estimate_calories


def make_food_entry(name, grams, calories_per_100g, protein_per_100g,
                    carbs_per_100g, fat_per_100g, meal):
    """Parse user-entered values through the same validation as the desktop app."""
    return FoodEntry(
        name=(name or "").strip(),
        grams=float(grams),
        calories_per_100g=float(calories_per_100g),
        protein_per_100g=float(protein_per_100g or 0),
        carbs_per_100g=float(carbs_per_100g or 0),
        fat_per_100g=float(fat_per_100g or 0),
        meal=meal,
    )


def make_exercise_entry(name, minutes, weight_kg, intensity="moderate", manual_calories=None):
    """Create an activity record using catalog estimates or a manually known burn."""
    duration = float(minutes)
    if manual_calories is None:
        calories = estimate_calories(name, intensity, float(weight_kg), duration)
    else:
        calories = float(manual_calories)
    return ExerciseEntry(name=name.strip(), duration_minutes=duration, calories_burned=calories)
