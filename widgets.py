"""
Reusable UI components: Card, StatCard, TaskRow.
"""

import tkinter as tk
from datetime import datetime

from config import COLORS


# ============================================================
#  Card — Floating surface with visible edge
# ============================================================
class Card(tk.Frame):
    """Floating card — lifted surface with visible edge."""

    def __init__(self, parent, title="", icon="", pad=20, **kw):
        super().__init__(parent, bg=COLORS["bg_card"], padx=pad, pady=pad, **kw)
        # 2px bright border for floating effect
        self.configure(highlightbackground=COLORS["border"], highlightthickness=2)
        if title:
            h = tk.Frame(self, bg=COLORS["bg_card"])
            h.pack(fill="x", pady=(0, pad - 8))
            tk.Label(h, text=f"{icon}  {title}", font=("Segoe UI", 13, "bold"),
                     bg=COLORS["bg_card"], fg=COLORS["text_main"]).pack(anchor="w")
            tk.Frame(h, bg=COLORS["divider"], height=1).pack(fill="x", pady=(8, 0))


# ============================================================
#  StatCard — Compact statistic block
# ============================================================
class StatCard(tk.Frame):
    """Compact stat card — black block on blue card."""

    def __init__(self, parent, icon, label, color, **kw):
        super().__init__(parent, bg=COLORS["bg_input"], padx=16, pady=12, **kw)
        self.configure(highlightbackground=COLORS["border"], highlightthickness=1)
        tk.Label(self, text=icon, font=("Segoe UI Emoji", 16),
                 bg=COLORS["bg_input"], fg=color).pack(anchor="w")
        self.v = tk.Label(self, text="0", font=("Segoe UI", 22, "bold"),
                          bg=COLORS["bg_input"], fg=COLORS["text_main"])
        self.v.pack(anchor="w", pady=(2, 0))
        tk.Label(self, text=label, font=("Segoe UI", 8),
                 bg=COLORS["bg_input"], fg=COLORS["text_sub"]).pack(anchor="w")

    def set(self, val):
        self.v.config(text=str(val))


# ============================================================
#  TaskRow — Single task display row
# ============================================================
class TaskRow(tk.Frame):
    """Task row — black block on blue card, white text."""

    def __init__(self, parent, task, on_done, on_del):
        super().__init__(parent, bg=COLORS["bg_input"], padx=12, pady=8)
        self.configure(highlightbackground=COLORS["border"], highlightthickness=1)
        done = task["status"] == "completed"
        today = datetime.now().strftime("%Y-%m-%d")
        dl = task.get("deadline", "")
        is_overdue = not done and dl and dl < today
        tt = task.get("task_type", "normal")

        # Status dot
        if done:
            dc = COLORS["green"]
        elif is_overdue:
            dc = COLORS["red"]
        elif tt == "main_focus":
            dc = COLORS["blue"]
        else:
            dc = COLORS["orange"]
        c = tk.Canvas(self, width=8, height=8, bg=COLORS["bg_input"], highlightthickness=0)
        c.create_oval(1, 1, 7, 7, fill=dc, outline="")
        c.pack(side="left", padx=(0, 8))

        # Title
        ts = ("Segoe UI", 11, "overstrike") if done else ("Segoe UI", 11, "bold")
        tf = COLORS["text_sub"] if done else COLORS["text_main"]
        tk.Label(self, text=task["title"], font=ts, bg=COLORS["bg_input"], fg=tf,
                 anchor="w").pack(side="left", fill="x", expand=True)

        # Importance stars
        imp = task.get("importance", 3)
        stars = "".join(["★" if i < imp else "☆" for i in range(5)])
        sc = "#D4A853" if not done else COLORS["text_muted"]
        tk.Label(self, text=stars, font=("Segoe UI", 7),
                 bg=COLORS["bg_input"], fg=sc).pack(side="left", padx=(4, 2))

        # Priority badge
        pr = task.get("priority", 0)
        if pr >= 80:
            pc = COLORS["red"]
        elif pr >= 50:
            pc = COLORS["orange"]
        else:
            pc = COLORS["green"]
        tk.Label(self, text=f" {pr} ", font=("Segoe UI", 8, "bold"),
                 bg=pc, fg="#FFF", padx=5, pady=1).pack(side="left", padx=3)

        # Subject tag
        tk.Label(self, text=f" {task['subject']} ", font=("Segoe UI", 8),
                 bg=COLORS["purple_dark"], fg="#FFF", padx=6, pady=1).pack(side="left", padx=6)

        # Date
        pd = task.get("plan_date", "")
        if pd:
            dl_label = f"⚠️ {pd}" if is_overdue else f"📅 {pd}"
            dl_color = COLORS["red"] if is_overdue else COLORS["text_sub"]
            tk.Label(self, text=dl_label, font=("Segoe UI", 8),
                     bg=COLORS["bg_input"], fg=dl_color).pack(side="left", padx=4)

        # Action buttons
        if not done:
            b = tk.Label(self, text=" ✓ ", font=("Segoe UI", 9, "bold"),
                         bg=COLORS["green"], fg="#FFF", padx=8, pady=3, cursor="hand2")
            b.pack(side="right", padx=1)
            b.bind("<Button-1>", lambda e: on_done(task["id"]))
        b2 = tk.Label(self, text=" ✕ ", font=("Segoe UI", 9),
                      bg=COLORS["red"], fg="#FFF", padx=8, pady=3, cursor="hand2")
        b2.pack(side="right", padx=1)
        b2.bind("<Button-1>", lambda e: on_del(task["id"]))


