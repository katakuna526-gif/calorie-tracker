"""Step-by-step setup window. It shows one question at a time from questions.py."""
import tkinter as tk
from tkinter import ttk
import questions as Q
from units import from_kg, to_kg

class Wizard(tk.Toplevel):
    def __init__(self, parent, answers=None, on_done=None, on_cancel=None, weight_unit="kg"):
        super().__init__(parent); self.title("Set up your profile"); self.geometry("520x440")
        self.weight_unit = weight_unit
        self.transient(parent); self.grab_set(); self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.answers=dict(answers or {}); self.on_done=on_done; self.on_cancel=on_cancel; self.index=0; self.var=tk.StringVar()
        self.progress=ttk.Label(self,text="",foreground="#6b7280"); self.progress.pack(anchor="w",padx=20,pady=(16,0))
        self.prompt=ttk.Label(self,text="",font=("TkDefaultFont",14,"bold"),wraplength=470); self.prompt.pack(anchor="w",padx=20,pady=(6,10))
        self.body=ttk.Frame(self); self.body.pack(fill="x",padx=20)
        self.help=ttk.Label(self,text="",foreground="#6b7280",wraplength=470); self.help.pack(anchor="w",padx=20,pady=(10,0))
        self.error=ttk.Label(self,text="",foreground="#b91c1c",wraplength=470); self.error.pack(anchor="w",padx=20,pady=(6,0))
        buttons=ttk.Frame(self); buttons.pack(side="bottom",fill="x",padx=20,pady=16)
        self.back_btn=ttk.Button(buttons,text="Back",command=self._back); self.back_btn.pack(side="left")
        self.next_btn=ttk.Button(buttons,text="Next",command=self._next); self.next_btn.pack(side="right")
        ttk.Button(buttons,text="Cancel",command=self._cancel).pack(side="right",padx=8); self._show()
    def _current(self):
        visible=Q.visible_questions(self.answers); return visible,self._safe_question(visible)
    def _safe_question(self, visible):
        if self.index >= len(visible): self.index=max(0,len(visible)-1)
        return visible[self.index]
    def _show(self):
        visible,q=self._current(); self.progress.config(text=f"Question {self.index+1} of {len(visible)}")
        self.prompt.config(text=q["prompt"]); self.help.config(text=q.get("help","")); self.error.config(text="")
        self.back_btn.state(["!disabled"] if self.index>0 else ["disabled"]); self.next_btn.config(text="Finish" if self.index==len(visible)-1 else "Next")
        for child in self.body.winfo_children(): child.destroy()
        saved=self.answers.get(q["key"])
        if q["type"]=="choice":
            self.var.set(saved if saved is not None else "")
            for value,label in q["choices"]: ttk.Radiobutton(self.body,text=label,value=value,variable=self.var).pack(anchor="w",pady=3)
        else:
            value = saved
            if value is not None and self.weight_unit == "lb" and q["key"] in ("weight_kg", "goal_weight_kg"):
                value = round(from_kg(float(value), "lb"), 1)
            self.var.set(str(value) if value is not None else q.get("default","")); row=ttk.Frame(self.body); row.pack(anchor="w")
            entry=ttk.Entry(row,textvariable=self.var,width=24); entry.pack(side="left"); entry.focus_set(); entry.bind("<Return>",lambda e:self._next())
            unit = q.get("unit", "")
            if self.weight_unit == "lb" and q["key"] in ("weight_kg", "goal_weight_kg"):
                unit = unit.replace("kg", "lb")
            if unit: ttk.Label(row,text=unit).pack(side="left",padx=6)
    def _next(self):
        _,q=self._current(); raw=self.var.get()
        if self.weight_unit == "lb" and q["key"] in ("weight_kg", "goal_weight_kg") and raw.strip():
            try: raw = str(to_kg(float(raw), "lb"))
            except ValueError: pass
        value,problem=Q.validate_answer(q,raw)
        if problem: self.error.config(text=problem); return
        self.answers[q["key"]]=value; visible=Q.visible_questions(self.answers)
        if self.index+1 < len(visible): self.index+=1; self._show(); return
        try: person=Q.person_from_answers(self.answers)
        except ValueError as exc: self.error.config(text=str(exc)); return
        self.destroy()
        if self.on_done: self.on_done(person)
    def _back(self):
        if self.index>0: self.index-=1; self._show()
    def _cancel(self):
        self.destroy()
        if self.on_cancel: self.on_cancel()
