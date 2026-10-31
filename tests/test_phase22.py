import unittest
from datetime import date

import questions as Q
import stats
from calorie_engine import DailyLog, ExerciseEntry, FoodEntry, Person


class Phase22Tests(unittest.TestCase):
    def test_optional_answers_may_be_missing(self):
        answers = {"name": "Alex", "age": 25, "sex": "male", "height_cm": 175.0,
                   "weight_kg": 70.0, "activity_level": "moderate",
                   "goal": "lose", "pace": "steady"}
        person = Q.person_from_answers(answers)
        self.assertIsNone(person.goal_weight_kg)
        self.assertIsNone(person.custom_calorie_target)

    def test_required_answers_still_required(self):
        with self.assertRaises(ValueError):
            Q.person_from_answers({"name": "A", "age": 25})

    def test_exercise_minutes_are_counted(self):
        d = date(2026, 1, 5)
        log = DailyLog(log_date=d,
                       foods=[FoodEntry("rice", 100, 130)],
                       exercises=[ExerciseEntry("walk", 30, 100), ExerciseEntry("run", 20, 200)])
        person = Person("A", 30, "male", 70, 175)
        recs = stats.daily_records(person, {d: log}, d, d)
        self.assertEqual(recs[0]["exercise_minutes"], 50.0)
        ins = stats.progress_insights(recs, lambda day: 2000)
        self.assertEqual(ins["exercise_minutes"], 50.0)


if __name__ == "__main__":
    unittest.main()