# ============================================================
#  InsightCard — AI insight display (pending/confirmed/refuted)
# ============================================================
class InsightCard(tk.Frame):
    """Single insight card. Handles 3 states:
    - pending:   shows question + answer input + Answer button
    - confirmed: shows green check + user's answer + confirmed date
    - refuted:   shows red X + user's answer + confirmed date
    """

    def __init__(self, parent, insight, on_answer=None, **kw):
        super().__init__(parent, bg=COLORS["bg_input"], padx=14, pady=10, **kw)
        self.configure(highlightbackground=COLORS["border"], highlightthickness=1)

        status = insight.get("status", "pending")
        confidence = insight.get("confidence", 0.5)
        category = insight.get("category", "general")

        # ── Row 0: Status icon + Title + Category badge ──
        row0 = tk.Frame(self, bg=COLORS["bg_input"])
        row0.pack(fill="x", pady=(0, 6))

        icons = {"pending": "💬", "confirmed": "✅", "refuted": "❌"}
        status_colors = {"pending": COLORS["blue"], "confirmed": COLORS["green"],
                         "refuted": COLORS["red"]}
        tk.Label(row0, text=icons.get(status, "❓"),
                 font=("Segoe UI Emoji", 14),
                 bg=COLORS["bg_input"], fg=status_colors.get(status)
                 ).pack(side="left", padx=(0, 8))

        tk.Label(row0, text=insight.get("title", ""),
                 font=("Segoe UI", 12, "bold"),
                 bg=COLORS["bg_input"], fg=COLORS["text_main"],
                 anchor="w").pack(side="left", fill="x", expand=True)

        # Category badge
        cat_colors = {
            "productivity": COLORS["blue"], "mood": COLORS["purple"],
            "sleep": COLORS["teal"], "habits": COLORS["orange"],
            "general": COLORS["text_muted"],
        }
        tk.Label(row0, text=f" {category} ", font=("Segoe UI", 8, "bold"),
                 bg=cat_colors.get(category, COLORS["text_muted"]), fg="#FFF",
                 padx=6, pady=2).pack(side="right", padx=3)

        # Confidence bar
        if confidence >= 0.7:
            conf_color = COLORS["green"]
            conf_text = "strong"
        elif confidence >= 0.5:
            conf_color = COLORS["orange"]
            conf_text = "moderate"
        else:
            conf_color = COLORS["red"]
            conf_text = "weak"
        tk.Label(row0, text=f" {int(confidence * 100)}% {conf_text} ",
                 font=("Segoe UI", 8), bg=conf_color, fg="#FFF",
                 padx=5, pady=1).pack(side="right", padx=6)

        # ── Hypothesis ──
        tk.Label(self, text=f"🤔 {insight.get('hypothesis', '')}",
                 font=("Segoe UI", 10), bg=COLORS["bg_input"],
                 fg=COLORS["text_sub"], wraplength=760, anchor="w",
                 justify="left").pack(fill="x", pady=(0, 4))

        # ── Evidence ──
        evidence = insight.get("evidence", [])
        if evidence:
            ev_frame = tk.Frame(self, bg=COLORS["bg_input"])
            ev_frame.pack(fill="x", pady=(0, 6))
            tk.Label(ev_frame, text="📊 Evidence:",
                     font=("Segoe UI", 9, "bold"), bg=COLORS["bg_input"],
                     fg=COLORS["text_sub"]).pack(anchor="w")
            for ev in evidence:
                tk.Label(ev_frame, text=f"  • {ev}",
                         font=("Segoe UI", 9), bg=COLORS["bg_input"],
                         fg=COLORS["text_muted"], anchor="w",
                         wraplength=760).pack(anchor="w")

        # ── Question (pending) or Answer (confirmed/refuted) ──
        if status == "pending":
            tk.Label(self, text=f"❓ {insight.get('question', '')}",
                     font=("Segoe UI", 10, "italic"), bg=COLORS["bg_input"],
                     fg=COLORS["purple"], wraplength=760, anchor="w",
                     justify="left").pack(fill="x", pady=(0, 6))
        else:
            answer = insight.get("user_answer", "(no answer)")
            tk.Label(self, text=f'💬 You said: "{answer}"',
                     font=("Segoe UI", 10, "italic"), bg=COLORS["bg_input"],
                     fg=COLORS["text_sub"], wraplength=760, anchor="w",
                     justify="left").pack(fill="x", pady=(0, 6))

        # ── Confirmed date ──
        if status != "pending" and insight.get("confirmed_at"):
            tk.Label(self, text=f"📅 {insight['confirmed_at']}",
                     font=("Segoe UI", 8), bg=COLORS["bg_input"],
                     fg=COLORS["text_muted"]).pack(anchor="w", pady=(0, 4))

        # ── Answer input (only for pending) ──
        if status == "pending" and on_answer:
            ans_frame = tk.Frame(self, bg=COLORS["bg_input"])
            ans_frame.pack(fill="x", pady=(4, 0))
            self.answer_entry = tk.Entry(ans_frame, font=("Segoe UI", 10),
                                         bg=COLORS["bg_input"],
                                         fg=COLORS["text_main"],
                                         insertbackground=COLORS["text_main"],
                                         relief="solid")
            self.answer_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

            ans_btn = tk.Label(ans_frame, text="Answer",
                               font=("Segoe UI", 10, "bold"),
                               bg=COLORS["purple"], fg="#FFF",
                               padx=16, pady=6, cursor="hand2")
            ans_btn.pack(side="right")

            # Bind both button + Enter key
            iid = insight["id"]
            ans_btn.bind("<Button-1>",
                         lambda e, iid=iid, ety=self.answer_entry: on_answer(iid, ety.get()))
            self.answer_entry.bind("<Return>",
                                   lambda e, iid=iid, ety=self.answer_entry: on_answer(iid, ety.get()))


