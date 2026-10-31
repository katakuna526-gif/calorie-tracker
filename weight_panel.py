"""The Weight tab: log a weigh-in and see how your weight has changed."""

import tkinter as tk
from tkinter import ttk, messagebox

import stats
import trends
from charts import draw_weight_chart
from units import from_kg, to_kg, weight_unit_label


class WeightPanel(ttk.Frame):
    def __init__(self, parent, store, get_date, on_change, get_weight_unit=lambda: "kg"):
        super().__init__(parent)
        self.store = store
        self.get_date = get_date    # function returning the date currently selected in the app
        self.on_change = on_change
        self.get_weight_unit = get_weight_unit
        self.rows = []              # listbox row -> date
        self._build()

    def _build(self):
        form = ttk.LabelFrame(self, text="Log your weight")
        form.pack(fill="x", padx=10, pady=10)
        self.date_label = ttk.Label(form, text="")
        self.date_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))
        self.weight_label = ttk.Label(form, text="Weight (kg)")
        self.weight_label.grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.kg = tk.StringVar()
        entry = ttk.Entry(form, textvariable=self.kg, width=10)
        entry.grid(row=1, column=1, padx=6)
        entry.bind("<Return>", lambda e: self._save())
        ttk.Button(form, text="Save weight", command=self._save).grid(row=1, column=2, padx=8)
        ttk.Label(form, text="Tip: weigh yourself at the same time each day, e.g. in the morning. "
                             "Your calorie target and exercise estimates use your latest weight.",
                  foreground="#6b7280", wraplength=700).grid(row=2, column=0, columnspan=3,
                                                              sticky="w", padx=8, pady=(0, 8))

        self.summary = ttk.Label(self, text="", font=("TkDefaultFont", 11, "bold"))
        self.summary.pack(anchor="w", padx=14, pady=(0, 2))
        self.goal_insight = ttk.Label(self, text="", wraplength=760)
        self.goal_insight.pack(anchor="w", padx=14, pady=(0, 2))
        self.trend_text = ttk.Label(self, text="", wraplength=760)
        self.trend_text.pack(anchor="w", padx=14, pady=(0, 6))

        self.listbox = tk.Listbox(self, height=10, font=("Courier", 11), exportselection=False)
        self.listbox.pack(fill="both", expand=True, padx=14)
        ttk.Button(self, text="Remove selected", command=self._remove).pack(pady=8)

        ttk.Label(self, text="Weight trend (last 30 days)").pack(anchor="w", padx=14, pady=(4, 2))
        self.chart = tk.Canvas(self, width=760, height=190, bg="white", highlightthickness=1,
                               highlightbackground="#d1d5db")
        self.chart.pack(fill="x", padx=14, pady=(0, 10))

    def _save(self):
        try:
            kg = to_kg(float(self.kg.get()), self.get_weight_unit())
        except ValueError:
            messagebox.showerror("Weight", "Weight must be a number.")
            return
        try:
            self.store.log_weight(self.get_date(), kg)
        except ValueError as exc:
            messagebox.showerror("Weight", str(exc))
            return
        self.kg.set("")
        self.on_change()

    def _remove(self):
        sel = self.listbox.curselection()
        if sel and sel[0] < len(self.rows):
            self.store.remove_weight(self.rows[sel[0]])
            self.on_change()

    def refresh(self):
        d = self.get_date()
        unit = self.get_weight_unit()
        label = weight_unit_label(unit)
        self.weight_label.config(text=f"Weight ({label})")
        self.date_label.config(text="For: " + d.strftime("%A, %d %B %Y"))
        info = stats.weight_summary(self.store.weights)
        self.rows = [e["date"] for e in info["entries"]]
        self.listbox.delete(0, "end")
        for e in info["entries"]:
            weight = from_kg(e["kg"], unit)
            change = "" if e["change"] is None else f"   ({from_kg(e['change'], unit):+.1f})"
            self.listbox.insert("end", f"{e['date'].strftime('%d %b %Y')}   {weight:>6.1f} {label}{change}")
        self._draw_trend(d)

        if not info["entries"]:
            self.summary.config(text="No weigh-ins yet.")
            self.goal_insight.config(text="")
        elif len(info["entries"]) == 1:
            self.summary.config(text=f"Latest: {from_kg(info['latest'][1], unit):.1f} {label}")
            self.goal_insight.config(text="Log another weigh-in to compare your weight direction with your goal.")
        else:
            self.summary.config(text=(f"Latest: {from_kg(info['latest'][1], unit):.1f} {label}   |   change since "
                                      f"{info['first'][0].strftime('%d %b')}: {from_kg(info['change'], unit):+.1f} {label} "
                                      f"over {info['days']} days"))
            if self.store.profile:
                goal = stats.weight_goal_insight(self.store.weights, self.store.profile.goal)
                self.goal_insight.config(text=goal["message"] + (f" Change: {goal['change']:+.1f} kg." if goal["change"] is not None else ""))
            else:
                self.goal_insight.config(text="Set up your profile to compare weight direction with your goal.")

        if self.store.profile and self.store.profile.goal_weight_kg is not None:
            progress = stats.goal_weight_progress(self.store.weights, self.store.profile.goal_weight_kg)
            if progress:
                remaining = progress["remaining_kg"]
                relation = "to go" if remaining > 0 else "past goal" if remaining < 0 else "at goal"
                line = (f"Goal weight: {from_kg(progress['goal_kg'], unit):.1f} {label} — "
                        f"{from_kg(abs(remaining), unit):.1f} {label} {relation} | "
                        f"{progress['progress_pct']:.0f}% progress from first weigh-in")
                prior = self.goal_insight.cget("text")
                self.goal_insight.config(text=(prior + "\n" if prior else "") + line)


    def _draw_trend(self, end):
        points = stats.weight_trend(self.store.weights, end, 30)
        draw_weight_chart(self.chart, 760, 190,
                          [(p["date"], from_kg(p["kg"], self.get_weight_unit())) for p in points],
                          unit=weight_unit_label(self.get_weight_unit()))
        if self.store.profile:
            rate = trends.weight_rate(self.store.weights, end)
            self.trend_text.config(text=trends.describe_trend(
                self.store.profile, rate, unit=self.get_weight_unit())["text"])
        else:
            self.trend_text.config(text="")
