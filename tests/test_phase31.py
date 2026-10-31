import unittest
from datetime import date, timedelta

import flet as ft

from flet_ui.app import _weight_chart, build_stats_screen
from flet_ui.theme import FONT_SIZES, SPACING, palette_for
from flet_ui.viewmodels import goal_weight_progress_label


def descendants(control):
    yield control
    for child in getattr(control, "controls", []) or []:
        yield from descendants(child)
    content = getattr(control, "content", None)
    if content is not None and content is not control:
        yield from descendants(content)


class Phase31PresentationTests(unittest.TestCase):
    def test_goal_weight_distance_uses_goal_direction(self):
        self.assertEqual(goal_weight_progress_label(-10, "lose", "kg"), "10 kg to go")
        self.assertEqual(goal_weight_progress_label(10, "gain", "kg"), "10 kg to go")
        self.assertEqual(goal_weight_progress_label(2, "lose", "kg"), "2 kg past goal")
        self.assertEqual(goal_weight_progress_label(0, "gain", "kg"), "At goal")

    def test_spacing_tokens_use_four_point_scale_and_question_title_is_readable(self):
        self.assertTrue(set(SPACING.values()).issubset({4, 8, 12, 16, 20, 24}))
        self.assertEqual(FONT_SIZES["question"], 26)

    def test_weight_chart_waits_for_two_distinct_weigh_ins(self):
        today = date(2025, 1, 2)
        one_weight = {today: 85.0}
        chart = _weight_chart(one_weight, None, "kg", palette_for("dark"), today)
        self.assertIn("Log your weight on 2 days to see your trend",
                      [getattr(item, "value", None) for item in descendants(chart)])

    def test_week_stats_keeps_all_seven_weekday_positions(self):
        start = date(2025, 1, 6)
        records = [{
            "day": start + timedelta(days=index),
            "logged": index in (0, 6),
            "calories_consumed": 400 if index == 0 else (600 if index == 6 else 0),
            "calories_burned": 1800 if index == 0 else 0,
        } for index in range(7)]
        data = {
            "start": start, "title": "06 Jan – 12 Jan 2025", "days_logged": 2,
            "days_in_range": 7, "has_profile": True, "records": records,
            "protein_avg": 80.4, "carbs_avg": 120.6, "fat_avg": 52.3,
            "adherence": None, "insights": None,
        }
        screen = build_stats_screen(data, palette_for("dark"), "week", lambda *_: None,
                                    lambda *_: None, lambda *_: None)
        labels = [item.value for item in descendants(screen)
                  if isinstance(item, ft.Text) and item.value in list("MTWTFSS")]
        self.assertEqual(labels[:7], list("MTWTFSS"))


if __name__ == "__main__":
    unittest.main()
