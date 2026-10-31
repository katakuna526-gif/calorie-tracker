"""Calorie engine: all the math, no UI.

Burn model (avoids double counting):
    baseline burn = BMR x 1.2   (resting + normal daily living, no workouts)
    total burn    = baseline burn + logged exercise calories
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

BASELINE_MULTIPLIER = 1.2

ACTIVITY_LEVELS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "high": 1.725,
    "very_high": 1.9,
}

MEALS = ("breakfast", "lunch", "dinner", "snacks")
MEAL_LABELS = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "snacks": "Snacks"}

# Sanity limits. They stop typos like "4434 g" or "045 g protein" from wrecking the totals.
MAX_GRAMS = 5000            # one food entry
MAX_KCAL_PER_100G = 900     # pure fat is 9 kcal per gram
MAX_EXERCISE_KCAL = 10000   # one exercise entry
MIN_WEIGHT_KG = 30
MAX_WEIGHT_KG = 300
SOFT_WARN_KCAL_PER_HOUR = 1000  # above this we ask "are you sure?" instead of refusing

GOALS = ("lose", "maintain", "gain")

# Calories per day added to / removed from the maintenance estimate.
PACE_ADJUSTMENT = {"gentle": 250, "steady": 500}

# Targets are never set below these, however the goal is chosen.
MIN_CALORIES = {"male": 1500, "female": 1200}


@dataclass
class Person:
    name: str
    age: int
    sex: str  # "male" or "female"
    weight_kg: float
    height_cm: float
    activity_level: str = "sedentary"
    goal: str = "maintain"   # lose, maintain or gain
    pace: str = "gentle"     # gentle or steady (ignored when maintaining)
    goal_weight_kg: Optional[float] = None
    custom_calorie_target: Optional[float] = None
    custom_protein_target: Optional[float] = None
    custom_carbs_target: Optional[float] = None
    custom_fat_target: Optional[float] = None

    def __post_init__(self):
        if self.sex.lower() not in ("male", "female"):
            raise ValueError("Sex must be 'male' or 'female'.")
        if self.activity_level.lower() not in ACTIVITY_LEVELS:
            raise ValueError("Unknown activity level.")
        if self.goal not in GOALS:
            raise ValueError("Goal must be lose, maintain or gain.")
        if self.pace not in PACE_ADJUSTMENT:
            raise ValueError("Pace must be gentle or steady.")
        if self.age <= 0 or self.weight_kg <= 0 or self.height_cm <= 0:
            raise ValueError("Age, weight and height must be positive.")
        for label, value, low, high in (
            ("Goal weight", self.goal_weight_kg, MIN_WEIGHT_KG, MAX_WEIGHT_KG),
            ("Custom calorie target", self.custom_calorie_target, 500, 10000),
            ("Custom protein target", self.custom_protein_target, 0, 1000),
            ("Custom carbs target", self.custom_carbs_target, 0, 1500),
            ("Custom fat target", self.custom_fat_target, 0, 1000),
        ):
            if value is not None and not (low <= value <= high):
                raise ValueError(f"{label} must be between {low:g} and {high:g}.")


def check_nutrition_values(calories: float, protein: float, carbs: float, fat: float) -> None:
    """Reject per-100 g values that cannot exist in real food.

    Pure fat is the densest food at 9 kcal per gram (900 per 100 g), and
    protein + carbs + fat can never weigh more than the 100 g they came from.
    """
    for label, value in (("Calories", calories), ("Protein", protein),
                         ("Carbs", carbs), ("Fat", fat)):
        if not (0 <= value):  # also rejects nan
            raise ValueError(f"{label} cannot be negative.")
    if calories > MAX_KCAL_PER_100G:
        raise ValueError(f"Calories per 100 g cannot be more than {MAX_KCAL_PER_100G:g}.")
    for label, value in (("Protein", protein), ("Carbs", carbs), ("Fat", fat)):
        if value > 100:
            raise ValueError(f"{label} per 100 g cannot be more than 100 g.")
    if protein + carbs + fat > 100.5:
        raise ValueError("Protein + carbs + fat cannot add up to more than 100 g per 100 g of food.")


@dataclass
class FoodEntry:
    name: str
    grams: float
    calories_per_100g: float
    protein_per_100g: float = 0.0
    carbs_per_100g: float = 0.0
    fat_per_100g: float = 0.0
    meal: str = "snacks"

    def __post_init__(self):
        if not (0 < self.grams <= MAX_GRAMS):
            raise ValueError(f"Grams must be between 0 and {MAX_GRAMS:g}.")
        check_nutrition_values(self.calories_per_100g, self.protein_per_100g,
                               self.carbs_per_100g, self.fat_per_100g)
        if self.meal not in MEALS:
            raise ValueError("Meal must be breakfast, lunch, dinner or snacks.")

    def _scale(self, per_100g: float) -> float:
        return self.grams / 100 * per_100g

    @property
    def calories(self) -> float:
        return self._scale(self.calories_per_100g)

    @property
    def protein(self) -> float:
        return self._scale(self.protein_per_100g)

    @property
    def carbs(self) -> float:
        return self._scale(self.carbs_per_100g)

    @property
    def fat(self) -> float:
        return self._scale(self.fat_per_100g)


@dataclass
class ExerciseEntry:
    name: str
    duration_minutes: float
    calories_burned: float

    def __post_init__(self):
        if not (0 < self.duration_minutes <= 1440):
            raise ValueError("Duration must be between 0 and 1440 minutes (one day).")
        if not (0 <= self.calories_burned <= MAX_EXERCISE_KCAL):
            raise ValueError(f"Calories burned must be between 0 and {MAX_EXERCISE_KCAL:g}.")


@dataclass
class DailyLog:
    log_date: date = field(default_factory=date.today)
    foods: List[FoodEntry] = field(default_factory=list)
    exercises: List[ExerciseEntry] = field(default_factory=list)


def calculate_bmr(person: Person) -> float:
    """Mifflin-St Jeor equation (an estimate, not a medical measurement)."""
    base = 10 * person.weight_kg + 6.25 * person.height_cm - 5 * person.age
    base += 5 if person.sex.lower() == "male" else -161
    return round(base, 2)


def calculate_tdee(person: Person) -> float:
    """BMR x the person's usual activity multiplier (shown for reference)."""
    return round(calculate_bmr(person) * ACTIVITY_LEVELS[person.activity_level.lower()], 2)


