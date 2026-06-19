"""
Main Application — layout, navigation, theme, timer, and all pages.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime, timedelta
import calendar
import json
import threading

import config
from services import DataManager, AIClient
from widgets import Card, StatCard, TaskRow, InsightCard


# ============================================================
#  Main App
# ============================================================
class App:
    def __init__(self):
        self.db = DataManager()
        self.is_dark = False
        self.api_key = self.db.get_api_key()

        self.win = ttk.Window(themename="flatly")
        self.win.title(config.APP_TITLE)
        self.win.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.win.minsize(config.MIN_WIDTH, config.MIN_HEIGHT)
        self.win.configure(bg=config.COLORS["bg_main"])

        self.current_page = None
        self.ai_loading = False
        self.timers = {}  # {task_id: {"start": timestamp, "label": tk.Label}}

        self._build_layout()
        self._nav_to_page("dashboard")

        if not self.api_key:
            self.win.after(500, self._prompt_api_key)

        # Show discover badge if there are pending questions
        self.win.after(600, self._update_discover_badge)

    # ═══ Layout ═══
    def _build_layout(self):
        self.sidebar = tk.Frame(self.win, bg=config.COLORS["bg_side"], width=config.SIDEBAR_W)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar_content()
        self.main_area = tk.Frame(self.win, bg=config.COLORS["bg_main"])
        self.main_area.pack(side="right", fill="both", expand=True)

    def _build_sidebar_content(self):
        # Logo
        lf = tk.Frame(self.sidebar, bg=config.COLORS["bg_side"])
        lf.pack(fill="x", padx=22, pady=(24, 20))
        tk.Label(lf, text="🌱", font=("Segoe UI Emoji", 30), bg=config.COLORS["bg_side"]).pack(anchor="w")
        tk.Label(lf, text="Growth", font=("Segoe UI", 15, "bold"),
                 bg=config.COLORS["bg_side"], fg=config.COLORS["text_main"]).pack(anchor="w", pady=(4, 0))
        tk.Label(lf, text="Student Planner", font=("Segoe UI", 8),
                 bg=config.COLORS["bg_side"], fg=config.COLORS["text_muted"]).pack(anchor="w")
        tk.Frame(self.sidebar, bg=config.COLORS["divider"], height=1).pack(fill="x", padx=18, pady=(0, 14))

        # Navigation
        self.nav_btns = {}
        for key, text in [
            ("dashboard", "📊  Dashboard"),
            ("timeline", "📋  Timeline"),
            ("tasks", "✅  Tasks"),
            ("ai", "🤖  AI Planner"),
            ("vision", "🌟  Vision"),
            ("discover", "🔍  Discover"),
            ("manual", "📖  Manual"),
        ]:
            b = tk.Label(self.sidebar, text=text, font=("Segoe UI", 12), bg=config.COLORS["bg_side"],
                         fg=config.COLORS["text_sub"], anchor="w", padx=24, pady=11, cursor="hand2")
            b.pack(fill="x")
            b.bind("<Button-1>", lambda e, k=key: self._nav_to_page(k))
            b.bind("<Enter>", lambda e, b=b, k=key:
                   b.configure(bg=config.COLORS["bg_hover"] if self.current_page != k else config.COLORS["purple_dark"],
                               fg=config.COLORS["text_main"] if self.current_page != k else "#FFF"))
            b.bind("<Leave>", lambda e, b=b, k=key:
                   b.configure(bg=config.COLORS["purple_dark"] if self.current_page == k else config.COLORS["bg_side"],
                               fg="#FFF" if self.current_page == k else config.COLORS["text_sub"]))
            self.nav_btns[key] = b

        # Theme toggle
        sp = tk.Frame(self.sidebar, bg=config.COLORS["bg_side"])
        sp.pack(fill="both", expand=True)
        tk.Frame(self.sidebar, bg=config.COLORS["border"], height=1).pack(fill="x", padx=16, pady=(0, 12))
        self.theme_btn = tk.Frame(self.sidebar, bg=config.COLORS["bg_side"], padx=16, pady=10, cursor="hand2")
        self.theme_btn.pack(fill="x", pady=(0, 16))
        self.theme_icon = tk.Label(self.theme_btn, text="🌙", font=("Segoe UI Emoji", 14),
                                   bg=config.COLORS["bg_side"], fg=config.COLORS["text_sub"])
        self.theme_icon.pack(side="left", padx=(0, 12))
        self.theme_text = tk.Label(self.theme_btn, text="Dark Mode", font=("Segoe UI", 11),
                                   bg=config.COLORS["bg_side"], fg=config.COLORS["text_sub"], anchor="w")
        self.theme_text.pack(side="left")
        for w in [self.theme_btn, self.theme_icon, self.theme_text]:
            w.bind("<Button-1>", lambda e: self._toggle_theme())

        # API Key
        self.api_btn = tk.Label(self.sidebar, text="⚙️  API Settings", font=("Segoe UI", 10),
                                bg=config.COLORS["bg_side"], fg=config.COLORS["text_muted"],
                                anchor="w", padx=24, pady=6, cursor="hand2")
        self.api_btn.pack(fill="x", pady=(0, 8))
        self.api_btn.bind("<Button-1>", lambda e: self._prompt_api_key())

    # ═══ Nav & Theme ═══
    def _nav_to_page(self, key):
        self.current_page = key
        for k, b in self.nav_btns.items():
            a = (k == key)
            b.configure(bg=config.COLORS["purple_dark"] if a else config.COLORS["bg_side"],
                        fg="#FFF" if a else config.COLORS["text_sub"])
        self._clear_main()
        {
            "dashboard": self._show_dashboard,
            "timeline": self._show_timeline,
            "tasks": self._show_tasks,
            "ai": self._show_ai,
            "vision": self._show_vision,
            "discover": self._show_discover,
            "manual": self._show_manual,
        }[key]()

    def _clear_main(self):
        for w in self.main_area.winfo_children():
            w.destroy()

    def _update_discover_badge(self):
        """Show pending question count badge on Discover nav item."""
        btn = self.nav_btns.get("discover")
        if not btn:
            return
        count = self.db.get_pending_insight_count()
        current_text = btn.cget("text")
        # Remove existing badge suffix
        base = current_text.split("  ·")[0]
        if count > 0:
            btn.config(text=f"{base}  ·{count}")
        else:
            btn.config(text=base)

    def _toggle_theme(self):
        self.is_dark = not self.is_dark
        try:
            self.win.style.theme_use("darkly" if self.is_dark else "flatly")
        except Exception:
            pass
        config.COLORS.update(config.DARK_COLORS if self.is_dark else config.LIGHT_COLORS)
        self.win.configure(bg=config.COLORS["bg_main"])
        self.main_area.configure(bg=config.COLORS["bg_main"])
        for w in self.sidebar.winfo_children():
            w.destroy()
        self.nav_btns = {}
        self._build_sidebar_content()
        self.theme_icon.config(text="☀️" if self.is_dark else "🌙")
        self.theme_text.config(text="Light Mode" if self.is_dark else "Dark Mode")
        self._nav_to_page(self.current_page)

    def _prompt_api_key(self):
        key = simpledialog.askstring(
            "DeepSeek API Key",
            "Enter your DeepSeek API Key:\n\n"
            "1. Sign up at platform.deepseek.com\n"
            "2. Create a key in API Keys page\n"
            "3. New users get free credits\n\n"
            "(Stored locally, never uploaded)",
            parent=self.win,
        )
        if key:
            self.api_key = key.strip()
            self.db.set_api_key(self.api_key)
            messagebox.showinfo("Success", "API Key saved!\nYou can now use the AI Planner.")

    # ═══ Scroll ═══
    def _scroll(self, parent):
        cv = tk.Canvas(parent, bg=config.COLORS["bg_main"], highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg=config.COLORS["bg_main"])
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=inner, anchor="nw", tags="in")
        cv.configure(yscrollcommand=sb.set)
        cv.bind("<Configure>", lambda e: cv.itemconfig("in", width=e.width))

        def _wh(e):
            cv.yview_scroll(int(-1 * (e.delta / 120)), "units")

        inner.bind("<Enter>", lambda e: cv.bind_all("<MouseWheel>", _wh))
        inner.bind("<Leave>", lambda e: cv.unbind_all("<MouseWheel>"))
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return cv, sb, inner

    # ═══ Timer ═══
    def _start_timer(self, tid, label, act_label=None):
        """Start a count-up timer, updating label every second."""
        import time as _time
        now = _time.time()
        self.timers[tid] = {"start": now, "label": label, "act_label": act_label, "running": True}
        self._tick_timer(tid)

    def _tick_timer(self, tid):
        """Update timer display every second."""
        import time as _time
        t = self.timers.get(tid)
        if not t or not t.get("running"):
            return
        elapsed = int(_time.time() - t["start"])
        mins, secs = divmod(elapsed, 60)
        t["label"].config(text=f"⏱ {mins:02d}:{secs:02d}")
        self._timer_after = self.win.after(1000, lambda: self._tick_timer(tid))

    def _stop_timer(self, tid):
        """Stop timer, save elapsed minutes, update actual label."""
        import time as _time
        t = self.timers.pop(tid, None)
        if not t:
            return
        t["running"] = False
        elapsed = int(_time.time() - t["start"])
        mins = max(1, round(elapsed / 60, 1))
        self.db.add_time(tid, mins)
        t["label"].config(text="▶")
        if t.get("act_label"):
            total = 0
            for tk_item in self.db.data["tasks"]:
                if tk_item["id"] == tid:
                    total = tk_item.get("actual_minutes", 0)
                    break
            t["act_label"].config(text=f"✓ {total:.0f}m", fg=config.COLORS["green"])

    # ═══ 1. Dashboard ═══
    def _show_dashboard(self):
        self._clear_main()
        stats = self.db.get_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        _, __, inner = self._scroll(self.main_area)

        h = datetime.now().hour
        g = "Good morning ☀️" if h < 12 else ("Good afternoon 🌤️" if h < 18 else "Good evening 🌙")
        tk.Label(inner, text=g, font=("Segoe UI", 24, "bold"),
                 bg=config.COLORS["bg_main"], fg=config.COLORS["text_main"]).pack(fill="x", padx=30, pady=(22, 2))
        tk.Label(inner, text=f"{today}  {config.WEEKDAYS_CN[datetime.now().weekday()]}",
                 font=("Segoe UI", 11), bg=config.COLORS["bg_main"],
                 fg=config.COLORS["text_sub"]).pack(fill="x", padx=30, pady=(0, 20))

        # Weekly theme
        weekly_theme = self.db.get_weekly_theme()
        if weekly_theme:
            wtf = tk.Frame(inner, bg=config.COLORS["bg_accent"])
            wtf.pack(fill="x", padx=30, pady=(0, 12))
            tk.Label(wtf, text=f"🎯  This week: {weekly_theme}", font=("Segoe UI", 12, "bold"),
                     bg=config.COLORS["bg_accent"], fg=config.COLORS["purple"]).pack(padx=16, pady=10, anchor="w")

        # Stat cards
        cards = tk.Frame(inner, bg=config.COLORS["bg_main"])
        cards.pack(fill="x", padx=30, pady=4)
        for i in range(5):
            cards.columnconfigure(i, weight=1, uniform="c")
        overd = sum(1 for t in self.db.get_tasks()
                    if t["status"] == "pending" and t.get("deadline", "") and t["deadline"] < today)
        for i, (ic, lb, val, cl) in enumerate([
            ("📋", "Total", stats["total"], config.COLORS["purple"]),
            ("⏳", "Pending", stats["pending"], config.COLORS["orange"]),
            ("✅", "Completed", stats["completed"], config.COLORS["green"]),
            ("📅", "Today", f"{stats['today_done']}/{stats['today_total']}", config.COLORS["blue"]),
            ("🚨", "Overdue", overd, config.COLORS["red"]),
        ]):
            c = StatCard(cards, ic, lb, cl)
            c.grid(row=0, column=i, sticky="nsew", padx=4)
            c.set(val)

        # Today's tasks — Focus + Quick with Pomodoro timer
        td_tasks = self.db.get_tasks(today)
        main_tasks = [t for t in td_tasks if t.get("task_type") == "main_focus"]
        quick_tasks = [t for t in td_tasks if t.get("task_type") == "quick_task"]
        other_tasks = [t for t in td_tasks if t.get("task_type") not in ("main_focus", "quick_task")]

        if td_tasks:
            if main_tasks or other_tasks:
                c1 = Card(inner, title="Focus", icon="🔵")
                c1.pack(fill="x", padx=30, pady=(18, 6))
                for t in main_tasks + other_tasks:
                    tid = t["id"]
                    dn = t["status"] == "completed"
                    dl2 = t.get("deadline", "")
                    is_od = not dn and dl2 and dl2 < today
                    row_bg = config.COLORS["bg_input"]
                    r = tk.Frame(c1, bg=row_bg, padx=8, pady=6,
                                 highlightbackground=config.COLORS["border"], highlightthickness=1)
                    r.pack(fill="x", pady=2)
                    if dn:
                        dc2 = config.COLORS["green"]
                    elif is_od:
                        dc2 = config.COLORS["red"]
                    else:
                        dc2 = config.COLORS["blue"]
                    cc = tk.Canvas(r, width=7, height=7, bg=row_bg, highlightthickness=0)
                    cc.create_oval(1, 1, 6, 6, fill=dc2, outline="")
                    cc.pack(side="left", padx=(0, 8))
                    ts = ("Segoe UI", 10, "overstrike") if dn else ("Segoe UI", 10, "bold")
                    tf = config.COLORS["text_sub"] if dn else config.COLORS["text_main"]
                    tk.Label(r, text=t["title"], font=ts, bg=row_bg, fg=tf, anchor="w").pack(
                        side="left", fill="x", expand=True)
                    # Target
                    hh = t.get("estimated_hours", 0)
                    if hh:
                        tk.Label(r, text=f"🎯 {hh}h", font=("Segoe UI", 8),
                                 bg=row_bg, fg=config.COLORS["text_sub"]).pack(side="right", padx=4)
                    # Actual
                    am = t.get("actual_minutes", 0)
                    act_label = tk.Label(r, text=f"✓ {am:.0f}m" if am else "—",
                                         font=("Segoe UI", 8), bg=row_bg,
                                         fg=config.COLORS["green"] if am else config.COLORS["text_muted"])
                    act_label.pack(side="right", padx=4)
                    # Complete button — mark done directly
                    done_btn = tk.Label(r, text=" ✓ ", font=("Segoe UI", 9, "bold"),
                                        bg=config.COLORS["green"], fg="#FFF",
                                        padx=6, pady=2, cursor="hand2")
                    done_btn.pack(side="right", padx=2)
                    if not dn:
                        done_btn.bind("<Button-1>",
                                      lambda e, tid=tid: (
                                          self.db.update_task(tid, status="completed"),
                                          self._show_dashboard()))
                    else:
                        done_btn.config(text="↩", bg=config.COLORS["orange"],
                                        font=("Segoe UI", 9, "bold"))
                        done_btn.bind("<Button-1>",
                                      lambda e, tid=tid: (
                                          self.db.update_task(tid, status="pending"),
                                          self._show_dashboard()))
                    # Timer controls
                    timer_label = tk.Label(r, text="▶", font=("Segoe UI", 10),
                                           bg=row_bg, fg=config.COLORS["blue"], cursor="hand2", padx=4)
                    timer_label.pack(side="right")
                    # Bind timer
                    if not dn:
                        def _start_stop(tid=tid, tl=timer_label, al=act_label):
                            if tid in self.timers and self.timers[tid].get("running"):
                                self._stop_timer(tid)
                            else:
                                self._start_timer(tid, tl, al)

                        timer_label.bind("<Button-1>", lambda e, cb=_start_stop: cb())
                    else:
                        timer_label.config(text="✓", fg=config.COLORS["green"])
            if quick_tasks:
                c2 = Card(inner, title="Quick Tasks", icon="🟢")
                c2.pack(fill="x", padx=30, pady=(8, 6))
                for t in quick_tasks:
                    tid = t["id"]
                    dn = t["status"] == "completed"
                    row_bg = config.COLORS["bg_input"]
                    r = tk.Frame(c2, bg=row_bg, padx=8, pady=5,
                                 highlightbackground=config.COLORS["border"], highlightthickness=1)
                    r.pack(fill="x", pady=2)
                    dc3 = config.COLORS["green"] if dn else config.COLORS["teal"]
                    cc = tk.Canvas(r, width=7, height=7, bg=row_bg, highlightthickness=0)
                    cc.create_oval(1, 1, 6, 6, fill=dc3, outline="")
                    cc.pack(side="left", padx=(0, 8))
                    ts = ("Segoe UI", 10, "overstrike") if dn else ("Segoe UI", 10)
                    tf = config.COLORS["text_sub"] if dn else config.COLORS["text_main"]
                    tk.Label(r, text=t["title"], font=ts, bg=row_bg, fg=tf, anchor="w").pack(
                        side="left", fill="x", expand=True)
                    hh = t.get("estimated_hours", 0)
                    if hh:
                        tk.Label(r, text=f"🎯 {hh}h", font=("Segoe UI", 8),
                                 bg=row_bg, fg=config.COLORS["text_sub"]).pack(side="right", padx=4)
                    am = t.get("actual_minutes", 0)
                    act_label2 = tk.Label(r, text=f"✓ {am:.0f}m" if am else "—",
                                          font=("Segoe UI", 8), bg=row_bg,
                                          fg=config.COLORS["green"] if am else config.COLORS["text_muted"])
                    act_label2.pack(side="right", padx=4)
                    # Complete button — mark done directly
                    done_btn2 = tk.Label(r, text=" ✓ ", font=("Segoe UI", 9, "bold"),
                                         bg=config.COLORS["green"], fg="#FFF",
                                         padx=6, pady=2, cursor="hand2")
                    done_btn2.pack(side="right", padx=2)
                    if not dn:
                        done_btn2.bind("<Button-1>",
                                       lambda e, tid=tid: (
                                           self.db.update_task(tid, status="completed"),
                                           self._show_dashboard()))
                    else:
                        done_btn2.config(text="↩", bg=config.COLORS["orange"],
                                         font=("Segoe UI", 9, "bold"))
                        done_btn2.bind("<Button-1>",
                                       lambda e, tid=tid: (
                                           self.db.update_task(tid, status="pending"),
                                           self._show_dashboard()))
                    timer_label2 = tk.Label(r, text="▶" if not dn else "✓",
                                            font=("Segoe UI", 10), bg=row_bg,
                                            fg=config.COLORS["blue"] if not dn else config.COLORS["green"],
                                            cursor="hand2", padx=4)
                    timer_label2.pack(side="right")
                    if not dn:
                        def _qs(tid=tid, tl=timer_label2, al=act_label2):
                            if tid in self.timers and self.timers[tid].get("running"):
                                self._stop_timer(tid)
                            else:
                                self._start_timer(tid, tl, al)

                        timer_label2.bind("<Button-1>", lambda e, cb=_qs: cb())
        else:
            c1 = Card(inner, title="Today", icon="📅")
            c1.pack(fill="x", padx=30, pady=(18, 10))
            tk.Label(c1, text="No tasks yet — go to AI Planner to create a plan ✨",
                     font=("Segoe UI", 11), bg=config.COLORS["bg_card"],
                     fg=config.COLORS["text_sub"]).pack(pady=10)

        # Vision snapshot
        visions = self.db.get_visions()
        if visions:
            c2 = Card(inner, title="Latest Vision", icon="🌟")
            c2.pack(fill="x", padx=30, pady=(12, 20))
            v = visions[0]
            a = v.get("analysis", {})
            themes = a.get("core_themes", "") if isinstance(a, dict) else ""
            if themes:
                tk.Label(c2, text=" · ".join(themes), font=("Segoe UI", 11),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["purple"],
                         wraplength=1200).pack(anchor="w")
            tk.Label(c2, text=v.get("date", ""), font=("Segoe UI", 9),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_muted"]).pack(anchor="w", pady=(6, 0))

    # ═══ Timeline ═══
    def _show_timeline(self):
        self._clear_main()
        _, __, inner = self._scroll(self.main_area)
        today = datetime.now()

        # Title bar with week navigation
        top = tk.Frame(inner, bg=config.COLORS["bg_main"])
        top.pack(fill="x", padx=28, pady=(18, 4))
        tk.Label(top, text="📋  Timeline", font=("Segoe UI", 20, "bold"),
                 bg=config.COLORS["bg_main"], fg=config.COLORS["text_main"]).pack(side="left")
        nav = tk.Frame(top, bg=config.COLORS["bg_main"])
        nav.pack(side="right")

        # Initialize week offset
        if not hasattr(self, "tl_week_offset"):
            self.tl_week_offset = 0

        monday = today - timedelta(days=today.weekday()) + timedelta(weeks=self.tl_week_offset)
        sunday = monday + timedelta(days=6)
        self.tl_title = tk.Label(nav, text=f"{monday.strftime('%m/%d')} — {sunday.strftime('%m/%d, %Y')}",
                                 font=("Segoe UI", 16, "bold"),
                                 bg=config.COLORS["bg_main"], fg=config.COLORS["purple"])
        self.tl_title.pack(side="left", padx=16)

        for text, dw in [("◀", -1), ("▶", 1)]:
            b = tk.Label(nav, text=text, font=("Segoe UI", 14),
                         bg=config.COLORS["bg_main"], fg=config.COLORS["text_sub"],
                         cursor="hand2", padx=6)
            b.pack(side="left")
            b.bind("<Button-1>", lambda e, dw=dw: (
                setattr(self, "tl_week_offset", self.tl_week_offset + dw),
                self._show_timeline()))

        # Today button
        today_btn = tk.Label(nav, text="Today", font=("Segoe UI", 11, "bold"),
                             bg=config.COLORS["purple"], fg="#FFF", padx=12, pady=4, cursor="hand2")
        today_btn.pack(side="left", padx=8)
        today_btn.bind("<Button-1>", lambda e: (
            setattr(self, "tl_week_offset", 0), self._show_timeline()))

        # Fetch data
        diary_map = self.db.get_diary_map()

        # Table header
        card = Card(inner, title="📊  Week Overview", icon="")
        card.pack(fill="x", padx=28, pady=(12, 0))

        # Column headers
        hdr = tk.Frame(card, bg=config.COLORS["bg_card"])
        hdr.pack(fill="x", pady=(0, 8))
        cols = [("Date", 10), ("Mood", 8), ("Sleep", 8), ("Deadline Tasks", 22), ("Highlights", 22)]
        for i, (label, w) in enumerate(cols):
            hdr.columnconfigure(i, weight=w, uniform="tl")
            tk.Label(hdr, text=label, font=("Segoe UI", 11, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"],
                     anchor="w").grid(row=0, column=i, sticky="w", padx=6)
        tk.Frame(card, bg=config.COLORS["divider"], height=1).pack(fill="x", pady=(0, 6))

        # Week days
        for i in range(7):
            d = monday + timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            is_today = ds == today.strftime("%Y-%m-%d")

            row_bg = config.COLORS["bg_input"] if is_today else config.COLORS["bg_card"]
            border_c = config.COLORS["purple_dark"] if is_today else config.COLORS["border"]
            row = tk.Frame(card, bg=row_bg, padx=10, pady=8,
                           highlightbackground=border_c, highlightthickness=1 if is_today else 1)
            row.pack(fill="x", pady=2)
            for ci in range(5):
                row.columnconfigure(ci, weight=cols[ci][1], uniform="tl")

            # Col 0: Date + weekday
            wd_cn = config.WEEKDAYS_CN[d.weekday()]
            wd = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]
            tk.Label(row, text=f"{d.day}  {wd}", font=("Segoe UI", 13, "bold"),
                     bg=row_bg, fg=config.COLORS["purple"] if is_today else config.COLORS["text_main"],
                     anchor="w").grid(row=0, column=0, sticky="w", padx=6)

            # Col 1: Mood from diary
            mood_text = "—"
            mood_color = config.COLORS["text_muted"]
            diary_entry = diary_map.get(ds)
            if diary_entry:
                analysis = diary_entry.get("analysis", {})
                if isinstance(analysis, dict):
                    mood = analysis.get("mood", {})
                    if isinstance(mood, dict) and mood.get("primary"):
                        score = mood.get("score", 5)
                        emoji = {"happy": "😊", "tired": "😫", "anxious": "😰", "sad": "😢",
                                 "calm": "😌", "excited": "🤩", "bored": "😐"}.get(mood["primary"], "😶")
                        mood_text = f"{emoji} {score}/10"
                        mood_color = config.COLORS["green"] if score >= 6 else config.COLORS["orange"]
            tk.Label(row, text=mood_text, font=("Segoe UI", 12),
                     bg=row_bg, fg=mood_color, anchor="w").grid(row=0, column=1, sticky="w", padx=6)

            # Col 2: Sleep from diary
            sleep_text = "—"
            sleep_color = config.COLORS["text_muted"]
            if diary_entry:
                analysis = diary_entry.get("analysis", {})
                if isinstance(analysis, dict):
                    sleep = analysis.get("sleep", {})
                    if isinstance(sleep, dict) and sleep.get("hours"):
                        sq = sleep.get("quality", "ok")
                        si = {"good": "😴💤", "ok": "😴", "bad": "😫⚠️"}.get(sq, "😴")
                        sleep_text = f"{si} {sleep['hours']}h"
                        sleep_color = config.COLORS["green"] if sq == "good" else (
                            config.COLORS["orange"] if sq == "ok" else config.COLORS["red"])
            tk.Label(row, text=sleep_text, font=("Segoe UI", 12),
                     bg=row_bg, fg=sleep_color, anchor="w").grid(row=0, column=2, sticky="w", padx=6)

            # Col 3: Deadline tasks
            deadline_tasks = self.db.get_deadline_tasks(ds)
            if deadline_tasks:
                task_frame = tk.Frame(row, bg=row_bg)
                task_frame.grid(row=0, column=3, sticky="w", padx=4)
                for t in deadline_tasks[:3]:
                    dn = t["status"] == "completed"
                    ts = ("Segoe UI", 11, "overstrike") if dn else ("Segoe UI", 11)
                    tc = config.COLORS["text_muted"] if dn else config.COLORS["text_main"]
                    dot = "✓ " if dn else "● "
                    title = t["title"][:20] + "…" if len(t["title"]) > 20 else t["title"]
                    tk.Label(task_frame, text=f"{dot}{title}", font=ts, bg=row_bg, fg=tc,
                             anchor="w").pack(anchor="w")
                if len(deadline_tasks) > 3:
                    tk.Label(task_frame, text=f"  +{len(deadline_tasks)-3} more",
                             font=("Segoe UI", 10, "italic"), bg=row_bg,
                             fg=config.COLORS["text_muted"], anchor="w").pack(anchor="w")
            else:
                tk.Label(row, text="—", font=("Segoe UI", 12),
                         bg=row_bg, fg=config.COLORS["text_muted"],
                         anchor="w").grid(row=0, column=3, sticky="w", padx=4)

            # Col 4: Diary highlights
            hl_text = "—"
            hl_color = config.COLORS["text_muted"]
            if diary_entry:
                analysis = diary_entry.get("analysis", {})
                if isinstance(analysis, dict):
                    highlights = analysis.get("highlights", [])
                    if highlights:
                        hl_text = " · ".join(highlights[:2])
                        if len(highlights) > 2:
                            hl_text += f"  +{len(highlights)-2}"
                        hl_color = config.COLORS["text_sub"]
            tk.Label(row, text=hl_text, font=("Segoe UI", 11),
                     bg=row_bg, fg=hl_color, anchor="w", wraplength=350,
                     justify="left").grid(row=0, column=4, sticky="w", padx=4)

        # Summary card
        summary = Card(inner, title="📈  Week Summary", icon="")
        summary.pack(fill="x", padx=28, pady=(12, 20))

        week_diary = [diary_map.get((monday + timedelta(days=i)).strftime("%Y-%m-%d"))
                      for i in range(7)]
        week_diary = [d for d in week_diary if d]
        week_tasks = sum(1 for i in range(7)
                         for t in self.db.get_deadline_tasks(
                             (monday + timedelta(days=i)).strftime("%Y-%m-%d")))

        summary_text = (
            f"📝  {len(week_diary)} diary entries this week  ·  "
            f"📌  {week_tasks} deadline tasks"
        )
        if week_diary:
            moods = [d.get("analysis", {}).get("mood", {}).get("score", 5)
                     for d in week_diary
                     if isinstance(d.get("analysis", {}), dict)
                     and isinstance(d.get("analysis", {}).get("mood", {}), dict)]
            if moods:
                avg_mood = sum(moods) / len(moods)
                emoji = "😊" if avg_mood >= 7 else ("😐" if avg_mood >= 5 else "😔")
                summary_text += f"  ·  Avg mood: {emoji} {avg_mood:.1f}/10"

        tk.Label(summary, text=summary_text, font=("Segoe UI", 12),
                 bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                 wraplength=1200).pack(anchor="w")

    # ═══ 2. Calendar ═══
    def _show_calendar(self):
        self._clear_main()
        today = datetime.now()
        self.cal_y = today.year
        self.cal_m = today.month

        top = tk.Frame(self.main_area, bg=config.COLORS["bg_main"])
        top.pack(fill="x", padx=24, pady=(16, 8))
        tk.Label(top, text="📅  Calendar", font=("Segoe UI", 20, "bold"),
                 bg=config.COLORS["bg_main"], fg=config.COLORS["text_main"]).pack(side="left")
        nav = tk.Frame(top, bg=config.COLORS["bg_main"])
        nav.pack(side="right")
        self.cal_title = tk.Label(nav, text="", font=("Segoe UI", 14, "bold"),
                                  bg=config.COLORS["bg_main"], fg=config.COLORS["purple"])
        self.cal_title.pack(side="left", padx=16)
        for text, dy, dm in [("◀", -1, 0), ("▶", 1, 0), ("▲", 0, -1), ("▼", 0, 1)]:
            b = tk.Label(nav, text=text, font=("Segoe UI", 12), bg=config.COLORS["bg_main"],
                         fg=config.COLORS["text_sub"], cursor="hand2", padx=4)
            b.pack(side="left")
            b.bind("<Button-1>", lambda e, dy=dy, dm=dm: self._cal_shift(dy, dm))
        body = tk.Frame(self.main_area, bg=config.COLORS["bg_main"])
        body.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        week_f = Card(self.main_area, title="Week Overview", icon="📋")
        week_f.pack(fill="x", padx=24, pady=(0, 16))
        self._draw_cal(body, week_f)

    def _cal_shift(self, dy, dm):
        if dm:
            self.cal_m += dm
            if self.cal_m > 12:
                self.cal_m = 1
                self.cal_y += 1
            if self.cal_m < 1:
                self.cal_m = 12
                self.cal_y -= 1
        else:
            d = datetime(self.cal_y, self.cal_m, 1) + timedelta(days=dy * 30)
            self.cal_y, self.cal_m = d.year, d.month
        body = self.main_area.winfo_children()
        week_f = None
        for w in self.main_area.winfo_children():
            if isinstance(w, Card) and "Week" in str(w):
                week_f = w
                break
        # Rebuild
        for w in self.main_area.winfo_children():
            if isinstance(w, tk.Frame) and w != self.sidebar:
                for ch in w.winfo_children():
                    if isinstance(ch, tk.Frame) and ch.cget("bg") == config.COLORS["bg_main"]:
                        self._draw_cal(ch, week_f or w)
                        return
        self._draw_cal(body, week_f or body)

    def _draw_cal(self, parent, week_f):
        for w in parent.winfo_children():
            w.destroy()
        self.cal_title.config(text=f"{self.cal_y}  {self.cal_m}")
        mt = self.db.get_month_deadline_groups(self.cal_y, self.cal_m)
        today = datetime.now()

        # Weekday headers
        WDS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        hdr = tk.Frame(parent, bg=config.COLORS["bg_main"])
        hdr.pack(fill="x", pady=(12, 4))
        for i, wd in enumerate(WDS):
            hdr.columnconfigure(i, weight=1, uniform="cal")
            tk.Label(hdr, text=wd, font=("Segoe UI", 10, "bold"), bg=config.COLORS["bg_main"],
                     fg=config.COLORS["red"] if i == 0 else config.COLORS["text_sub"]
                     ).grid(row=0, column=i, sticky="ew", ipady=4)

        # Calendar grid — each cell is a lifted card on black base
        weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(self.cal_y, self.cal_m)
        for wk in weeks:
            row = tk.Frame(parent, bg=config.COLORS["bg_main"])
            row.pack(fill="x", pady=3, padx=2)
            for i in range(7):
                row.columnconfigure(i, weight=1, uniform="cal")
            for di, day in enumerate(wk):
                if day == 0:
                    # Empty cell — bare base layer
                    tk.Frame(row, bg=config.COLORS["bg_main"], padx=6, pady=8).grid(
                        row=0, column=di, sticky="nsew")
                    continue
                ist = (day == today.day and self.cal_m == today.month and self.cal_y == today.year)
                day_tasks = mt.get(day, [])
                # Cell background: today → purple, others → card
                if ist:
                    cb = config.COLORS["purple_dark"]
                    border_c = "#4060A0"
                else:
                    cb = config.COLORS["bg_card"]
                    border_c = config.COLORS["border"]
                cell = tk.Frame(row, bg=cb, padx=6, pady=6,
                                highlightbackground=border_c, highlightthickness=2)
                cell.grid(row=0, column=di, sticky="nsew", ipady=8, padx=2, pady=2)
                # Day number — white on today, normal on other cells
                day_fg = "#FFF" if ist else config.COLORS["text_main"]
                tk.Label(cell, text=str(day), font=("Segoe UI", 14, "bold"), bg=cb,
                         fg=day_fg).pack(anchor="ne")
                if day_tasks:
                    dl_f = tk.Frame(cell, bg=cb)
                    dl_f.pack(anchor="sw", pady=(4, 0), fill="x")
                    # Show up to 3 tasks as purple badge labels
                    max_show = 3
                    for idx, t in enumerate(day_tasks[:max_show]):
                        done = t["status"] == "completed"
                        title = t["title"]
                        if len(title) > 14:
                            title = title[:12] + "…"
                        # Purple badge — entire label background
                        badge_bg = "#5A3FB0" if not ist else config.COLORS["bg_accent"]
                        badge_fg = "#FFF" if not ist else "#FFF"
                        dot = "✓ " if done else "● "
                        lbl = tk.Label(dl_f, text=f"{dot}{title}",
                                       font=("Segoe UI", 8, "overstrike" if done else "bold"),
                                       bg=badge_bg, fg=badge_fg,
                                       padx=4, pady=1, anchor="w")
                        lbl.pack(anchor="w", pady=1)
                    remaining = len(day_tasks) - max_show
                    if remaining > 0:
                        tk.Label(dl_f, text=f"  +{remaining} more",
                                 font=("Segoe UI", 7, "italic"), bg=cb,
                                 fg=config.COLORS["text_muted"], anchor="w").pack(anchor="w")
                cell.bind("<Button-1>", lambda e, d=day: self._day_detail(d))
                for ch in cell.winfo_children():
                    ch.bind("<Button-1>", lambda e, d=day: self._day_detail(d))

        # Week overview
        for w in list(week_f.winfo_children()):
            w.destroy()
        wf_content = tk.Frame(week_f, bg=config.COLORS["bg_card"])
        wf_content.pack(fill="x", padx=0, pady=(8, 6))
        monday = today - timedelta(days=today.weekday())
        for i in range(7):
            wf_content.columnconfigure(i, weight=1, uniform="wk")
        for i in range(7):
            d = monday + timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            dt = self.db.get_tasks(ds)
            ist = d.date() == today.date()
            cb_wf = config.COLORS["bg_input"] if ist else config.COLORS["bg_card"]
            cell = tk.Frame(wf_content, bg=cb_wf, padx=8, pady=8,
                            highlightbackground=config.COLORS["border"], highlightthickness=1)
            cell.grid(row=0, column=i, sticky="nsew", padx=2)
            dc_w = config.COLORS["purple"] if ist else config.COLORS["text_main"]
            tk.Label(cell, text=f"{WDS[i]}\n{d.day}", font=("Segoe UI", 10, "bold"),
                     bg=cb_wf, fg=dc_w).pack(pady=(0, 6))
            if dt:
                dn = sum(1 for t in dt if t["status"] == "completed")
                tk.Label(cell, text=f"✅ {dn}/{len(dt)}", font=("Segoe UI", 9), bg=cb_wf,
                         fg=config.COLORS["green"] if dn == len(dt) else config.COLORS["orange"]).pack()
            else:
                tk.Label(cell, text="—", font=("Segoe UI", 9), bg=cb_wf,
                         fg=config.COLORS["text_muted"]).pack()

    def _day_detail(self, day):
        ds = f"{self.cal_y}-{self.cal_m:02d}-{day:02d}"
        tasks = self.db.get_deadline_tasks(ds)  # show deadline tasks, not daily tasks
        w = tk.Toplevel(self.win)
        w.title(f"📅 {ds}")
        w.geometry("620x520")
        w.configure(bg=config.COLORS["bg_card"])
        w.transient(self.win)
        try:
            wd = config.WEEKDAYS_CN[datetime.strptime(ds, "%Y-%m-%d").weekday()]
        except Exception:
            wd = ""
        tk.Label(w, text=f"📅  {ds}  {wd}", font=("Segoe UI", 14, "bold"),
                 bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"]).pack(padx=20, pady=(20, 14))
        if tasks:
            for t in tasks:
                r = tk.Frame(w, bg=config.COLORS["bg_card"])
                r.pack(fill="x", padx=20, pady=3)
                dn = t["status"] == "completed"
                dc2 = config.COLORS["green"] if dn else config.COLORS["orange"]
                cc = tk.Canvas(r, width=8, height=8, bg=config.COLORS["bg_card"], highlightthickness=0)
                cc.create_oval(1, 1, 7, 7, fill=dc2, outline="")
                cc.pack(side="left", padx=(0, 8))
                ts = ("Segoe UI", 11, "overstrike") if dn else ("Segoe UI", 11)
                tf = config.COLORS["text_sub"] if dn else config.COLORS["text_main"]
                tk.Label(r, text=t["title"], font=ts, bg=config.COLORS["bg_card"], fg=tf,
                         anchor="w").pack(side="left", fill="x", expand=True)

                def _tg(tid=t["id"]):
                    ns = "pending" if t["status"] == "completed" else "completed"
                    self.db.update_task(tid, status=ns)
                    w.destroy()
                    self._day_detail(day)

                bt = "↩ Undo" if dn else "✓ Done"
                bc = config.COLORS["orange"] if dn else config.COLORS["green"]
                b = tk.Label(r, text=bt, font=("Segoe UI", 9), bg=bc, fg="#FFF", padx=10, pady=3, cursor="hand2")
                b.pack(side="right")
                b.bind("<Button-1>", lambda e, cb=_tg: cb())
        else:
            tk.Label(w, text="📭  No tasks on this day", font=("Segoe UI", 12),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"]).pack(expand=True)

    # ═══ 3. Tasks ═══
    def _show_tasks(self):
        self._clear_main()
        _, __, inner = self._scroll(self.main_area)
        tk.Label(inner, text="✅  Tasks", font=("Segoe UI", 20, "bold"),
                 bg=config.COLORS["bg_main"], fg=config.COLORS["text_main"]).pack(fill="x", padx=28, pady=(18, 14))

        form = Card(inner, title="New Task", icon="➕")
        form.pack(fill="x", padx=28, pady=(0, 14))
        ff = tk.Frame(form, bg=config.COLORS["bg_card"])
        ff.pack(fill="x")
        for i in range(4):
            ff.columnconfigure(i, weight=[2, 1, 1, 0][i], uniform="f")
        tk.Label(ff, text="Task", font=("Segoe UI", 9), bg=config.COLORS["bg_card"],
                 fg=config.COLORS["text_sub"]).grid(row=0, column=0, sticky="w")
        e_title = tk.Entry(ff, font=("Segoe UI", 11), bg=config.COLORS["bg_input"],
                           fg=config.COLORS["text_main"], insertbackground=config.COLORS["text_main"], relief="flat")
        e_title.grid(row=1, column=0, sticky="ew", padx=(0, 6), ipady=2)
        tk.Label(ff, text="Subject", font=("Segoe UI", 9), bg=config.COLORS["bg_card"],
                 fg=config.COLORS["text_sub"]).grid(row=0, column=1, sticky="w")
        e_subj = tk.Entry(ff, font=("Segoe UI", 11), bg=config.COLORS["bg_input"],
                          fg=config.COLORS["text_main"], insertbackground=config.COLORS["text_main"], relief="flat")
        e_subj.grid(row=1, column=1, sticky="ew", padx=3, ipady=2)
        tk.Label(ff, text="Deadline", font=("Segoe UI", 9), bg=config.COLORS["bg_card"],
                 fg=config.COLORS["text_sub"]).grid(row=0, column=2, sticky="w")
        e_date = tk.Entry(ff, font=("Segoe UI", 11), bg=config.COLORS["bg_input"],
                          fg=config.COLORS["text_main"], insertbackground=config.COLORS["text_main"], relief="flat")
        e_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        e_date.grid(row=1, column=2, sticky="ew", padx=3, ipady=2)
        add_btn = tk.Label(ff, text="  Add  ", font=("Segoe UI", 10, "bold"),
                           bg=config.COLORS["purple"], fg="#FFF", padx=16, pady=7, cursor="hand2")
        add_btn.grid(row=1, column=3, padx=(6, 0))

        lf = tk.Frame(inner, bg=config.COLORS["bg_main"])
        lf.pack(fill="both", expand=True, padx=28)
        lf_detail = tk.Frame(inner, bg=config.COLORS["bg_main"])
        lf_detail.pack(fill="both", expand=True, padx=28)

        def _refresh():
            for w in lf.winfo_children():
                w.destroy()
            for w in lf_detail.winfo_children():
                w.destroy()
            ts = sorted(self.db.get_tasks(), key=lambda t: (t["status"] != "pending", t["id"]))
            if not ts:
                tk.Label(lf, text="🎉  No tasks yet", font=("Segoe UI", 12),
                         bg=config.COLORS["bg_main"], fg=config.COLORS["text_sub"]).pack(pady=30)
                return
            # Group by subject — show project-level cards
            from collections import defaultdict
            groups = defaultdict(list)
            for t in ts:
                groups[t.get("subject", "Other")].append(t)
            for subj, items in groups.items():
                total = len(items)
                done = sum(1 for t in items if t["status"] == "completed")
                dl = sorted([t.get("deadline", "") for t in items if t.get("deadline")])
                deadline = dl[-1] if dl else "—"
                prios = [t.get("priority", 50) for t in items]
                avg_prio = int(sum(prios) / len(prios)) if prios else 50
                if avg_prio >= 80:
                    pc = config.COLORS["red"]
                elif avg_prio >= 50:
                    pc = config.COLORS["orange"]
                else:
                    pc = config.COLORS["green"]
                # Project card
                card = tk.Frame(lf, bg=config.COLORS["bg_card"], padx=14, pady=10,
                                highlightbackground=config.COLORS["border"], highlightthickness=1)
                card.pack(fill="x", pady=3)
                # Left: status dot + title
                all_done = done == total
                dot_c = config.COLORS["green"] if all_done else config.COLORS["blue"]
                c = tk.Canvas(card, width=10, height=10, bg=config.COLORS["bg_card"], highlightthickness=0)
                c.create_oval(2, 2, 8, 8, fill=dot_c, outline="")
                c.pack(side="left", padx=(0, 10))
                tk.Label(card, text=subj, font=("Segoe UI", 12, "bold"),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"]).pack(side="left")
                # Priority
                tk.Label(card, text=f"Prior: {avg_prio}", font=("Segoe UI", 9, "bold"),
                         bg=config.COLORS["bg_card"], fg=pc).pack(side="left", padx=12)
                # Deadline
                tk.Label(card, text=f"📅 {deadline}", font=("Segoe UI", 9),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"]).pack(side="left", padx=6)
                # Progress
                tk.Label(card, text=f"{done}/{total} done", font=("Segoe UI", 9),
                         bg=config.COLORS["bg_card"],
                         fg=config.COLORS["green"] if all_done else config.COLORS["text_sub"]).pack(side="right")
                # Delete project button — removes all tasks under this subject
                del_btn = tk.Label(card, text=" 🗑 ", font=("Segoe UI", 9, "bold"),
                                   bg=config.COLORS["red"], fg="#FFF",
                                   padx=8, pady=3, cursor="hand2")
                del_btn.pack(side="right", padx=4)
                del_btn.bind("<Button-1>", lambda e, s=subj, n=total:
                             messagebox.askyesno("Delete Project",
                                                 f"Delete project \"{s}\" and all its {n} tasks?\n\n"
                                                 "This includes all daily subtasks split from it.",
                                                 parent=self.win) and (
                                 db.delete_tasks_by_subject(s), _refresh()))
                # Expand button
                exp_btn = tk.Label(card, text="▼", font=("Segoe UI", 9),
                                   bg=config.COLORS["bg_card"], fg=config.COLORS["text_muted"],
                                   cursor="hand2", padx=6)
                exp_btn.pack(side="right")
                exp_btn.bind("<Button-1>", lambda e, it=items, s=subj: _show_detail(s, it))

        def _show_detail(subj, items):
            for w in lf_detail.winfo_children():
                w.destroy()
            dcard = Card(lf_detail, title=f"📋  {subj}", icon="", pad=14)
            dcard.pack(fill="x", pady=(8, 0))
            for t in items:
                TaskRow(dcard, t,
                        lambda tid, it=items: (
                            db.update_task(tid, status="completed"), _refresh()),
                        lambda tid, it=items: (
                            messagebox.askyesno("Confirm", "Delete?") and (db.delete_task(tid), _refresh())),
                        ).pack(fill="x", pady=2)

        def _add(e=None):
            t = e_title.get().strip()
            if not t:
                messagebox.showwarning("Warning", "Please enter a task name!")
                return
            self.db.add_task(t, e_subj.get().strip() or "Other", e_date.get().strip())
            e_title.delete(0, "end")
            e_subj.delete(0, "end")
            _refresh()

        add_btn.bind("<Button-1>", _add)
        e_title.bind("<Return>", _add)
        db = self.db  # capture for closures
        _refresh()

    # ═══ 4. AI Planner ═══
    def _show_ai(self):
        self._clear_main()
        _, __, inner = self._scroll(self.main_area)
        tk.Label(inner, text="🤖  AI Planner", font=("Segoe UI", 20, "bold"),
                 bg=config.COLORS["bg_main"], fg=config.COLORS["text_main"]).pack(fill="x", padx=28, pady=(18, 4))
        tk.Label(inner, text="Powered by DeepSeek — describe your goal, AI plans and analyzes",
                 font=("Segoe UI", 10), bg=config.COLORS["bg_main"],
                 fg=config.COLORS["text_sub"]).pack(fill="x", padx=28, pady=(0, 8))

        # Mode selector
        mode_f = tk.Frame(inner, bg=config.COLORS["bg_main"])
        mode_f.pack(fill="x", padx=28, pady=(0, 12))
        self.ai_mode = tk.StringVar(value="plan")
        for text, mode in [("🧠 Smart Plan", "plan"), ("🔄 Replan", "replan"), ("📝 Diary", "diary")]:
            b = tk.Label(mode_f, text=text, font=("Segoe UI", 11),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"],
                         padx=16, pady=8, cursor="hand2",
                         highlightbackground=config.COLORS["border"], highlightthickness=1)
            b.pack(side="left", padx=(0, 8))
            b.bind("<Button-1>",
                   lambda e, m=mode, b1=b: (
                       self.ai_mode.set(m),
                       [b2.configure(bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"])
                        for b2 in mode_f.winfo_children()],
                       b1.configure(bg=config.COLORS["purple"], fg="#FFF"),
                   ))

        # Input
        in_card = Card(inner, title="✍️  What's your goal?", icon="")
        in_card.pack(fill="x", padx=28, pady=(0, 12))
        self.ai_input = tk.Text(in_card, height=4, font=("Segoe UI", 12),
                                bg=config.COLORS["bg_input"], fg=config.COLORS["text_main"],
                                insertbackground=config.COLORS["text_main"], relief="flat",
                                padx=12, pady=12, wrap="word")
        self.ai_input.pack(fill="x")
        go_f = tk.Frame(in_card, bg=config.COLORS["bg_card"])
        go_f.pack(fill="x", pady=(12, 0))
        go_btn = tk.Label(go_f, text="🤖  Analyze", font=("Segoe UI", 12, "bold"),
                          bg=config.COLORS["purple"], fg="#FFF", padx=20, pady=10, cursor="hand2")
        go_btn.pack(side="right")
        go_btn.bind("<Button-1>", lambda e: self._run_ai())
        self.ai_status = tk.Label(go_f, text="", font=("Segoe UI", 9),
                                  bg=config.COLORS["bg_card"], fg=config.COLORS["text_muted"])
        self.ai_status.pack(side="left", pady=(4, 0))

        # Quick tip
        tips = tk.Frame(inner, bg=config.COLORS["bg_main"])
        tips.pack(fill="x", padx=28, pady=(0, 8))
        for tip in ["6/30 Computer Architecture exam — review textbook Mon, practice problems Tue-Wed"]:
            t = tk.Label(tips, text=f"💡  Try: {tip}", font=("Segoe UI", 9),
                         bg=config.COLORS["bg_main"], fg=config.COLORS["text_muted"], cursor="hand2")
            t.pack(anchor="w")
            t.bind("<Button-1>",
                   lambda e, tx=tip: (self.ai_input.delete("1.0", "end"), self.ai_input.insert("1.0", tx)))

        # Results
        self.ai_result = tk.Frame(inner, bg=config.COLORS["bg_main"])
        self.ai_result.pack(fill="both", padx=28)

    def _run_ai(self):
        if self.ai_loading:
            return
        mode = self.ai_mode.get()

        if mode == "replan":
            pending = self.db.get_pending_tasks()
            if not pending:
                messagebox.showinfo("Info", "No pending tasks!\nUse Smart Plan to create tasks first.")
                return
            if not self.api_key:
                self._prompt_api_key()
                return
            if not self.api_key:
                return
            self.ai_loading = True
            today = datetime.now().strftime("%Y-%m-%d")
            tasks_list = "\n".join([
                f"- [{t['subject']}] {t['title']} "
                f"(deadline:{t.get('deadline', 'none')}, hours:{t.get('estimated_hours', 0)}h, "
                f"importance:{t.get('importance', 3)}, urgency:{t.get('urgency', 3)})"
                for t in pending
            ])
            system_prompt = config.PROMPTS["plan"].replace("{today}", today)
            text = config.PROMPTS["replan"].replace("{today}", today).replace("{tasks_list}", tasks_list)
            call_mode = "plan"
        else:
            text = self.ai_input.get("1.0", "end").strip()
            if not text:
                messagebox.showwarning("Warning", "Please enter your goal!")
                return
            if not self.api_key:
                self._prompt_api_key()
                return
            if not self.api_key:
                return
            self.ai_loading = True
            today = datetime.now().strftime("%Y-%m-%d")
            raw_sp = config.PROMPTS.get(mode, config.PROMPTS["plan"])
            system_prompt = raw_sp.replace("{today}", today) if "{today}" in raw_sp else None
            call_mode = mode

        self.ai_status.config(text="⏳  Analyzing...")
        for w in self.ai_result.winfo_children():
            w.destroy()

        _mode = mode
        _text = text
        _sp = system_prompt
        _cm = call_mode

        def _work():
            result = AIClient.ask(_cm, _text, self.api_key, system_prompt=_sp)
            self.win.after(0, lambda: self._show_ai_result(_mode, result, _text))

        threading.Thread(target=_work, daemon=True).start()

    def _show_ai_result(self, mode, result, raw_text):
        self.ai_loading = False
        self.ai_status.config(text="")
        if "error" in result:
            messagebox.showerror("AI Error", result["error"])
            return
        for w in self.ai_result.winfo_children():
            w.destroy()

        if mode in ("plan", "replan"):
            card = Card(self.ai_result, title="📋  Plan Result", icon="")
            card.pack(fill="x", pady=(6, 10))
            info_f = tk.Frame(card, bg=config.COLORS["bg_card"])
            info_f.pack(fill="x", pady=(0, 10))
            info_items = [
                ("📌 Title", result.get("title", "")),
                ("📅 Deadline", result.get("deadline", "")),
                ("⏱ Hours", f"{result.get('hours', 0)}h"),
                ("🏷 Type", result.get("type", "")),
                ("⭐ Importance", f"{result.get('importance', '?')}/5"),
                ("🔥 Urgency", f"{result.get('urgency', '?')}/5"),
                ("🎯 Priority", f"{result.get('priority', '?')}"),
            ]
            for i, (lb, vl) in enumerate(info_items):
                if vl and vl != "?/5" and vl != "?":
                    tk.Label(info_f, text=f"{lb}: {vl}", font=("Segoe UI", 10),
                             bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"]
                             ).grid(row=i // 3, column=i % 3, sticky="w", padx=4, pady=2)

            wt = result.get("weekly_theme", "")
            if wt:
                wtf = tk.Frame(card, bg=config.COLORS["bg_accent"])
                wtf.pack(fill="x", pady=(4, 10))
                tk.Label(wtf, text=f"🎯  Weekly Theme: {wt}", font=("Segoe UI", 12, "bold"),
                         bg=config.COLORS["bg_accent"], fg=config.COLORS["purple"]).pack(padx=14, pady=8)

            plan = result.get("plan", [])
            if plan:
                plan_card = Card(self.ai_result, title=f"📅  Daily Plan ({len(plan)} days)", icon="")
                plan_card.pack(fill="x", pady=(4, 8))
                for item in plan:
                    d = item.get("date", "")
                    wd = ""
                    try:
                        wd = config.WEEKDAYS_CN[datetime.strptime(d, "%Y-%m-%d").weekday()]
                    except Exception:
                        pass
                    day_hdr = tk.Frame(plan_card, bg=config.COLORS["bg_card"])
                    day_hdr.pack(fill="x", pady=(6, 2))
                    tk.Label(day_hdr, text=f"📅  {d} {wd}", font=("Segoe UI", 12, "bold"),
                             bg=config.COLORS["bg_card"], fg=config.COLORS["purple"]).pack(anchor="w")
                    sep = tk.Frame(plan_card, bg=config.COLORS["divider"], height=1)
                    sep.pack(fill="x")

                    mf = item.get("main_focus", {}) if isinstance(item.get("main_focus"), dict) else {}
                    old_title = item.get("title", "")
                    if old_title and not mf:
                        mf = {"title": old_title, "hours": item.get("hours", 0),
                              "note": item.get("note", "")}
                    if mf and mf.get("title"):
                        mf_row = tk.Frame(plan_card, bg=config.COLORS["bg_card"])
                        mf_row.pack(fill="x", pady=2)
                        tk.Label(mf_row, text="🔵 Focus", font=("Segoe UI", 9, "bold"),
                                 bg=config.COLORS["blue"], fg="#FFF", padx=6, pady=2).pack(
                            side="left", padx=(0, 8))
                        tk.Label(mf_row, text=mf.get("title", ""), font=("Segoe UI", 11, "bold"),
                                 bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                                 anchor="w").pack(side="left", fill="x", expand=True)
                        mh = mf.get("hours", 0)
                        if mh:
                            tk.Label(mf_row, text=f"⏱ {mh}h", font=("Segoe UI", 9),
                                     bg=config.COLORS["bg_card"],
                                     fg=config.COLORS["text_sub"]).pack(side="right")
                        mn = mf.get("note", "")
                        if mn:
                            nt_row = tk.Frame(plan_card, bg=config.COLORS["bg_card"])
                            nt_row.pack(fill="x")
                            tk.Label(nt_row, text=f"    💡 {mn}", font=("Segoe UI", 8),
                                     bg=config.COLORS["bg_card"],
                                     fg=config.COLORS["text_muted"]).pack(anchor="w")

                    qts = item.get("quick_tasks", [])
                    if qts:
                        for qt in qts:
                            qt_row = tk.Frame(plan_card, bg=config.COLORS["bg_card"])
                            qt_row.pack(fill="x", pady=1)
                            tk.Label(qt_row, text="🟢 Quick", font=("Segoe UI", 9, "bold"),
                                     bg=config.COLORS["green"], fg="#FFF", padx=6, pady=2).pack(
                                side="left", padx=(0, 8))
                            tk.Label(qt_row, text=qt.get("title", ""), font=("Segoe UI", 10),
                                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                                     anchor="w").pack(side="left", fill="x", expand=True)
                            qh = qt.get("hours", 0)
                            if qh:
                                tk.Label(qt_row, text=f"⏱ {qh}h", font=("Segoe UI", 8),
                                         bg=config.COLORS["bg_card"],
                                         fg=config.COLORS["text_sub"]).pack(side="right")
                            qn = qt.get("note", "")
                            if qn:
                                tk.Label(qt_row, text=f"💡 {qn}", font=("Segoe UI", 8),
                                         bg=config.COLORS["bg_card"],
                                         fg=config.COLORS["text_muted"]).pack(side="right", padx=6)

                import_btn = tk.Label(plan_card, text="✅  Import All Tasks",
                                      font=("Segoe UI", 11, "bold"), bg=config.COLORS["green"],
                                      fg="#FFF", padx=20, pady=10, cursor="hand2")
                import_btn.pack(pady=(12, 0))

                def _imp():
                    tl = []
                    meta = {"importance": result.get("importance", 3),
                            "urgency": result.get("urgency", 3),
                            "priority": result.get("priority", 50),
                            "weekly_theme": result.get("weekly_theme", "")}
                    for it in plan:
                        mf = it.get("main_focus", {}) if isinstance(it.get("main_focus"), dict) else {}
                        old_t = it.get("title", "")
                        if old_t and not mf:
                            tl.append({
                                "title": old_t, "subject": result.get("title", ""),
                                "deadline": result.get("deadline", ""),
                                "plan_date": it.get("date", ""), "hours": it.get("hours", 0),
                                "task_type": "main_focus", "importance": meta["importance"],
                                "urgency": meta["urgency"], "priority": meta["priority"],
                                "weekly_theme": meta["weekly_theme"],
                            })
                        else:
                            if mf and mf.get("title"):
                                tl.append({
                                    "title": mf["title"], "subject": result.get("title", ""),
                                    "deadline": result.get("deadline", ""),
                                    "plan_date": it.get("date", ""), "hours": mf.get("hours", 0),
                                    "task_type": "main_focus", "importance": meta["importance"],
                                    "urgency": meta["urgency"], "priority": meta["priority"],
                                    "weekly_theme": meta["weekly_theme"],
                                })
                            for qt in it.get("quick_tasks", []):
                                tl.append({
                                    "title": qt["title"], "subject": result.get("title", ""),
                                    "deadline": result.get("deadline", ""),
                                    "plan_date": it.get("date", ""), "hours": qt.get("hours", 0),
                                    "task_type": "quick_task",
                                    "importance": max(1, meta["importance"] - 1),
                                    "urgency": meta["urgency"],
                                    "priority": max(0, meta["priority"] - 20),
                                    "weekly_theme": meta["weekly_theme"],
                                })
                    self.db.add_tasks_batch(tl)
                    nf = sum(1 for t in tl if t['task_type'] == 'main_focus')
                    nq = sum(1 for t in tl if t['task_type'] == 'quick_task')
                    messagebox.showinfo("Imported", f"{len(tl)} tasks imported ({nf} focus + {nq} quick)!")

                import_btn.bind("<Button-1>", lambda e: _imp())

            adv = result.get("advice", "")
            if adv:
                ac = Card(self.ai_result, title="💡  AI Advice", icon="")
                ac.pack(fill="x", pady=(4, 10))
                tk.Label(ac, text=adv, font=("Segoe UI", 10), bg=config.COLORS["bg_card"],
                         fg=config.COLORS["text_main"], wraplength=1200).pack(anchor="w")
            if mode == "plan":
                self.ai_input.delete("1.0", "end")

        elif mode == "diary":
            card = Card(self.ai_result, title="📊  Diary Analysis", icon="")
            card.pack(fill="x", pady=(6, 10))

            mood = result.get("mood", {})
            me = {"happy": "😊", "tired": "😫", "anxious": "😰", "sad": "😢",
                  "calm": "😌", "excited": "🤩", "bored": "😐"}.get(mood.get("primary", ""), "😶")
            mr = tk.Frame(card, bg=config.COLORS["bg_card"])
            mr.pack(fill="x", pady=4)
            tk.Label(mr, text=f"{me}  Mood", font=("Segoe UI", 11, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                     width=12, anchor="w").pack(side="left")
            sc = mood.get("score", 5)
            bar = tk.Frame(mr, bg=config.COLORS["bg_input"], height=18)
            bar.pack(side="left", fill="x", expand=True, padx=8)
            tk.Frame(bar, bg=config.COLORS["green"] if sc >= 6 else config.COLORS["orange"],
                     width=sc * 30, height=18).place(x=0, y=0, width=sc * 30, height=18)
            tk.Label(mr, text=f"{sc}/10", font=("Segoe UI", 11, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"]).pack(side="right")

            sleep = result.get("sleep", {})
            si = {"good": "😴💤", "ok": "😴", "bad": "😫⚠️", "unknown": "❓"}.get(
                sleep.get("quality", ""), "❓")
            sr = tk.Frame(card, bg=config.COLORS["bg_card"])
            sr.pack(fill="x", pady=4)
            tk.Label(sr, text=f"{si}  Sleep", font=("Segoe UI", 11, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                     width=12, anchor="w").pack(side="left")
            tk.Label(sr, text=f"{sleep.get('hours', 0)}h · {sleep.get('quality', '')}",
                     font=("Segoe UI", 11), bg=config.COLORS["bg_card"],
                     fg=config.COLORS["text_sub"]).pack(side="left")

            for label, items, color in [
                ("✨ Highlights", result.get("highlights", []), config.COLORS["green"]),
                ("💔 Lowlights", result.get("lowlights", []), config.COLORS["red"]),
            ]:
                if items:
                    fr = tk.Frame(card, bg=config.COLORS["bg_card"])
                    fr.pack(fill="x", pady=2)
                    tk.Label(fr, text=f"{label}", font=("Segoe UI", 10, "bold"),
                             bg=config.COLORS["bg_card"], fg=color, width=12, anchor="w").pack(
                        side="left", anchor="n")
                    tf2 = tk.Frame(fr, bg=config.COLORS["bg_card"])
                    tf2.pack(side="left", fill="x", expand=True)
                    for it in items:
                        tk.Label(tf2, text=f"• {it}", font=("Segoe UI", 9),
                                 bg=config.COLORS["bg_card"],
                                 fg=config.COLORS["text_sub"], anchor="w").pack(anchor="w")

            reply = result.get("reply", "")
            if reply:
                rc = Card(self.ai_result, title="💬  AI Says", icon="")
                rc.pack(fill="x", pady=(8, 10))
                tk.Label(rc, text=reply, font=("Segoe UI", 11), bg=config.COLORS["bg_card"],
                         fg=config.COLORS["purple"], wraplength=1200).pack(anchor="w")

            sugs = result.get("suggestions", [])
            if sugs:
                sc2 = Card(self.ai_result, title="💡  Suggestions", icon="")
                sc2.pack(fill="x", pady=(4, 10))
                for s in sugs:
                    tk.Label(sc2, text=f"• {s}", font=("Segoe UI", 10),
                             bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                             wraplength=1200, anchor="w").pack(anchor="w", pady=2)

            self.db.add_diary(raw_text, result)
            save_btn = tk.Label(self.ai_result, text="✅  Diary saved", font=("Segoe UI", 10),
                                bg=config.COLORS["bg_main"], fg=config.COLORS["green"])
            save_btn.pack(pady=(4, 10))
            self.ai_input.delete("1.0", "end")

            # Auto-trigger discover analysis after diary entry (with cooldown)
            task_count = len(self.db.data.get("tasks", []))
            diary_count = len(self.db.data.get("diary", []))
            if task_count + diary_count >= 3:
                def _auto_discover():
                    last = self.db.get_discover_last_run()
                    if last:
                        try:
                            last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M")
                            if (datetime.now() - last_dt).total_seconds() < 3600:
                                return  # Within cooldown
                        except Exception:
                            pass
                    self._run_discover_analysis()
                self.win.after(1500, _auto_discover)

    # ═══ 5. Vision ═══
    def _show_vision(self):
        self._clear_main()
        _, __, inner = self._scroll(self.main_area)
        tk.Label(inner, text="🌟  Life Vision", font=("Segoe UI", 20, "bold"),
                 bg=config.COLORS["bg_main"], fg=config.COLORS["text_main"]).pack(fill="x", padx=28, pady=(18, 4))
        tk.Label(inner, text="Write down who you want to become. AI helps you understand yourself.",
                 font=("Segoe UI", 10), bg=config.COLORS["bg_main"],
                 fg=config.COLORS["text_sub"]).pack(fill="x", padx=28, pady=(0, 14))

        in_card = Card(inner, title="✍️  Your Vision", icon="")
        in_card.pack(fill="x", padx=28, pady=(0, 12))
        tk.Label(in_card, text="e.g. I want to become an engineer who solves real problems with technology, "
                               "maintain reading and exercise habits, have my own team before 30",
                 font=("Segoe UI", 9), bg=config.COLORS["bg_card"],
                 fg=config.COLORS["text_muted"]).pack(anchor="w", pady=(0, 8))
        self.vision_input = tk.Text(in_card, height=3, font=("Segoe UI", 12),
                                    bg=config.COLORS["bg_input"], fg=config.COLORS["text_main"],
                                    insertbackground=config.COLORS["text_main"], relief="flat",
                                    padx=12, pady=12, wrap="word")
        self.vision_input.pack(fill="x")
        go_f = tk.Frame(in_card, bg=config.COLORS["bg_card"])
        go_f.pack(fill="x", pady=(10, 0))
        self.vision_status = tk.Label(go_f, text="", font=("Segoe UI", 9),
                                      bg=config.COLORS["bg_card"], fg=config.COLORS["text_muted"])
        self.vision_status.pack(side="left", pady=(4, 0))
        go_btn = tk.Label(go_f, text="🤖  Deep Analysis", font=("Segoe UI", 12, "bold"),
                          bg=config.COLORS["purple"], fg="#FFF", padx=20, pady=10, cursor="hand2")
        go_btn.pack(side="right")
        go_btn.bind("<Button-1>", lambda e: self._run_vision())

        self.vision_result = tk.Frame(inner, bg=config.COLORS["bg_main"])
        self.vision_result.pack(fill="both", padx=28)

        visions = self.db.get_visions()
        if visions:
            tc = Card(inner, title="📜  Vision Timeline", icon="")
            tc.pack(fill="x", padx=28, pady=(12, 20))

            # Detail panel (hidden until a vision is clicked)
            self.vision_detail = tk.Frame(inner, bg=config.COLORS["bg_main"])
            self.vision_detail.pack(fill="both", padx=28)

            for idx, v in enumerate(visions):
                a = v.get("analysis", {}) if isinstance(v.get("analysis"), dict) else {}
                date_str = v.get("date", "")
                themes = a.get("core_themes", [])

                # Vision card row
                r = tk.Frame(tc, bg=config.COLORS["bg_card"], padx=12, pady=8,
                             highlightbackground=config.COLORS["border"], highlightthickness=1,
                             cursor="hand2")
                r.pack(fill="x", pady=2)

                # Date
                tk.Label(r, text=date_str, font=("Segoe UI", 10, "bold"),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["purple"],
                         width=18, anchor="w").pack(side="left")

                # Raw preview
                raw = v.get("raw", "")
                preview = raw[:50] + "…" if len(raw) > 50 else raw
                tk.Label(r, text=preview, font=("Segoe UI", 10),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"],
                         anchor="w").pack(side="left", padx=10, fill="x", expand=True)

                # Core themes as tags
                if themes:
                    for th in themes[:3]:
                        tk.Label(r, text=f" {th} ", font=("Segoe UI", 9),
                                 bg=config.COLORS["bg_accent"], fg=config.COLORS["purple"],
                                 padx=6, pady=2).pack(side="right", padx=2)

                # Expand button
                exp_btn = tk.Label(r, text="▼", font=("Segoe UI", 10),
                                   bg=config.COLORS["bg_card"], fg=config.COLORS["text_muted"],
                                   cursor="hand2", padx=6)
                exp_btn.pack(side="right")

                # Click handlers — both row and button
                for w in [r, exp_btn]:
                    w.bind("<Button-1>", lambda e, v=v: self._show_vision_detail(v))

    def _show_vision_detail(self, v):
        """Show full vision details below the timeline."""
        for w in self.vision_detail.winfo_children():
            w.destroy()

        a = v.get("analysis", {}) if isinstance(v.get("analysis"), dict) else {}
        date_str = v.get("date", "")
        raw = v.get("raw", "")

        detail_card = Card(self.vision_detail, title=f"📋  Vision — {date_str}", icon="", pad=16)
        detail_card.pack(fill="x", pady=(8, 4))

        # Raw text
        tk.Label(detail_card, text="✍️  Original", font=("Segoe UI", 10, "bold"),
                 bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"]).pack(anchor="w")
        tk.Label(detail_card, text=raw, font=("Segoe UI", 11),
                 bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                 wraplength=1200, justify="left").pack(anchor="w", pady=(2, 12))

        # Core themes
        themes = a.get("core_themes", [])
        if themes:
            tk.Label(detail_card, text="🎯  Core Themes", font=("Segoe UI", 10, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"]).pack(anchor="w")
            tf = tk.Frame(detail_card, bg=config.COLORS["bg_card"])
            tf.pack(fill="x", pady=(2, 10))
            for th in themes:
                tk.Label(tf, text=f"  {th}  ", font=("Segoe UI", 11),
                         bg=config.COLORS["bg_accent"], fg=config.COLORS["purple"],
                         padx=10, pady=4).pack(side="left", padx=3)

        # Career path
        cp = a.get("career_path", "")
        if cp:
            tk.Label(detail_card, text="💼  Career Path", font=("Segoe UI", 10, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"]).pack(anchor="w", pady=(4, 2))
            tk.Label(detail_card, text=cp, font=("Segoe UI", 11),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                     wraplength=1200).pack(anchor="w", pady=(0, 10))

        # Habit gaps
        gaps = a.get("habit_gaps", [])
        if gaps:
            tk.Label(detail_card, text="📊  Current vs Vision", font=("Segoe UI", 10, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"]).pack(anchor="w", pady=(4, 2))
            for g in gaps:
                gr = tk.Frame(detail_card, bg=config.COLORS["bg_card"])
                gr.pack(fill="x", pady=2)
                tk.Label(gr, text=f"🎯 {g.get('goal', '')}", font=("Segoe UI", 11, "bold"),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"]).pack(side="left")
                tk.Label(gr, text=f"→ {g.get('status', '')}", font=("Segoe UI", 11),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["orange"]).pack(side="right")

        # Short-term
        st = a.get("short_term", [])
        if st:
            st_card = Card(self.vision_detail, title="⚡  This Week", icon="", pad=14)
            st_card.pack(fill="x", pady=(8, 4))
            for it in st:
                tk.Label(st_card, text=f"• {it}", font=("Segoe UI", 11),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                         wraplength=1200, anchor="w").pack(anchor="w", pady=2)

        # Mid-term
        mt = a.get("mid_term", [])
        if mt:
            mt_card = Card(self.vision_detail, title="🎯  Milestones", icon="", pad=14)
            mt_card.pack(fill="x", pady=(8, 4))
            for it in mt:
                tk.Label(mt_card, text=f"• {it}", font=("Segoe UI", 11),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                         wraplength=1200, anchor="w").pack(anchor="w", pady=2)

        # Inspiration
        insp = a.get("inspiration", "")
        if insp:
            tk.Label(detail_card, text=f"💫 {insp}", font=("Segoe UI", 12, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["purple"],
                     wraplength=1200).pack(anchor="w", pady=(10, 0))

        # Delete button
        del_btn = tk.Label(self.vision_detail, text="🗑  Delete this vision",
                           font=("Segoe UI", 10), bg=config.COLORS["bg_main"],
                           fg=config.COLORS["red"], cursor="hand2", pady=6)
        del_btn.pack(pady=(4, 10))
        del_btn.bind("<Button-1>", lambda e, d=date_str: (
            messagebox.askyesno("Delete Vision", f"Delete vision from {d}?",
                                parent=self.win) and (
                self.db.data.__setitem__("visions",
                    [x for x in self.db.data["visions"] if x.get("date") != d]),
                self.db.save(),
                self._show_vision())))

    def _run_vision(self):
        text = self.vision_input.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Warning", "Please write your vision first!")
            return
        if not self.api_key:
            self._prompt_api_key()
            return
        if not self.api_key:
            return

        self.vision_status.config(text="⏳  Analyzing...")
        for w in self.vision_result.winfo_children():
            w.destroy()

        def _work():
            result = AIClient.ask("vision", text, self.api_key)
            self.win.after(0, lambda: self._show_vision_result(result, text))

        threading.Thread(target=_work, daemon=True).start()

    def _show_vision_result(self, result, raw):
        self.vision_status.config(text="")
        if "error" in result:
            messagebox.showerror("AI Error", result["error"])
            return

        for w in self.vision_result.winfo_children():
            w.destroy()

        card = Card(self.vision_result, title="🔍  Deep Analysis", icon="")
        card.pack(fill="x", pady=(6, 10))
        themes = result.get("core_themes", [])
        if themes:
            tf = tk.Frame(card, bg=config.COLORS["bg_card"])
            tf.pack(fill="x", pady=(0, 8))
            for th in themes:
                tk.Label(tf, text=f"  {th}  ", font=("Segoe UI", 11),
                         bg=config.COLORS["bg_accent"], fg=config.COLORS["purple"],
                         padx=10, pady=4).pack(side="left", padx=4)

        cp = result.get("career_path", "")
        if cp:
            tk.Label(card, text="💼  Career Path", font=("Segoe UI", 11, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"]).pack(anchor="w", pady=(4, 2))
            tk.Label(card, text=cp, font=("Segoe UI", 10), bg=config.COLORS["bg_card"],
                     fg=config.COLORS["text_sub"], wraplength=1200).pack(anchor="w", pady=(0, 8))

        gaps = result.get("habit_gaps", [])
        if gaps:
            tk.Label(card, text="📊  Current vs Vision", font=("Segoe UI", 11, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"]).pack(anchor="w", pady=(4, 2))
            for g in gaps:
                r = tk.Frame(card, bg=config.COLORS["bg_card"])
                r.pack(fill="x", pady=2)
                tk.Label(r, text=f"🎯 {g.get('goal', '')}", font=("Segoe UI", 10, "bold"),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"]).pack(side="left")
                tk.Label(r, text=f"→ {g.get('status', '')}", font=("Segoe UI", 10),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["orange"]).pack(side="right")

        for label, items, icon in [
            ("This Week", result.get("short_term", []), "⚡"),
            ("Milestones", result.get("mid_term", []), "🎯"),
        ]:
            if items:
                ac = Card(self.vision_result, title=f"{icon}  {label}", icon="")
                ac.pack(fill="x", pady=(8, 8))
                for it in items:
                    tk.Label(ac, text=f"• {it}", font=("Segoe UI", 10),
                             bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                             wraplength=1200, anchor="w").pack(anchor="w", pady=2)

        insp = result.get("inspiration", "")
        if insp:
            ic = Card(self.vision_result, icon="")
            ic.pack(fill="x", pady=(4, 12))
            tk.Label(ic, text=f"💫 {insp}", font=("Segoe UI", 12, "bold"),
                     bg=config.COLORS["bg_card"], fg=config.COLORS["purple"], wraplength=1200).pack()

        self.db.add_vision(raw, result)
        self.vision_input.delete("1.0", "end")
        messagebox.showinfo("Saved", "Vision saved!\nScroll down to see your vision timeline.")

    # ═══ 6. Discover — AI Proactive Inquiry ═══
    def _show_discover(self):
        self._clear_main()
        _, __, inner = self._scroll(self.main_area)

        # Header
        tk.Label(inner, text="🔍  Discover", font=("Segoe UI", 20, "bold"),
                 bg=config.COLORS["bg_main"], fg=config.COLORS["text_main"]
                 ).pack(fill="x", padx=28, pady=(18, 4))
        tk.Label(inner,
                 text="AI observes your data patterns and asks questions to help "
                      "you understand yourself better.",
                 font=("Segoe UI", 10), bg=config.COLORS["bg_main"],
                 fg=config.COLORS["text_sub"]).pack(fill="x", padx=28, pady=(0, 8))

        # Analyze button row
        btn_frame = tk.Frame(inner, bg=config.COLORS["bg_main"])
        btn_frame.pack(fill="x", padx=28, pady=(0, 16))
        analyze_btn = tk.Label(btn_frame, text="🔬  Analyze My Patterns",
                               font=("Segoe UI", 13, "bold"),
                               bg=config.COLORS["purple"], fg="#FFF",
                               padx=24, pady=14, cursor="hand2")
        analyze_btn.pack(side="left")
        analyze_btn.bind("<Button-1>", lambda e: self._run_discover_analysis())

        self.discover_status = tk.Label(btn_frame, text="",
                                        font=("Segoe UI", 9),
                                        bg=config.COLORS["bg_main"],
                                        fg=config.COLORS["text_muted"])
        self.discover_status.pack(side="left", padx=16)

        # Last run info
        last_run = self.db.get_discover_last_run()
        if last_run:
            tk.Label(btn_frame, text=f"Last analysis: {last_run}",
                     font=("Segoe UI", 9), bg=config.COLORS["bg_main"],
                     fg=config.COLORS["text_muted"]).pack(side="right")

        # ── Section 1: Pending Questions ──
        pending_insights = self.db.get_insights("pending")
        pc = Card(inner, title="💬  AI wants to know...", icon="", pad=16)
        pc.pack(fill="x", padx=28, pady=(0, 12))

        if pending_insights:
            for insight in pending_insights:
                InsightCard(pc, insight,
                            on_answer=self._answer_insight
                            ).pack(fill="x", pady=4)
        else:
            tk.Label(pc,
                     text='No pending questions. Click "Analyze My Patterns" '
                          'to let AI discover something about you!',
                     font=("Segoe UI", 10), bg=config.COLORS["bg_card"],
                     fg=config.COLORS["text_muted"]).pack(pady=12)

        # ── Section 2: Confirmed Patterns ──
        confirmed_insights = self.db.get_insights("confirmed")
        cc = Card(inner, title="✅  Confirmed Patterns", icon="", pad=16)
        cc.pack(fill="x", padx=28, pady=(0, 12))

        if confirmed_insights:
            for insight in confirmed_insights:
                InsightCard(cc, insight).pack(fill="x", pady=4)
            # Link to Operating Manual
            link_f = tk.Frame(cc, bg=config.COLORS["bg_card"])
            link_f.pack(fill="x", pady=(8, 0))
            manual_link = tk.Label(link_f,
                                   text=f"📖  View all {len(confirmed_insights)} patterns in Operating Manual →",
                                   font=("Segoe UI", 10, "bold"),
                                   bg=config.COLORS["bg_card"], fg=config.COLORS["purple"],
                                   cursor="hand2")
            manual_link.pack(side="right")
            manual_link.bind("<Button-1>", lambda e: self._nav_to_page("manual"))
        else:
            tk.Label(cc,
                     text="Answer AI's questions above to build your self-knowledge base.",
                     font=("Segoe UI", 10), bg=config.COLORS["bg_card"],
                     fg=config.COLORS["text_muted"]).pack(pady=12)

        # ── Section 3: Refuted Hypotheses ──
        refuted_insights = self.db.get_insights("refuted")
        rc = Card(inner, title="❌  Refuted Hypotheses", icon="", pad=16)
        rc.pack(fill="x", padx=28, pady=(0, 20))

        if refuted_insights:
            self.refuted_visible = tk.BooleanVar(value=False)
            toggle_btn = tk.Label(rc,
                                  text=f"▶  Show refuted ({len(refuted_insights)})",
                                  font=("Segoe UI", 10), bg=config.COLORS["bg_card"],
                                  fg=config.COLORS["purple"], cursor="hand2", anchor="w")
            toggle_btn.pack(fill="x", pady=(0, 6))

            self.refuted_container = tk.Frame(rc, bg=config.COLORS["bg_card"])

            def _toggle_refuted():
                if self.refuted_visible.get():
                    self.refuted_container.pack_forget()
                    toggle_btn.config(
                        text=f"▶  Show refuted ({len(refuted_insights)})")
                    self.refuted_visible.set(False)
                else:
                    self.refuted_container.pack(fill="x")
                    toggle_btn.config(text="▼  Hide refuted")
                    self.refuted_visible.set(True)
                    if not self.refuted_container.winfo_children():
                        for insight in refuted_insights:
                            InsightCard(self.refuted_container, insight).pack(
                                fill="x", pady=4)

            toggle_btn.bind("<Button-1>", lambda e: _toggle_refuted())
        else:
            tk.Label(rc, text="No refuted hypotheses yet.",
                     font=("Segoe UI", 10), bg=config.COLORS["bg_card"],
                     fg=config.COLORS["text_muted"]).pack(pady=12)

    def _run_discover_analysis(self):
        """Trigger AI pattern analysis on user data."""
        if self.ai_loading:
            return
        if not self.api_key:
            self._prompt_api_key()
            return
        if not self.api_key:
            return

        # Cooldown: max once per hour to save API credits
        last = self.db.get_discover_last_run()
        if last:
            try:
                last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M")
                diff = (datetime.now() - last_dt).total_seconds()
                if diff < 3600:
                    mins_left = 60 - int(diff / 60)
                    messagebox.showinfo(
                        "Cooldown",
                        f"Please wait ~{mins_left} minutes before analyzing again.\n"
                        "AI analysis uses API credits — limited to once per hour.")
                    return
            except Exception:
                pass

        self.ai_loading = True
        self.discover_status.config(text="⏳  Analyzing your data patterns...")

        # Aggregate data and send to AI
        data_summary = self.db.aggregate_for_discover()
        user_msg = json.dumps(data_summary, ensure_ascii=False, indent=2)

        def _work():
            result = AIClient.ask("discover", user_msg, self.api_key)
            self.win.after(0, lambda: self._show_discover_result(result))

        threading.Thread(target=_work, daemon=True).start()

    def _show_discover_result(self, result):
        """Handle AI pattern analysis response."""
        self.ai_loading = False
        self.discover_status.config(text="")

        if "error" in result:
            messagebox.showerror("AI Error", result["error"])
            return

        # Persist insights
        insights_data = result.get("insights", [])
        count_added = 0
        for ins in insights_data:
            self.db.add_insight({
                "title": ins.get("title", ""),
                "hypothesis": ins.get("hypothesis", ""),
                "evidence": ins.get("evidence", []),
                "confidence": ins.get("confidence", 0.5),
                "question": ins.get("question", ""),
                "category": ins.get("category", "general"),
                "status": "pending",
            })
            count_added += 1

        self.db.set_discover_last_run()
        self._update_discover_badge()
        self._show_discover()

        summary = result.get("summary", "")
        if count_added > 0:
            msg = f"Found {count_added} new insight{'s' if count_added > 1 else ''}!"
            if summary:
                msg += f"\n\n{summary}"
            messagebox.showinfo("Analysis Complete", msg)
        else:
            if summary:
                messagebox.showinfo("Analysis Complete",
                                    f"No strong patterns found yet.\n\n{summary}")
            else:
                messagebox.showinfo("Analysis Complete",
                                    "No strong patterns found yet.\n"
                                    "Keep using the app — more data helps AI find patterns!")

    def _answer_insight(self, insight_id, answer_text):
        """User answers a pending insight question. AI validates the answer."""
        answer_text = answer_text.strip()
        if not answer_text:
            messagebox.showwarning("Warning", "Please type your answer first!")
            return
        if self.ai_loading:
            return

        # Find the insight
        insight = None
        for i in self.db.data.get("insights", []):
            if i["id"] == insight_id:
                insight = i
                break
        if not insight:
            return

        self.ai_loading = True
        self.discover_status.config(text="⏳  AI is thinking about your answer...")

        # Build validation prompt
        val_text = (
            f"Hypothesis: {insight['hypothesis']}\n"
            f"Question asked: {insight['question']}\n"
            f"User's answer: \"{answer_text}\""
        )

        def _work():
            result = AIClient.ask("discover_validate", val_text, self.api_key)
            self.win.after(0, lambda: self._show_answer_result(
                insight_id, answer_text, result))

        threading.Thread(target=_work, daemon=True).start()

    def _show_answer_result(self, insight_id, answer_text, result):
        """Handle AI validation of a user's answer."""
        self.ai_loading = False
        self.discover_status.config(text="")

        if "error" in result:
            messagebox.showerror("AI Error", result["error"])
            return

        status = result.get("status", "confirmed")
        reply = result.get("reply", "")

        self.db.update_insight(insight_id,
                               status=status,
                               user_answer=answer_text,
                               confirmed_at=datetime.now().strftime("%Y-%m-%d"))
        self._update_discover_badge()
        self._show_discover()

        # Suggest re-synthesis if manual needs updating
        if status == "confirmed" and self.db.needs_resynthesis():
            manual = self.db.get_manual()
            confirmed_now = self.db.get_confirmed_insight_count()
            if manual:
                # Manual exists but is stale
                def _hint_resynth():
                    if messagebox.askyesno(
                        "Update Manual?",
                        f"You now have {confirmed_now} confirmed patterns.\n"
                        "Your Operating Manual may be out of date.\n\n"
                        "Re-synthesize now?"
                    ):
                        self._nav_to_page("manual")
                        self.win.after(300, self._run_manual_synthesis)
                self.win.after(500, _hint_resynth)
            elif confirmed_now >= 2:
                # No manual yet, enough data
                def _hint_first():
                    if messagebox.askyesno(
                        "Create Manual?",
                        f"You have {confirmed_now} confirmed patterns — enough "
                        "to synthesize your first Operating Manual!\n\n"
                        "Create it now?"
                    ):
                        self._nav_to_page("manual")
                        self.win.after(300, self._run_manual_synthesis)
                self.win.after(500, _hint_first)

        if reply:
            title = "✅ Insight Confirmed!" if status == "confirmed" else "❌ Insight Refuted"
            messagebox.showinfo(title, reply)

    # ═══ 7. Manual — Operating Manual ═══
    def _show_manual(self):
        self._clear_main()
        _, __, inner = self._scroll(self.main_area)

        # Header
        tk.Label(inner, text="📖  My Operating Manual", font=("Segoe UI", 20, "bold"),
                 bg=config.COLORS["bg_main"], fg=config.COLORS["text_main"]
                 ).pack(fill="x", padx=28, pady=(18, 4))
        tk.Label(inner,
                 text="Synthesized from your confirmed patterns — a living guide to how you work best.",
                 font=("Segoe UI", 10), bg=config.COLORS["bg_main"],
                 fg=config.COLORS["text_sub"]).pack(fill="x", padx=28, pady=(0, 12))

        manual = self.db.get_manual()
        confirmed_count = self.db.get_confirmed_insight_count()

        # ── Action bar ──
        btn_frame = tk.Frame(inner, bg=config.COLORS["bg_main"])
        btn_frame.pack(fill="x", padx=28, pady=(0, 16))

        needs_update = self.db.needs_resynthesis()
        syn_btn = tk.Label(btn_frame,
                           text="🔄  Re-synthesize" if manual else "🔬  Synthesize My Patterns",
                           font=("Segoe UI", 12, "bold"),
                           bg=config.COLORS["orange"] if (needs_update and manual) else config.COLORS["purple"],
                           fg="#FFF", padx=20, pady=12, cursor="hand2")
        syn_btn.pack(side="left")
        syn_btn.bind("<Button-1>", lambda e: self._run_manual_synthesis())

        self.manual_status = tk.Label(btn_frame, text="",
                                      font=("Segoe UI", 9),
                                      bg=config.COLORS["bg_main"],
                                      fg=config.COLORS["text_muted"])
        self.manual_status.pack(side="left", padx=14)

        if manual:
            last = manual.get("last_synthesized", "")
            count = manual.get("insight_count_at_synthesis", 0)
            tk.Label(btn_frame,
                     text=f"Synthesized: {last}  ·  from {count} insights",
                     font=("Segoe UI", 9), bg=config.COLORS["bg_main"],
                     fg=config.COLORS["text_muted"]).pack(side="right")

        if confirmed_count < 2 and not manual:
            # ── Empty state ──
            ec = Card(inner, title="🔍  Not enough data yet", icon="", pad=20)
            ec.pack(fill="x", padx=28, pady=(0, 16))
            tk.Label(ec,
                     text="Your Operating Manual is built from confirmed patterns.\n\n"
                          "How to get started:\n"
                          "1. Go to Discover → Analyze My Patterns\n"
                          "2. Answer the AI's questions to confirm patterns\n"
                          "3. Come back here when you have at least 2 confirmed insights\n\n"
                          f"You currently have {confirmed_count} confirmed insight{'s' if confirmed_count != 1 else ''}.",
                     font=("Segoe UI", 11), bg=config.COLORS["bg_card"],
                     fg=config.COLORS["text_sub"], wraplength=800, justify="left").pack(pady=8)
            return

        if not manual:
            # Has enough insights but no manual yet
            ec = Card(inner, title="✨  Ready to synthesize!", icon="", pad=20)
            ec.pack(fill="x", padx=28, pady=(0, 16))
            tk.Label(ec,
                     text=f"You have {confirmed_count} confirmed patterns.\n"
                          "Let AI weave them into your personal Operating Manual.",
                     font=("Segoe UI", 11), bg=config.COLORS["bg_card"],
                     fg=config.COLORS["text_sub"]).pack(pady=8)
            return

        # ── Render Manual ──

        # Summary card
        summary = manual.get("summary", "")
        if summary:
            sc = tk.Frame(inner, bg=config.COLORS["bg_accent"],
                          highlightbackground=config.COLORS["purple"], highlightthickness=2)
            sc.pack(fill="x", padx=28, pady=(0, 16))
            tk.Label(sc, text="💡 " + summary, font=("Segoe UI", 13, "bold"),
                     bg=config.COLORS["bg_accent"], fg=config.COLORS["purple"],
                     wraplength=1200, justify="left").pack(padx=22, pady=16)

        # Causal chains
        chains = manual.get("causal_chains", [])
        if chains:
            cc = Card(inner, title="🔗  Your Causal Chains", icon="", pad=16)
            cc.pack(fill="x", padx=28, pady=(0, 14))
            for ch in chains:
                chain_steps = ch.get("chain", [])
                desc = ch.get("description", "")
                intervention = ch.get("intervention_point", "")
                advice = ch.get("intervention_advice", "")

                # Chain visual: step → step → step
                cf = tk.Frame(cc, bg=config.COLORS["bg_card"])
                cf.pack(fill="x", pady=(4, 6))

                parts = []
                for i, step in enumerate(chain_steps):
                    parts.append(step)
                    if i < len(chain_steps) - 1:
                        parts.append("→")
                chain_text = "  ".join(
                    f"⟶ {p}" if i > 0 and p != "→" else p
                    for i, p in enumerate(parts)
                )
                # Simpler: join with arrows in between
                chain_display = "  →  ".join(chain_steps)
                tk.Label(cf, text=chain_display, font=("Segoe UI", 11, "bold"),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"],
                         wraplength=1000).pack(anchor="w", pady=(0, 4))
                if desc:
                    tk.Label(cf, text=desc, font=("Segoe UI", 10, "italic"),
                             bg=config.COLORS["bg_card"], fg=config.COLORS["text_sub"],
                             wraplength=1000, justify="left").pack(anchor="w", pady=(0, 6))

                # Intervention
                if intervention:
                    intv_f = tk.Frame(cf, bg=config.COLORS["bg_input"])
                    intv_f.pack(fill="x", pady=(0, 4))
                    tk.Label(intv_f, text=f"🎯  Best intervention: {intervention}",
                             font=("Segoe UI", 9, "bold"),
                             bg=config.COLORS["bg_input"], fg=config.COLORS["orange"]
                             ).pack(anchor="w", padx=10, pady=6)
                    if advice:
                        tk.Label(intv_f, text=advice, font=("Segoe UI", 9),
                                 bg=config.COLORS["bg_input"], fg=config.COLORS["text_sub"],
                                 wraplength=1000, justify="left").pack(anchor="w", padx=10, pady=(0, 6))

                # Separator between chains
                tk.Frame(cf, bg=config.COLORS["divider"], height=1).pack(fill="x", pady=(4, 0))

        # Domains accordion
        domains = manual.get("domains", {})
        if domains:
            dc = Card(inner, title="📂  Patterns by Domain", icon="", pad=16)
            dc.pack(fill="x", padx=28, pady=(0, 14))

            domain_icons = {
                "productivity": "⚡", "mood": "🧠", "sleep": "😴",
                "habits": "🔄", "general": "💡",
            }
            self.domain_expanded = {}

            for domain_key, items in domains.items():
                if not items:
                    continue
                icon = domain_icons.get(domain_key, "📌")
                label = domain_key.capitalize()

                # Domain header (clickable toggle)
                d_header = tk.Frame(dc, bg=config.COLORS["bg_card"], cursor="hand2")
                d_header.pack(fill="x", pady=(6, 0))

                self.domain_expanded[domain_key] = tk.BooleanVar(value=True)
                toggle_lbl = tk.Label(d_header, text="▼", font=("Segoe UI", 10),
                                      bg=config.COLORS["bg_card"], fg=config.COLORS["purple"])
                toggle_lbl.pack(side="left", padx=(0, 8))

                tk.Label(d_header, text=f"{icon}  {label}",
                         font=("Segoe UI", 12, "bold"),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_main"]
                         ).pack(side="left")
                tk.Label(d_header, text=f"({len(items)})",
                         font=("Segoe UI", 9),
                         bg=config.COLORS["bg_card"], fg=config.COLORS["text_muted"]
                         ).pack(side="left", padx=6)

                # Domain content container
                d_content = tk.Frame(dc, bg=config.COLORS["bg_card"])
                d_content.pack(fill="x", pady=(4, 8))

                for item in items:
                    ir = tk.Frame(d_content, bg=config.COLORS["bg_input"],
                                  highlightbackground=config.COLORS["border"], highlightthickness=1)
                    ir.pack(fill="x", pady=2)
                    tk.Label(ir, text=f"• {item.get('title', '')}",
                             font=("Segoe UI", 10, "bold"),
                             bg=config.COLORS["bg_input"], fg=config.COLORS["text_main"],
                             wraplength=1000, anchor="w", justify="left"
                             ).pack(anchor="w", padx=12, pady=(8, 2))
                    hyp = item.get("hypothesis", "")
                    if hyp:
                        tk.Label(ir, text=hyp, font=("Segoe UI", 9),
                                 bg=config.COLORS["bg_input"], fg=config.COLORS["text_sub"],
                                 wraplength=1000, anchor="w", justify="left"
                                 ).pack(anchor="w", padx=12, pady=(0, 2))
                    confirmed = item.get("user_confirmed", "")
                    if confirmed:
                        tk.Label(ir, text=f'💬  You said: "{confirmed}"',
                                 font=("Segoe UI", 9, "italic"),
                                 bg=config.COLORS["bg_input"], fg=config.COLORS["purple"],
                                 wraplength=1000, anchor="w", justify="left"
                                 ).pack(anchor="w", padx=12, pady=(0, 6))

                def make_toggle(dk, lbl, cont):
                    def _toggle():
                        if self.domain_expanded[dk].get():
                            cont.pack_forget()
                            lbl.config(text="▶")
                            self.domain_expanded[dk].set(False)
                        else:
                            cont.pack(fill="x", pady=(4, 8), after=lbl.master)
                            lbl.config(text="▼")
                            self.domain_expanded[dk].set(True)
                    return _toggle

                d_header.bind("<Button-1>",
                              lambda e, dk=domain_key, tl=toggle_lbl, dc2=d_content:
                              make_toggle(dk, tl, dc2)())

        # Good loops & Bad loops side by side
        gl = manual.get("good_loops", [])
        bl = manual.get("bad_loops", [])
        if gl or bl:
            loops_f = tk.Frame(inner, bg=config.COLORS["bg_main"])
            loops_f.pack(fill="x", padx=28, pady=(0, 14))

            if gl:
                gc = Card(loops_f, title="🟢  Good Loops — Reinforce These", icon="", pad=14)
                gc.pack(side="left", fill="both", expand=True, padx=(0, 8))
                for loop in gl:
                    tk.Label(gc, text=f"🔄 {loop.get('description', '')}",
                             font=("Segoe UI", 10), bg=config.COLORS["bg_card"],
                             fg=config.COLORS["text_main"], wraplength=500,
                             anchor="w", justify="left").pack(anchor="w", pady=2)
                    reinforce = loop.get("reinforce", "")
                    if reinforce:
                        tk.Label(gc, text=f"💪 {reinforce}", font=("Segoe UI", 9),
                                 bg=config.COLORS["bg_card"], fg=config.COLORS["green"],
                                 wraplength=500, anchor="w", justify="left").pack(
                            anchor="w", pady=(0, 8))

            if bl:
                bc = Card(loops_f, title="🔴  Bad Loops — Break These", icon="", pad=14)
                bc.pack(side="right", fill="both", expand=True, padx=(8, 0))
                for loop in bl:
                    tk.Label(bc, text=f"⚠️ {loop.get('description', '')}",
                             font=("Segoe UI", 10), bg=config.COLORS["bg_card"],
                             fg=config.COLORS["text_main"], wraplength=500,
                             anchor="w", justify="left").pack(anchor="w", pady=2)
                    break_it = loop.get("break_it", "")
                    if break_it:
                        tk.Label(bc, text=f"🔧 {break_it}", font=("Segoe UI", 9),
                                 bg=config.COLORS["bg_card"], fg=config.COLORS["red"],
                                 wraplength=500, anchor="w", justify="left").pack(
                            anchor="w", pady=(0, 8))

        # Top intervention
        top_int = manual.get("top_intervention", "")
        if top_int:
            tic = tk.Frame(inner, bg=config.COLORS["purple_dark"],
                           highlightbackground=config.COLORS["purple"], highlightthickness=2)
            tic.pack(fill="x", padx=28, pady=(0, 20))
            tk.Label(tic, text="🎯  Your #1 Priority Right Now",
                     font=("Segoe UI", 10, "bold"),
                     bg=config.COLORS["purple_dark"], fg="#FFF"
                     ).pack(anchor="w", padx=20, pady=(14, 2))
            tk.Label(tic, text=top_int, font=("Segoe UI", 12),
                     bg=config.COLORS["purple_dark"], fg="#FFF",
                     wraplength=1200, justify="left").pack(anchor="w", padx=20, pady=(0, 14))

    def _run_manual_synthesis(self):
        """Trigger AI synthesis of confirmed insights into Operating Manual."""
        if self.ai_loading:
            return
        if not self.api_key:
            self._prompt_api_key()
            return
        if not self.api_key:
            return

        confirmed = self.db.get_insights("confirmed")
        if len(confirmed) < 2:
            messagebox.showinfo("Not Enough Data",
                                "Need at least 2 confirmed insights to synthesize a manual.\n"
                                f"You have {len(confirmed)}. Keep answering questions in Discover!")
            return

        self.ai_loading = True
        self.manual_status.config(text="⏳  Synthesizing your patterns...")

        # Build the user message with all confirmed insights
        insights_for_ai = []
        for ins in confirmed:
            insights_for_ai.append({
                "id": ins["id"],
                "title": ins.get("title", ""),
                "hypothesis": ins.get("hypothesis", ""),
                "evidence": ins.get("evidence", []),
                "category": ins.get("category", "general"),
                "user_confirmed": ins.get("user_answer", ""),
            })
        user_msg = json.dumps(insights_for_ai, ensure_ascii=False, indent=2)

        def _work():
            result = AIClient.ask("manual_synthesize", user_msg, self.api_key)
            self.win.after(0, lambda: self._show_manual_result(result))

        threading.Thread(target=_work, daemon=True).start()

    def _show_manual_result(self, result):
        """Handle AI synthesis response."""
        self.ai_loading = False
        self.manual_status.config(text="")

        if "error" in result:
            messagebox.showerror("AI Error", result["error"])
            return

        self.db.set_manual(result)
        self._show_manual()
        messagebox.showinfo("Manual Ready",
                            "Your Operating Manual has been synthesized!\n\n"
                            "It will update as you confirm more patterns about yourself.")

    # ═══ Run ═══
    def run(self):
        self.win.mainloop()


if __name__ == "__main__":
    App().run()
