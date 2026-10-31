import unittest
from datetime import date

from calorie_engine import (
    Person, FoodEntry, ExerciseEntry, DailyLog,
    calculate_bmr, calculate_tdee, calculate_baseline_burn,
    calculate_food_totals, calculate_exercise_burn, calculate_daily_summary,
)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.alex = Person("Alex", 25, "male", 70, 175, "moderate")

    def test_bmr_male(self):
        self.assertEqual(calculate_bmr(self.alex), 1673.75)

    def test_bmr_female(self):
        self.assertEqual(calculate_bmr(Person("Sam", 30, "female", 60, 165)), 1320.25)

    def test_tdee_and_baseline(self):
        self.assertEqual(calculate_tdee(self.alex), round(1673.75 * 1.55, 2))
        self.assertEqual(calculate_baseline_burn(self.alex), round(1673.75 * 1.2, 2))

    def test_food_per_100g(self):
        chicken = FoodEntry("Chicken", 150, 165, 31, 0, 3.6)
        self.assertAlmostEqual(chicken.calories, 247.5)
        self.assertAlmostEqual(chicken.protein, 46.5)
        self.assertAlmostEqual(chicken.fat, 5.4)

    def test_food_totals(self):
        log = DailyLog(date(2026, 10, 3))
        log.foods.append(FoodEntry("Roti", 100, 200, 6, 40, 3))
        log.foods.append(FoodEntry("Rice", 200, 130, 2.7, 28, 0.3))
        t = calculate_food_totals(log)
        self.assertEqual(t["calories"], 460)
        self.assertEqual(t["carbs_g"], 96)

    def test_exercise_burn(self):
        log = DailyLog()
        log.exercises += [ExerciseEntry("Walk", 45, 180), ExerciseEntry("Run", 20, 200)]
        self.assertEqual(calculate_exercise_burn(log), 380)

    def test_daily_summary_balance(self):
        log = DailyLog(date(2026, 10, 3))
        log.foods.append(FoodEntry("Roti", 100, 200))
        log.exercises.append(ExerciseEntry("Walk", 45, 180))
        s = calculate_daily_summary(self.alex, log)
        baseline = round(1673.75 * 1.2, 2)
        self.assertEqual(s["calories_burned"], round(baseline + 180, 2))
        self.assertEqual(s["calorie_balance"], round(200 - (baseline + 180), 2))

    def test_empty_log(self):
        s = calculate_daily_summary(self.alex, DailyLog())
        self.assertEqual(s["calories_consumed"], 0)
        self.assertEqual(s["exercise_calories"], 0)

    def test_bad_food(self):
        for kw in (dict(name="x", grams=0, calories_per_100g=100),
                   dict(name="x", grams=-5, calories_per_100g=100),
                   dict(name="x", grams=100, calories_per_100g=-1)):
            with self.assertRaises(ValueError):
                FoodEntry(**kw)

    def test_bad_person_and_exercise(self):
        with self.assertRaises(ValueError):
            Person("x", 25, "other", 70, 175)
        with self.assertRaises(ValueError):
            Person("x", 25, "male", 70, 175, "extreme")
        with self.assertRaises(ValueError):
            ExerciseEntry("x", 0, 100)


if __name__ == "__main__":
    unittest.main()