def calculate_baseline_burn(person: Person) -> float:
    return round(calculate_bmr(person) * BASELINE_MULTIPLIER, 2)


def calculate_food_totals(log: DailyLog) -> dict:
    return {
        "calories": round(sum(f.calories for f in log.foods), 2),
        "protein_g": round(sum(f.protein for f in log.foods), 2),
        "carbs_g": round(sum(f.carbs for f in log.foods), 2),
        "fat_g": round(sum(f.fat for f in log.foods), 2),
    }


def calculate_exercise_burn(log: DailyLog) -> float:
    return round(sum(e.calories_burned for e in log.exercises), 2)


def calculate_daily_summary(person: Person, log: DailyLog) -> dict:
    food = calculate_food_totals(log)
    baseline = calculate_baseline_burn(person)
    exercise = calculate_exercise_burn(log)
    burned = round(baseline + exercise, 2)
    return {
        "date": str(log.log_date),
        "calories_consumed": food["calories"],
        "calories_burned": burned,
        "baseline_burn": baseline,
        "exercise_calories": exercise,
        "calorie_balance": round(food["calories"] - burned, 2),
        "bmr": calculate_bmr(person),
        "tdee": calculate_tdee(person),
        "protein_g": food["protein_g"],
        "carbs_g": food["carbs_g"],
        "fat_g": food["fat_g"],
    }


def calculate_targets(person: Person) -> dict:
    """Daily calorie and macro targets from the person's goal.

    Starts from TDEE (BMR x usual activity), adds or removes the pace
    adjustment, and never goes below a minimum calorie floor.
    Macros: protein by body weight, fat 25% of calories, carbs the rest.
    """
    tdee = calculate_tdee(person)
    if person.goal == "lose":
        adjustment = -PACE_ADJUSTMENT[person.pace]
    elif person.goal == "gain":
        adjustment = PACE_ADJUSTMENT[person.pace]
    else:
        adjustment = 0

    raw = tdee + adjustment
    floor = MIN_CALORIES[person.sex.lower()]
    calories = (person.custom_calorie_target if person.custom_calorie_target is not None
                else max(raw, floor))

    protein_g = (person.custom_protein_target if person.custom_protein_target is not None
                 else person.weight_kg * (1.2 if person.goal == "maintain" else 1.6))
    fat_g = (person.custom_fat_target if person.custom_fat_target is not None
             else calories * 0.25 / 9)
    carbs_g = (person.custom_carbs_target if person.custom_carbs_target is not None
               else max(0.0, (calories - protein_g * 4 - fat_g * 9) / 4))

    return {
        "calories": round(calories),
        "protein_g": round(protein_g),
        "carbs_g": round(carbs_g),
        "fat_g": round(fat_g),
        "adjustment": adjustment,
        "floor_applied": person.custom_calorie_target is None and raw < floor,
    }


def calculate_meal_totals(log: DailyLog) -> dict:
    """Calories eaten at each meal, e.g. {"breakfast": 320.0, "lunch": 0.0, ...}."""
    totals = {meal: 0.0 for meal in MEALS}
    for food in log.foods:
        totals[food.meal] += food.calories
    return {meal: round(kcal, 2) for meal, kcal in totals.items()}


def calculate_exercise_calories(met: float, weight_kg: float, minutes: float) -> float:
    """Extra calories burned by an activity, on top of resting.

    MET = how many times your resting energy use an activity takes. Resting is
    1 MET, and the daily "baseline" burn already covers resting, so only the
    extra counts here:  (MET - 1) x weight in kg x hours.
    This is an estimate: real burn varies with fitness, technique and terrain.
    """
    if not (met >= 1):
        raise ValueError("MET must be at least 1.")
    if not (MIN_WEIGHT_KG <= weight_kg <= MAX_WEIGHT_KG):
        raise ValueError(f"Weight must be between {MIN_WEIGHT_KG} and {MAX_WEIGHT_KG} kg.")
    if not (0 < minutes <= 1440):
        raise ValueError("Duration must be between 0 and 1440 minutes (one day).")
    return round((met - 1) * weight_kg * minutes / 60, 1)


def is_unusually_high_burn(minutes: float, calories: float) -> bool:
    """True if the burn rate is far above normal. Used to ask for confirmation, not to refuse."""
    return minutes > 0 and calories / (minutes / 60) > SOFT_WARN_KCAL_PER_HOUR
