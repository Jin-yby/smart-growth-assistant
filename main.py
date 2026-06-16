"""
🌱 Student Growth Assistant — AI-Powered Self-Management Tool
=============================================================
DeepSeek AI · Task Management · Calendar · Self-Awareness · Vision

Run: python main.py
Deps: pip install ttkbootstrap requests
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime, timedelta
import json, os, re, calendar, random, threading, requests

# ============================================================
#  Config
# ============================================================
APP_TITLE = "🌱 Growth Assistant"
WINDOW_WIDTH, WINDOW_HEIGHT = 2400, 1600
MIN_WIDTH, MIN_HEIGHT = 2000, 1400
DATA_FILE = "growth_data.json"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SIDEBAR_W = 380

WEEKDAYS_CN = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

DARK_COLORS = {
    # 3-layer depth: black base → blue cards → black content + white text
    "bg_main":"#000000",      # L0: pure black — deepest
    "bg_side":"#040810",      #    sidebar — near black
    "bg_card":"#0F1F3A",      # L1: DEEP BLUE card — data block divider
    "bg_input":"#02050C",     # L2: near-black content area inside blue card
    "bg_hover":"#132840",     #    hover on blue
    "bg_accent":"#16102E",    #    purple-tinted accent
    "purple":"#A186F1","purple_dark":"#7C5EE0","green":"#34D399",
    "orange":"#FBBF24","red":"#F87171","blue":"#60A5FA","teal":"#2DD4BF",
    "text_main":"#E4E8F4","text_sub":"#9098B0","text_muted":"#5E667E",
    "border":"#1D3050","divider":"#132038",  # blue-tinted edges
}
LIGHT_COLORS = {
    # Clean palette — soft purple accent
    "bg_main":"#FFFFFF","bg_side":"#FFFFFF","bg_card":"#FFFFFF",
    "bg_input":"#F9FAFB","bg_hover":"#F6F8FA","bg_accent":"#F5F0FF",
    "purple":"#A186F1","purple_dark":"#7C5EE0","green":"#10B981",
    "orange":"#F59E0B","red":"#EF4444","blue":"#3B82F6","teal":"#14B8A6",
    "text_main":"#1A1A1A","text_sub":"#6B7280","text_muted":"#9CA3AF",
    "border":"#EBEBEB","divider":"#F5F5F5",
}
COLORS = LIGHT_COLORS.copy()

PROMPTS = {
    "plan": """You are a study planner. Today is {today}. The user describes a goal. Please:

1. Identify task type (exam prep / habit / reading / project)
2. Rate importance (1-5) and urgency (1-5), calculate priority (0-100)
3. Extract deadline and estimate total hours
4. List all subjects/topics involved and rate difficulty for each (1=easy, 5=hard).
   Allocate time proportionally: difficulty-5 topics get 5× the time of difficulty-1.
5. ⚠️ CRITICAL: Cover EVERY DAY from today ({today}) to the deadline (inclusive).
   Divide the total period into three phases:
   - Foundation (first 40% of days): one topic at a time, basics
   - Deepen (middle 30%): focus on hard topics, drills
   - Sprint (last 30%): mock exams, gap filling
6. Each day has TWO time blocks:
   - Focus Block (主攻, 2-3h, morning): ONE most-important subject — rotate subjects across days
   - Quick Block (碎片, 15-30min × 2, scattered time): memorization / mini-drills
7. Subject rotation rules:
   - Max 2 subjects per day
   - Each subject gets 2-3 consecutive days then rotates
   - Harder subjects get more days
   - Do NOT cover ALL subjects every day!
8. Set a weekly theme summarizing the focus
9. Return ONLY valid JSON (no extra text):
{{
  "type": "type",
  "title": "plan title",
  "deadline": "YYYY-MM-DD",
  "hours": total_estimated_hours,
  "importance": 1-5,
  "urgency": 1-5,
  "priority": 0-100,
  "weekly_theme": "this week's theme",
  "plan": [
    {{
      "date": "YYYY-MM-DD",
      "main_focus": {{"title": "Subject: specific task", "hours": number, "note": "focus tip"}},
      "quick_tasks": [{{"title": "Subject: quick task", "hours": decimal, "note": "tip"}}]
    }}
  ],
  "advice": "one-line execution tip"
}}""",

    "replan": """You are a study planner. The user has these pending tasks. Today is {today}. Please:

1. Group tasks by subject, find the furthest deadline
2. Calculate days from today to furthest deadline, divide into 3 phases:
   - Foundation (40%): basics one subject at a time
   - Deepen (30%): hard topics, drills
   - Sprint (30%): review, mock exams
3. Schedule daily blocks (Focus + Quick), rotating subjects:
   - Max 2 subjects per day, harder subjects get more consecutive days
4. Set a weekly theme
5. Return ONLY valid JSON:
{{
  "weekly_theme": "weekly theme",
  "plan": [
    {{
      "date": "YYYY-MM-DD",
      "main_focus": {{"title": "Subject: task", "hours": number, "note": "tip"}},
      "quick_tasks": [{{"title": "Subject: quick task", "hours": decimal, "note": "tip"}}]
    }}
  ],
  "advice": "execution tip"
}}

User's tasks:
{tasks_list}""",

    "diary": """You are a psychological analyst. Analyze the diary entry and return JSON:
{
  "mood": {"primary": "emotion", "score": 1-10},
  "sleep": {"hours": number, "quality": "good/ok/bad"},
  "highlights": ["positive events"],
  "lowlights": ["negative events"],
  "social": "social summary",
  "suggestions": ["3 personalized tips"],
  "reply": "warm, empathetic 2-3 sentence reply"
}""",

    "vision": """You are a life coach. Analyze the user's vision and return JSON:
{
  "core_themes": ["theme1", "theme2", "theme3"],
  "career_path": "career direction analysis",
  "habit_gaps": [{"goal": "desired habit", "status": "current state"}],
  "short_term": ["3 actionable steps this week"],
  "mid_term": ["semester/year milestones"],
  "inspiration": "one motivational quote"
}""",
}


# ============================================================
#  AI Client
# ============================================================
class AIClient:
    """DeepSeek API wrapper."""

    @staticmethod
    def get_api_key():
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    key = data.get("api_key", "")
                    if key:
                        return key
            except Exception:
                pass
        return None

    @staticmethod
    def ask(prompt_type, user_text, api_key, system_prompt=None):
        if not api_key:
            return {"error": "Please set your DeepSeek API Key first"}

        sp = system_prompt or PROMPTS.get(prompt_type, PROMPTS["plan"])

        try:
            resp = requests.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": sp},
                        {"role": "user", "content": user_text},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000,
                },
                timeout=30,
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```\w*\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            return json.loads(content)
        except requests.exceptions.Timeout:
            return {"error": "Request timeout — check network"}
        except requests.exceptions.ConnectionError:
            return {"error": "Cannot connect to DeepSeek — check network"}
        except json.JSONDecodeError:
            return {"error": f"AI response format error: {content[:200]}..."}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}


# ============================================================
#  Data Manager
# ============================================================
class DataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename
        self.data = self._load()

    def _load(self):
        defaults = {"importance":3, "urgency":3, "priority":50, "task_type":"normal", "weekly_theme":"", "actual_minutes":0}
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for t in data.get("tasks",[]):
                    for k,v in defaults.items():
                        if k not in t: t[k] = v
                return data
            except:
                pass
        return {"tasks":[], "next_id":1, "diary":[], "visions":[], "api_key":""}

    def save(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def set_api_key(self, key):
        self.data["api_key"] = key
        self.save()

    def get_api_key(self):
        return self.data.get("api_key", "")

    # Tasks
    def get_tasks(self, date_str=None):
        tasks = self.data.get("tasks",[])
        return [t for t in tasks if t.get("plan_date")==date_str] if date_str else tasks

    def add_task(self, title, subject, deadline, plan_date=None, hours=0,
                 importance=3, urgency=3, priority=50, task_type="normal", weekly_theme="", actual_minutes=0):
        t = {"id":self.data["next_id"], "title":title, "subject":subject or "Other",
             "deadline":deadline or "", "plan_date":plan_date or datetime.now().strftime("%Y-%m-%d"),
             "estimated_hours":hours, "status":"pending",
             "created":datetime.now().strftime("%Y-%m-%d %H:%M"),
             "importance":importance, "urgency":urgency, "priority":priority,
             "task_type":task_type, "weekly_theme":weekly_theme,
             "actual_minutes":actual_minutes}
        self.data["tasks"].append(t)
        self.data["next_id"]+=1
        self.save()
        return t

    def add_time(self, tid, minutes):
        """Accumulate actual focused minutes on a task."""
        for t in self.data["tasks"]:
            if t["id"]==tid:
                t["actual_minutes"] = t.get("actual_minutes",0) + minutes
                self.save(); return True
        return False

    def add_tasks_batch(self, items, meta=None):
        for it in items:
            self.add_task(
                it.get("title",""), it.get("subject",""), it.get("deadline",""),
                it.get("plan_date",""), it.get("hours",0),
                importance=it.get("importance", meta.get("importance",3) if meta else 3),
                urgency=it.get("urgency", meta.get("urgency",3) if meta else 3),
                priority=it.get("priority", meta.get("priority",50) if meta else 50),
                task_type=it.get("task_type","normal"),
                weekly_theme=it.get("weekly_theme", meta.get("weekly_theme","") if meta else "")
            )

    def update_task(self, tid, **kw):
        for t in self.data["tasks"]:
            if t["id"]==tid: t.update(kw); self.save(); return True
        return False

    def delete_task(self, tid):
        self.data["tasks"]=[t for t in self.data["tasks"] if t["id"]!=tid]; self.save()

    def get_stats(self):
        tasks=self.data["tasks"]
        total=len(tasks)
        pending=sum(1 for t in tasks if t["status"]=="pending")
        completed=sum(1 for t in tasks if t["status"]=="completed")
        today=datetime.now().strftime("%Y-%m-%d")
        td=self.get_tasks(today)
        td_done=sum(1 for t in td if t["status"]=="completed")
        return {"total":total,"pending":pending,"completed":completed,
                "rate":int(completed/total*100) if total else 0,
                "today_total":len(td),"today_done":td_done}

    def get_month_tasks(self, y, m):
        """Count tasks by deadline date (for calendar milestone markers)."""
        r={}
        for t in self.data["tasks"]:
            dl=t.get("deadline","")
            if dl and dl.startswith(f"{y}-{m:02d}"):
                d=int(dl.split("-")[2]); r[d]=r.get(d,0)+1
        return r

    def get_deadline_tasks(self, date_str):
        """Get tasks whose deadline matches this date (big milestones)."""
        return [t for t in self.data.get("tasks",[]) if t.get("deadline","")==date_str]

    def get_weekly_theme(self):
        tasks = self.data.get("tasks",[])
        for t in sorted(tasks, key=lambda x: x.get("created",""), reverse=True):
            wt = t.get("weekly_theme","")
            if wt: return wt
        return ""

    def get_pending_tasks(self):
        return [t for t in self.data.get("tasks",[]) if t["status"] == "pending"]

    # Diary
    def add_diary(self, text, analysis):
        e={"date":datetime.now().strftime("%Y-%m-%d"),"raw":text,"analysis":analysis}
        self.data["diary"].append(e); self.save()

    def get_diary(self, limit=30):
        return sorted(self.data.get("diary",[]), key=lambda x:x.get("date",""), reverse=True)[:limit]

    # Vision
    def add_vision(self, text, analysis):
        v={"date":datetime.now().strftime("%Y-%m-%d %H:%M"),"raw":text,"analysis":analysis}
        self.data["visions"].append(v); self.save()

    def get_visions(self):
        return sorted(self.data.get("visions",[]), key=lambda x:x.get("date",""), reverse=True)


# ============================================================
#  UI Components
# ============================================================
class Card(tk.Frame):
    """Floating card — lifted surface with visible edge."""
    def __init__(self, parent, title="", icon="", pad=20, **kw):
        super().__init__(parent, bg=COLORS["bg_card"], padx=pad, pady=pad, **kw)
        # 2px bright border for floating effect
        self.configure(highlightbackground=COLORS["border"],highlightthickness=2)
        if title:
            h=tk.Frame(self, bg=COLORS["bg_card"])
            h.pack(fill="x", pady=(0,pad-8))
            tk.Label(h, text=f"{icon}  {title}", font=("Segoe UI",13,"bold"),
                     bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(anchor="w")
            tk.Frame(h, bg=COLORS["divider"],height=1).pack(fill="x",pady=(8,0))


class StatCard(tk.Frame):
    """Compact stat card — black block on blue card."""
    def __init__(self, parent, icon, label, color, **kw):
        super().__init__(parent, bg=COLORS["bg_input"], padx=16, pady=12, **kw)
        self.configure(highlightbackground=COLORS["border"],highlightthickness=1)
        tk.Label(self,text=icon,font=("Segoe UI Emoji",16),bg=COLORS["bg_input"],fg=color).pack(anchor="w")
        self.v=tk.Label(self,text="0",font=("Segoe UI",22,"bold"),bg=COLORS["bg_input"],fg=COLORS["text_main"])
        self.v.pack(anchor="w",pady=(2,0))
        tk.Label(self,text=label,font=("Segoe UI",8),bg=COLORS["bg_input"],fg=COLORS["text_sub"]).pack(anchor="w")
    def set(self,val): self.v.config(text=str(val))


class TaskRow(tk.Frame):
    """Task row — black block on blue card, white text."""
    def __init__(self,parent,task,on_done,on_del):
        super().__init__(parent,bg=COLORS["bg_input"],padx=12,pady=8)
        self.configure(highlightbackground=COLORS["border"],highlightthickness=1)
        done=task["status"]=="completed"
        today=datetime.now().strftime("%Y-%m-%d")
        dl=task.get("deadline","")
        is_overdue = not done and dl and dl < today
        tt=task.get("task_type","normal")
        # Status dot
        if done: dc=COLORS["green"]
        elif is_overdue: dc=COLORS["red"]
        elif tt=="main_focus": dc=COLORS["blue"]
        else: dc=COLORS["orange"]
        c=tk.Canvas(self,width=8,height=8,bg=COLORS["bg_input"],highlightthickness=0)
        c.create_oval(1,1,7,7,fill=dc,outline=""); c.pack(side="left",padx=(0,8))
        # Title
        ts=("Segoe UI",11,"overstrike") if done else ("Segoe UI",11,"bold")
        tf=COLORS["text_sub"] if done else COLORS["text_main"]
        tk.Label(self,text=task["title"],font=ts,bg=COLORS["bg_input"],fg=tf,anchor="w").pack(side="left",fill="x",expand=True)
        # Importance stars
        imp=task.get("importance",3)
        stars="".join(["★" if i<imp else "☆" for i in range(5)])
        sc="#D4A853" if not done else COLORS["text_muted"]
        tk.Label(self,text=stars,font=("Segoe UI",7),bg=COLORS["bg_input"],fg=sc).pack(side="left",padx=(4,2))
        # Priority badge
        pr=task.get("priority",0)
        if pr>=80: pc=COLORS["red"]
        elif pr>=50: pc=COLORS["orange"]
        else: pc=COLORS["green"]
        tk.Label(self,text=f" {pr} ",font=("Segoe UI",8,"bold"),bg=pc,fg="#FFF",padx=5,pady=1).pack(side="left",padx=3)
        # Subject tag
        tk.Label(self,text=f" {task['subject']} ",font=("Segoe UI",8),bg=COLORS["purple_dark"],fg="#FFF",padx=6,pady=1).pack(side="left",padx=6)
        # Date
        pd=task.get("plan_date","")
        if pd:
            dl_label = f"⚠️ {pd}" if is_overdue else f"📅 {pd}"
            dl_color = COLORS["red"] if is_overdue else COLORS["text_sub"]
            tk.Label(self,text=dl_label,font=("Segoe UI",8),bg=COLORS["bg_input"],fg=dl_color).pack(side="left",padx=4)
        # Action buttons
        if not done:
            b=tk.Label(self,text=" ✓ ",font=("Segoe UI",9,"bold"),bg=COLORS["green"],fg="#FFF",padx=8,pady=3,cursor="hand2"); b.pack(side="right",padx=1)
            b.bind("<Button-1>",lambda e:on_done(task["id"]))
        b2=tk.Label(self,text=" ✕ ",font=("Segoe UI",9),bg=COLORS["red"],fg="#FFF",padx=8,pady=3,cursor="hand2"); b2.pack(side="right",padx=1)
        b2.bind("<Button-1>",lambda e:on_del(task["id"]))


# ============================================================
#  Main App
# ============================================================
class App:
    def __init__(self):
        self.db=DataManager()
        self.is_dark=False
        self.api_key=self.db.get_api_key()

        self.win=ttk.Window(themename="flatly")
        self.win.title(APP_TITLE)
        self.win.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.win.minsize(MIN_WIDTH,MIN_HEIGHT)
        self.win.configure(bg=COLORS["bg_main"])

        self.current_page=None
        self.ai_loading=False
        self.timers = {}  # {task_id: {"start": timestamp, "label": tk.Label}}

        self._build_layout()
        self._nav_to_page("dashboard")

        if not self.api_key:
            self.win.after(500, self._prompt_api_key)

    # ═══ Layout ═══
    def _build_layout(self):
        self.sidebar=tk.Frame(self.win,bg=COLORS["bg_side"],width=SIDEBAR_W)
        self.sidebar.pack(side="left",fill="y"); self.sidebar.pack_propagate(False)
        self._build_sidebar_content()
        self.main_area=tk.Frame(self.win,bg=COLORS["bg_main"])
        self.main_area.pack(side="right",fill="both",expand=True)

    def _build_sidebar_content(self):
        # Logo
        lf=tk.Frame(self.sidebar,bg=COLORS["bg_side"]); lf.pack(fill="x",padx=22,pady=(24,20))
        tk.Label(lf,text="🌱",font=("Segoe UI Emoji",30),bg=COLORS["bg_side"]).pack(anchor="w")
        tk.Label(lf,text="Growth",font=("Segoe UI",15,"bold"),bg=COLORS["bg_side"],fg=COLORS["text_main"]).pack(anchor="w",pady=(4,0))
        tk.Label(lf,text="Student Planner",font=("Segoe UI",8),bg=COLORS["bg_side"],fg=COLORS["text_muted"]).pack(anchor="w")
        tk.Frame(self.sidebar,bg=COLORS["divider"],height=1).pack(fill="x",padx=18,pady=(0,14))

        # Navigation
        self.nav_btns={}
        for key,text in [
            ("dashboard","📊  Dashboard"),
            ("calendar","📅  Calendar"),
            ("tasks","✅  Tasks"),
            ("ai","🤖  AI Planner"),
            ("vision","🌟  Vision"),
        ]:
            b=tk.Label(self.sidebar,text=text,font=("Segoe UI",12),bg=COLORS["bg_side"],
                       fg=COLORS["text_sub"],anchor="w",padx=24,pady=11,cursor="hand2")
            b.pack(fill="x")
            b.bind("<Button-1>",lambda e,k=key:self._nav_to_page(k))
            b.bind("<Enter>",lambda e,b=b:b.configure(bg=COLORS["bg_hover"]))
            b.bind("<Leave>",lambda e,b=b,k=key:
                b.configure(bg=COLORS["bg_hover"] if self.current_page==k else COLORS["bg_side"]))
            self.nav_btns[key]=b

        # Theme toggle
        sp=tk.Frame(self.sidebar,bg=COLORS["bg_side"]); sp.pack(fill="both",expand=True)
        tk.Frame(self.sidebar,bg=COLORS["border"],height=1).pack(fill="x",padx=16,pady=(0,12))
        self.theme_btn=tk.Frame(self.sidebar,bg=COLORS["bg_side"],padx=16,pady=10,cursor="hand2")
        self.theme_btn.pack(fill="x",pady=(0,16))
        self.theme_icon=tk.Label(self.theme_btn,text="🌙",font=("Segoe UI Emoji",14),bg=COLORS["bg_side"],fg=COLORS["text_sub"])
        self.theme_icon.pack(side="left",padx=(0,12))
        self.theme_text=tk.Label(self.theme_btn,text="Dark Mode",font=("Segoe UI",11),bg=COLORS["bg_side"],fg=COLORS["text_sub"],anchor="w")
        self.theme_text.pack(side="left")
        for w in[self.theme_btn,self.theme_icon,self.theme_text]:w.bind("<Button-1>",lambda e:self._toggle_theme())

        # API Key
        self.api_btn=tk.Label(self.sidebar,text="⚙️  API Settings",font=("Segoe UI",10),bg=COLORS["bg_side"],
                              fg=COLORS["text_muted"],anchor="w",padx=24,pady=6,cursor="hand2")
        self.api_btn.pack(fill="x",pady=(0,8))
        self.api_btn.bind("<Button-1>",lambda e:self._prompt_api_key())

    # ═══ Nav & Theme ═══
    def _nav_to_page(self,key):
        self.current_page=key
        for k,b in self.nav_btns.items():
            a=(k==key); b.configure(bg=COLORS["bg_hover"] if a else COLORS["bg_side"],fg=COLORS["purple"] if a else COLORS["text_sub"])
        self._clear_main()
        {"dashboard":self._show_dashboard,"calendar":self._show_calendar,"tasks":self._show_tasks,
         "ai":self._show_ai,"vision":self._show_vision}[key]()

    def _clear_main(self):
        for w in self.main_area.winfo_children():w.destroy()

    def _toggle_theme(self):
        global COLORS
        self.is_dark=not self.is_dark
        try: self.win.style.theme_use("darkly" if self.is_dark else "flatly")
        except: pass
        COLORS.update(DARK_COLORS if self.is_dark else LIGHT_COLORS)
        self.win.configure(bg=COLORS["bg_main"]); self.main_area.configure(bg=COLORS["bg_main"])
        for w in self.sidebar.winfo_children():w.destroy()
        self.nav_btns={}; self._build_sidebar_content()
        self.theme_icon.config(text="☀️" if self.is_dark else "🌙")
        self.theme_text.config(text="Light Mode" if self.is_dark else "Dark Mode")
        self._nav_to_page(self.current_page)

    def _prompt_api_key(self):
        key=simpledialog.askstring("DeepSeek API Key",
            "Enter your DeepSeek API Key:\n\n"
            "1. Sign up at platform.deepseek.com\n"
            "2. Create a key in API Keys page\n"
            "3. New users get free credits\n\n"
            "(Stored locally, never uploaded)",
            parent=self.win)
        if key:
            self.api_key=key.strip()
            self.db.set_api_key(self.api_key)
            messagebox.showinfo("Success","API Key saved!\nYou can now use the AI Planner.")

    # ═══ Scroll ═══
    def _scroll(self, parent):
        cv=tk.Canvas(parent,bg=COLORS["bg_main"],highlightthickness=0)
        sb=ttk.Scrollbar(parent,orient="vertical",command=cv.yview)
        inner=tk.Frame(cv,bg=COLORS["bg_main"])
        inner.bind("<Configure>",lambda e:cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0,0),window=inner,anchor="nw",tags="in")
        cv.configure(yscrollcommand=sb.set)
        cv.bind("<Configure>",lambda e:cv.itemconfig("in",width=e.width))
        def _wh(e):cv.yview_scroll(int(-1*(e.delta/120)),"units")
        inner.bind("<Enter>",lambda e:cv.bind_all("<MouseWheel>",_wh))
        inner.bind("<Leave>",lambda e:cv.unbind_all("<MouseWheel>"))
        cv.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        return cv,sb,inner

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
        if not t or not t.get("running"): return
        elapsed = int(_time.time() - t["start"])
        mins, secs = divmod(elapsed, 60)
        t["label"].config(text=f"⏱ {mins:02d}:{secs:02d}")
        self._timer_after = self.win.after(1000, lambda: self._tick_timer(tid))

    def _stop_timer(self, tid):
        """Stop timer, save elapsed minutes, update actual label."""
        import time as _time
        t = self.timers.pop(tid, None)
        if not t: return
        t["running"] = False
        elapsed = int(_time.time() - t["start"])
        mins = max(1, round(elapsed / 60, 1))
        self.db.add_time(tid, mins)
        t["label"].config(text="▶")
        if t.get("act_label"):
            total = 0
            for tk in self.db.data["tasks"]:
                if tk["id"] == tid: total = tk.get("actual_minutes", 0); break
            t["act_label"].config(text=f"✓ {total:.0f}m", fg=COLORS["green"])

    # ═══ 1. Dashboard ═══
    def _show_dashboard(self):
        self._clear_main()
        stats=self.db.get_stats()
        today=datetime.now().strftime("%Y-%m-%d")
        _,__,inner=self._scroll(self.main_area)

        h=datetime.now().hour
        g="Good morning ☀️" if h<12 else ("Good afternoon 🌤️" if h<18 else "Good evening 🌙")
        tk.Label(inner,text=g,font=("Segoe UI",24,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(fill="x",padx=30,pady=(22,2))
        tk.Label(inner,text=f"{today}  {WEEKDAYS_CN[datetime.now().weekday()]}",font=("Segoe UI",11),bg=COLORS["bg_main"],fg=COLORS["text_sub"]).pack(fill="x",padx=30,pady=(0,20))

        # Weekly theme
        weekly_theme=self.db.get_weekly_theme()
        if weekly_theme:
            wtf=tk.Frame(inner,bg=COLORS["bg_accent"]); wtf.pack(fill="x",padx=30,pady=(0,12))
            tk.Label(wtf,text=f"🎯  This week: {weekly_theme}",font=("Segoe UI",12,"bold"),bg=COLORS["bg_accent"],fg=COLORS["purple"]).pack(padx=16,pady=10,anchor="w")

        # Stat cards
        cards=tk.Frame(inner,bg=COLORS["bg_main"]); cards.pack(fill="x",padx=30,pady=4)
        for i in range(5):cards.columnconfigure(i,weight=1,uniform="c")
        overd=sum(1 for t in self.db.get_tasks() if t["status"]=="pending" and t.get("deadline","") and t["deadline"]<today)
        for i,(ic,lb,val,cl) in enumerate([
            ("📋","Total",stats["total"],COLORS["purple"]),
            ("⏳","Pending",stats["pending"],COLORS["orange"]),
            ("✅","Completed",stats["completed"],COLORS["green"]),
            ("📅","Today",f"{stats['today_done']}/{stats['today_total']}",COLORS["blue"]),
            ("🚨","Overdue",overd,COLORS["red"]),
        ]):
            c=StatCard(cards,ic,lb,cl); c.grid(row=0,column=i,sticky="nsew",padx=4); c.set(val)

        # Today's tasks — Focus + Quick with Pomodoro timer
        td_tasks=self.db.get_tasks(today)
        main_tasks=[t for t in td_tasks if t.get("task_type")=="main_focus"]
        quick_tasks=[t for t in td_tasks if t.get("task_type")=="quick_task"]
        other_tasks=[t for t in td_tasks if t.get("task_type") not in ("main_focus","quick_task")]

        if td_tasks:
            if main_tasks or other_tasks:
                c1=Card(inner,title="Focus",icon="🔵"); c1.pack(fill="x",padx=30,pady=(18,6))
                for t in main_tasks+other_tasks:
                    tid=t["id"]; dn=t["status"]=="completed"
                    dl2=t.get("deadline",""); is_od=not dn and dl2 and dl2<today
                    row_bg=COLORS["bg_input"]
                    r=tk.Frame(c1,bg=row_bg,padx=8,pady=6,highlightbackground=COLORS["border"],highlightthickness=1); r.pack(fill="x",pady=2)
                    if dn: dc2=COLORS["green"]
                    elif is_od: dc2=COLORS["red"]
                    else: dc2=COLORS["blue"]
                    cc=tk.Canvas(r,width=7,height=7,bg=row_bg,highlightthickness=0)
                    cc.create_oval(1,1,6,6,fill=dc2,outline=""); cc.pack(side="left",padx=(0,8))
                    ts=("Segoe UI",10,"overstrike") if dn else ("Segoe UI",10,"bold")
                    tf=COLORS["text_sub"] if dn else COLORS["text_main"]
                    tk.Label(r,text=t["title"],font=ts,bg=row_bg,fg=tf,anchor="w").pack(side="left",fill="x",expand=True)
                    # Target
                    hh=t.get("estimated_hours",0)
                    if hh:tk.Label(r,text=f"🎯 {hh}h",font=("Segoe UI",8),bg=row_bg,fg=COLORS["text_sub"]).pack(side="right",padx=4)
                    # Actual
                    am=t.get("actual_minutes",0)
                    act_label=tk.Label(r,text=f"✓ {am:.0f}m" if am else "—",font=("Segoe UI",8),bg=row_bg,fg=COLORS["green"] if am else COLORS["text_muted"])
                    act_label.pack(side="right",padx=4)
                    # Timer controls
                    timer_label=tk.Label(r,text="▶",font=("Segoe UI",10),bg=row_bg,fg=COLORS["blue"],cursor="hand2",padx=4)
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
                        timer_label.config(text="✓", fg=COLORS["green"])
            if quick_tasks:
                c2=Card(inner,title="Quick Tasks",icon="🟢"); c2.pack(fill="x",padx=30,pady=(8,6))
                for t in quick_tasks:
                    tid=t["id"]; dn=t["status"]=="completed"
                    row_bg=COLORS["bg_input"]
                    r=tk.Frame(c2,bg=row_bg,padx=8,pady=5,highlightbackground=COLORS["border"],highlightthickness=1); r.pack(fill="x",pady=2)
                    dc3=COLORS["green"] if dn else COLORS["teal"]
                    cc=tk.Canvas(r,width=7,height=7,bg=row_bg,highlightthickness=0)
                    cc.create_oval(1,1,6,6,fill=dc3,outline=""); cc.pack(side="left",padx=(0,8))
                    ts=("Segoe UI",10,"overstrike") if dn else ("Segoe UI",10)
                    tf=COLORS["text_sub"] if dn else COLORS["text_main"]
                    tk.Label(r,text=t["title"],font=ts,bg=row_bg,fg=tf,anchor="w").pack(side="left",fill="x",expand=True)
                    hh=t.get("estimated_hours",0)
                    if hh:tk.Label(r,text=f"🎯 {hh}h",font=("Segoe UI",8),bg=row_bg,fg=COLORS["text_sub"]).pack(side="right",padx=4)
                    am=t.get("actual_minutes",0)
                    act_label2=tk.Label(r,text=f"✓ {am:.0f}m" if am else "—",font=("Segoe UI",8),bg=row_bg,fg=COLORS["green"] if am else COLORS["text_muted"])
                    act_label2.pack(side="right",padx=4)
                    timer_label2=tk.Label(r,text="▶" if not dn else "✓",font=("Segoe UI",10),bg=row_bg,fg=COLORS["blue"] if not dn else COLORS["green"],cursor="hand2",padx=4)
                    timer_label2.pack(side="right")
                    if not dn:
                        def _qs(tid=tid, tl=timer_label2, al=act_label2):
                            if tid in self.timers and self.timers[tid].get("running"):
                                self._stop_timer(tid)
                            else:
                                self._start_timer(tid, tl, al)
                        timer_label2.bind("<Button-1>", lambda e, cb=_qs: cb())
        else:
            c1=Card(inner,title="Today",icon="📅"); c1.pack(fill="x",padx=30,pady=(18,10))
            tk.Label(c1,text="No tasks yet — go to AI Planner to create a plan ✨",font=("Segoe UI",11),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(pady=10)

        # Vision snapshot
        visions=self.db.get_visions()
        if visions:
            c2=Card(inner,title="Latest Vision",icon="🌟"); c2.pack(fill="x",padx=30,pady=(12,20))
            v=visions[0]
            a=v.get("analysis",{})
            themes=a.get("core_themes","") if isinstance(a,dict) else ""
            if themes:
                tk.Label(c2,text=" · ".join(themes),font=("Segoe UI",11),bg=COLORS["bg_card"],fg=COLORS["purple"],wraplength=1200).pack(anchor="w")
            tk.Label(c2,text=v.get("date",""),font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"]).pack(anchor="w",pady=(6,0))

    # ═══ 2. Calendar ═══
    def _show_calendar(self):
        self._clear_main()
        today=datetime.now(); self.cal_y=today.year; self.cal_m=today.month

        top=tk.Frame(self.main_area,bg=COLORS["bg_main"]); top.pack(fill="x",padx=24,pady=(16,8))
        tk.Label(top,text="📅  Calendar",font=("Segoe UI",20,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(side="left")
        nav=tk.Frame(top,bg=COLORS["bg_main"]); nav.pack(side="right")
        self.cal_title=tk.Label(nav,text="",font=("Segoe UI",14,"bold"),bg=COLORS["bg_main"],fg=COLORS["purple"])
        self.cal_title.pack(side="left",padx=16)
        for text,dy, dm in [("◀", -1,0), ("▶", 1,0), ("▲", 0,-1), ("▼", 0,1)]:
            b=tk.Label(nav,text=text,font=("Segoe UI",12),bg=COLORS["bg_main"],fg=COLORS["text_sub"],cursor="hand2",padx=4)
            b.pack(side="left")
            b.bind("<Button-1>",lambda e,dy=dy,dm=dm:self._cal_shift(dy,dm))
        body=tk.Frame(self.main_area,bg=COLORS["bg_main"]); body.pack(fill="both",expand=True,padx=24,pady=(0,12))
        week_f=Card(self.main_area,title="Week Overview",icon="📋"); week_f.pack(fill="x",padx=24,pady=(0,16))
        self._draw_cal(body,week_f)

    def _cal_shift(self,dy,dm):
        if dm:
            self.cal_m+=dm
            if self.cal_m>12:self.cal_m=1;self.cal_y+=1
            if self.cal_m<1:self.cal_m=12;self.cal_y-=1
        else:
            d=datetime(self.cal_y,self.cal_m,1)+timedelta(days=dy*30)
            self.cal_y,self.cal_m=d.year,d.month
        body=self.main_area.winfo_children()
        week_f=None
        for w in self.main_area.winfo_children():
            if isinstance(w,Card) and "Week" in str(w):week_f=w;break
        # Rebuild
        for w in self.main_area.winfo_children():
            if isinstance(w,tk.Frame) and w!=self.sidebar:
                for ch in w.winfo_children():
                    if isinstance(ch,tk.Frame) and ch.cget("bg")==COLORS["bg_main"]:
                        self._draw_cal(ch,week_f or w);return
        self._draw_cal(body,week_f or body)

    def _draw_cal(self,parent,week_f):
        for w in parent.winfo_children():w.destroy()
        self.cal_title.config(text=f"{self.cal_y}  {self.cal_m}")
        mt=self.db.get_month_tasks(self.cal_y,self.cal_m)
        today=datetime.now()

        # Weekday headers
        WDS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
        hdr=tk.Frame(parent,bg=COLORS["bg_main"]); hdr.pack(fill="x",pady=(12,4))
        for i,wd in enumerate(WDS):
            hdr.columnconfigure(i,weight=1,uniform="cal")
            tk.Label(hdr,text=wd,font=("Segoe UI",10,"bold"),bg=COLORS["bg_main"],
                     fg=COLORS["red"] if i==0 else COLORS["text_sub"]).grid(row=0,column=i,sticky="ew",ipady=4)

        # Calendar grid — each cell is a lifted card on black base
        weeks=calendar.Calendar(firstweekday=6).monthdayscalendar(self.cal_y,self.cal_m)
        for wk in weeks:
            row=tk.Frame(parent,bg=COLORS["bg_main"]); row.pack(fill="x",pady=3,padx=2)
            for i in range(7):row.columnconfigure(i,weight=1,uniform="cal")
            for di,day in enumerate(wk):
                if day==0:
                    # Empty cell — bare base layer
                    tk.Frame(row,bg=COLORS["bg_main"],padx=6,pady=8).grid(row=0,column=di,sticky="nsew"); continue
                ist=(day==today.day and self.cal_m==today.month and self.cal_y==today.year)
                # Today: accent highlight, other days: card layer
                if ist:
                    cb=COLORS["purple_dark"]; border_c="#4060A0"
                else:
                    cb=COLORS["bg_card"]; border_c=COLORS["border"]
                cell=tk.Frame(row,bg=cb,padx=8,pady=8,highlightbackground=border_c,highlightthickness=2)
                cell.grid(row=0,column=di,sticky="nsew",ipady=12,padx=2,pady=2)
                # Day number
                tk.Label(cell,text=str(day),font=("Segoe UI",16,"bold"),bg=cb,
                         fg="#FFF" if ist else COLORS["text_main"]).pack(anchor="ne")
                # Deadline markers — sit on cell bg
                cnt=mt.get(day,0)
                if cnt:
                    dl_f=tk.Frame(cell,bg=cb); dl_f.pack(anchor="sw",pady=(6,0),fill="x")
                    if cnt==1:
                        tk.Label(dl_f,text=f"📌",font=("Segoe UI",9),bg=cb,fg=COLORS["orange" if not ist else "#FFD"]).pack(anchor="w")
                    else:
                        tk.Label(dl_f,text=f"📌 ×{cnt}",font=("Segoe UI",9),bg=cb,
                                 fg=COLORS["red" if not ist else "#FFB"]).pack(anchor="w")
                cell.bind("<Button-1>",lambda e,d=day:self._day_detail(d))
                for ch in cell.winfo_children():ch.bind("<Button-1>",lambda e,d=day:self._day_detail(d))

        # Week overview
        for w in list(week_f.winfo_children()):w.destroy()
        wf_content=tk.Frame(week_f,bg=COLORS["bg_card"]); wf_content.pack(fill="x",padx=0,pady=(8,6))
        monday=today-timedelta(days=today.weekday())
        for i in range(7):wf_content.columnconfigure(i,weight=1,uniform="wk")
        for i in range(7):
            d=monday+timedelta(days=i); ds=d.strftime("%Y-%m-%d")
            dt=self.db.get_tasks(ds); ist=d.date()==today.date()
            cb_wf = COLORS["bg_input"] if ist else COLORS["bg_card"]
            cell=tk.Frame(wf_content,bg=cb_wf,padx=8,pady=8,
                          highlightbackground=COLORS["border"],highlightthickness=1)
            cell.grid(row=0,column=i,sticky="nsew",padx=2)
            dc_w=COLORS["purple"] if ist else COLORS["text_main"]
            tk.Label(cell,text=f"{WDS[i]}\n{d.day}",font=("Segoe UI",10,"bold"),bg=cb_wf,fg=dc_w).pack(pady=(0,6))
            if dt:
                dn=sum(1 for t in dt if t["status"]=="completed")
                tk.Label(cell,text=f"✅ {dn}/{len(dt)}",font=("Segoe UI",9),bg=cb_wf,
                         fg=COLORS["green"] if dn==len(dt) else COLORS["orange"]).pack()
            else:
                tk.Label(cell,text="—",font=("Segoe UI",9),bg=cb_wf,fg=COLORS["text_muted"]).pack()

    def _day_detail(self,day):
        ds=f"{self.cal_y}-{self.cal_m:02d}-{day:02d}"
        tasks=self.db.get_deadline_tasks(ds)  # show deadline tasks, not daily tasks
        w=tk.Toplevel(self.win); w.title(f"📅 {ds}"); w.geometry("620x520"); w.configure(bg=COLORS["bg_card"]); w.transient(self.win)
        try:wd=WEEKDAYS_CN[datetime.strptime(ds,"%Y-%m-%d").weekday()]
        except:wd=""
        tk.Label(w,text=f"📅  {ds}  {wd}",font=("Segoe UI",14,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(padx=20,pady=(20,14))
        if tasks:
            for t in tasks:
                r=tk.Frame(w,bg=COLORS["bg_card"]); r.pack(fill="x",padx=20,pady=3)
                dn=t["status"]=="completed"; dc2=COLORS["green"] if dn else COLORS["orange"]
                cc=tk.Canvas(r,width=8,height=8,bg=COLORS["bg_card"],highlightthickness=0)
                cc.create_oval(1,1,7,7,fill=dc2,outline=""); cc.pack(side="left",padx=(0,8))
                ts=("Segoe UI",11,"overstrike") if dn else ("Segoe UI",11)
                tf=COLORS["text_sub"] if dn else COLORS["text_main"]
                tk.Label(r,text=t["title"],font=ts,bg=COLORS["bg_card"],fg=tf,anchor="w").pack(side="left",fill="x",expand=True)
                def _tg(tid=t["id"]):
                    ns="pending" if t["status"]=="completed" else "completed"
                    self.db.update_task(tid,status=ns); w.destroy(); self._day_detail(day)
                bt="↩ Undo" if dn else "✓ Done"; bc=COLORS["orange"] if dn else COLORS["green"]
                b=tk.Label(r,text=bt,font=("Segoe UI",9),bg=bc,fg="#FFF",padx=10,pady=3,cursor="hand2")
                b.pack(side="right"); b.bind("<Button-1>",lambda e,cb=_tg:cb())
        else:
            tk.Label(w,text="📭  No tasks on this day",font=("Segoe UI",12),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(expand=True)

    # ═══ 3. Tasks ═══
    def _show_tasks(self):
        self._clear_main(); _,__,inner=self._scroll(self.main_area)
        tk.Label(inner,text="✅  Tasks",font=("Segoe UI",20,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(fill="x",padx=28,pady=(18,14))

        form=Card(inner,title="New Task",icon="➕"); form.pack(fill="x",padx=28,pady=(0,14))
        ff=tk.Frame(form,bg=COLORS["bg_card"]); ff.pack(fill="x")
        for i in range(4):ff.columnconfigure(i,weight=[2,1,1,0][i],uniform="f")
        tk.Label(ff,text="Task",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).grid(row=0,column=0,sticky="w")
        e_title=tk.Entry(ff,font=("Segoe UI",11),bg=COLORS["bg_input"],fg=COLORS["text_main"],insertbackground=COLORS["text_main"],relief="flat")
        e_title.grid(row=1,column=0,sticky="ew",padx=(0,6),ipady=2)
        tk.Label(ff,text="Subject",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).grid(row=0,column=1,sticky="w")
        e_subj=tk.Entry(ff,font=("Segoe UI",11),bg=COLORS["bg_input"],fg=COLORS["text_main"],insertbackground=COLORS["text_main"],relief="flat")
        e_subj.grid(row=1,column=1,sticky="ew",padx=3,ipady=2)
        tk.Label(ff,text="Deadline",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).grid(row=0,column=2,sticky="w")
        e_date=tk.Entry(ff,font=("Segoe UI",11),bg=COLORS["bg_input"],fg=COLORS["text_main"],insertbackground=COLORS["text_main"],relief="flat")
        e_date.insert(0,datetime.now().strftime("%Y-%m-%d")); e_date.grid(row=1,column=2,sticky="ew",padx=3,ipady=2)
        add_btn=tk.Label(ff,text="  Add  ",font=("Segoe UI",10,"bold"),bg=COLORS["purple"],fg="#FFF",padx=16,pady=7,cursor="hand2")
        add_btn.grid(row=1,column=3,padx=(6,0))

        lf=tk.Frame(inner,bg=COLORS["bg_main"]); lf.pack(fill="both",expand=True,padx=28)
        lf_detail=tk.Frame(inner,bg=COLORS["bg_main"]); lf_detail.pack(fill="both",expand=True,padx=28)
        def _refresh():
            for w in lf.winfo_children():w.destroy()
            for w in lf_detail.winfo_children():w.destroy()
            ts=sorted(self.db.get_tasks(),key=lambda t:(t["status"]!="pending",t["id"]))
            if not ts:
                tk.Label(lf,text="🎉  No tasks yet",font=("Segoe UI",12),bg=COLORS["bg_main"],fg=COLORS["text_sub"]).pack(pady=30)
                return
            # Group by subject — show project-level cards
            from collections import defaultdict
            groups=defaultdict(list)
            for t in ts: groups[t.get("subject","Other")].append(t)
            for subj,items in groups.items():
                total=len(items); done=sum(1 for t in items if t["status"]=="completed")
                dl=sorted([t.get("deadline","") for t in items if t.get("deadline")])
                deadline=dl[-1] if dl else "—"
                prios=[t.get("priority",50) for t in items]
                avg_prio=int(sum(prios)/len(prios)) if prios else 50
                if avg_prio>=80: pc=COLORS["red"]
                elif avg_prio>=50: pc=COLORS["orange"]
                else: pc=COLORS["green"]
                # Project card
                card=tk.Frame(lf,bg=COLORS["bg_card"],padx=14,pady=10,highlightbackground=COLORS["border"],highlightthickness=1)
                card.pack(fill="x",pady=3)
                # Left: status dot + title
                all_done=done==total
                dot_c=COLORS["green"] if all_done else COLORS["blue"]
                c=tk.Canvas(card,width=10,height=10,bg=COLORS["bg_card"],highlightthickness=0)
                c.create_oval(2,2,8,8,fill=dot_c,outline=""); c.pack(side="left",padx=(0,10))
                tk.Label(card,text=subj,font=("Segoe UI",12,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(side="left")
                # Priority
                tk.Label(card,text=f"Prior: {avg_prio}",font=("Segoe UI",9,"bold"),bg=COLORS["bg_card"],fg=pc).pack(side="left",padx=12)
                # Deadline
                tk.Label(card,text=f"📅 {deadline}",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(side="left",padx=6)
                # Progress
                tk.Label(card,text=f"{done}/{total} done",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["green"] if all_done else COLORS["text_sub"]).pack(side="right")
                # Expand button
                exp_btn=tk.Label(card,text="▼",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"],cursor="hand2",padx=6)
                exp_btn.pack(side="right")
                exp_btn.bind("<Button-1>",lambda e,it=items,s=subj:_show_detail(s,it))
        def _show_detail(subj,items):
            for w in lf_detail.winfo_children():w.destroy()
            dcard=Card(lf_detail,title=f"📋  {subj}",icon="",pad=14); dcard.pack(fill="x",pady=(8,0))
            for t in items:
                TaskRow(dcard,t,
                    lambda tid,it=items:(db.update_task(tid,status="completed"),_refresh()),
                    lambda tid,it=items:(messagebox.askyesno("Confirm","Delete?") and (db.delete_task(tid),_refresh()))
                ).pack(fill="x",pady=2)
        def _add(e=None):
            t=e_title.get().strip()
            if not t:messagebox.showwarning("Warning","Please enter a task name!"); return
            self.db.add_task(t,e_subj.get().strip() or "Other",e_date.get().strip()); e_title.delete(0,"end"); e_subj.delete(0,"end"); _refresh()
        add_btn.bind("<Button-1>",_add); e_title.bind("<Return>",_add)
        db=self.db  # capture for closures
        _refresh()

    # ═══ 4. AI Planner ═══
    def _show_ai(self):
        self._clear_main(); _,__,inner=self._scroll(self.main_area)
        tk.Label(inner,text="🤖  AI Planner",font=("Segoe UI",20,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(fill="x",padx=28,pady=(18,4))
        tk.Label(inner,text="Powered by DeepSeek — describe your goal, AI plans and analyzes",font=("Segoe UI",10),bg=COLORS["bg_main"],fg=COLORS["text_sub"]).pack(fill="x",padx=28,pady=(0,8))

        # Mode selector
        mode_f=tk.Frame(inner,bg=COLORS["bg_main"]); mode_f.pack(fill="x",padx=28,pady=(0,12))
        self.ai_mode=tk.StringVar(value="plan")
        for text,mode in [("🧠 Smart Plan","plan"),("🔄 Replan","replan"),("📝 Diary","diary")]:
            b=tk.Label(mode_f,text=text,font=("Segoe UI",11),bg=COLORS["bg_card"],fg=COLORS["text_sub"],padx=16,pady=8,cursor="hand2",
                       highlightbackground=COLORS["border"],highlightthickness=1)
            b.pack(side="left",padx=(0,8))
            b.bind("<Button-1>",lambda e,m=mode,b1=b:(self.ai_mode.set(m),[b2.configure(bg=COLORS["bg_card"],fg=COLORS["text_sub"]) for b2 in mode_f.winfo_children()], b1.configure(bg=COLORS["purple"],fg="#FFF")))

        # Input
        in_card=Card(inner,title="✍️  What's your goal?",icon=""); in_card.pack(fill="x",padx=28,pady=(0,12))
        self.ai_input=tk.Text(in_card,height=4,font=("Segoe UI",12),bg=COLORS["bg_input"],fg=COLORS["text_main"],
                              insertbackground=COLORS["text_main"],relief="flat",padx=12,pady=12,wrap="word")
        self.ai_input.pack(fill="x")
        go_f=tk.Frame(in_card,bg=COLORS["bg_card"]); go_f.pack(fill="x",pady=(12,0))
        go_btn=tk.Label(go_f,text="🤖  Analyze",font=("Segoe UI",12,"bold"),bg=COLORS["purple"],fg="#FFF",padx=20,pady=10,cursor="hand2")
        go_btn.pack(side="right")
        go_btn.bind("<Button-1>",lambda e:self._run_ai())
        self.ai_status=tk.Label(go_f,text="",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"])
        self.ai_status.pack(side="left",pady=(4,0))

        # Quick tip
        tips=tk.Frame(inner,bg=COLORS["bg_main"]); tips.pack(fill="x",padx=28,pady=(0,8))
        for tip in ["6/30 Computer Architecture exam — review textbook Mon, practice problems Tue-Wed"]:
            t=tk.Label(tips,text=f"💡  Try: {tip}",font=("Segoe UI",9),bg=COLORS["bg_main"],fg=COLORS["text_muted"],cursor="hand2")
            t.pack(anchor="w"); t.bind("<Button-1>",lambda e,tx=tip:(self.ai_input.delete("1.0","end"),self.ai_input.insert("1.0",tx)))

        # Results
        self.ai_result=tk.Frame(inner,bg=COLORS["bg_main"])
        self.ai_result.pack(fill="both",padx=28)

    def _run_ai(self):
        if self.ai_loading: return
        mode=self.ai_mode.get()

        if mode=="replan":
            pending=self.db.get_pending_tasks()
            if not pending:
                messagebox.showinfo("Info","No pending tasks!\nUse Smart Plan to create tasks first."); return
            if not self.api_key:self._prompt_api_key(); return
            if not self.api_key:return
            self.ai_loading=True
            today=datetime.now().strftime("%Y-%m-%d")
            tasks_list="\n".join([f"- [{t['subject']}] {t['title']} (deadline:{t.get('deadline','none')}, hours:{t.get('estimated_hours',0)}h, importance:{t.get('importance',3)}, urgency:{t.get('urgency',3)})" for t in pending])
            system_prompt = PROMPTS["plan"].replace("{today}", today)
            text = PROMPTS["replan"].replace("{today}",today).replace("{tasks_list}",tasks_list)
            call_mode = "plan"
        else:
            text=self.ai_input.get("1.0","end").strip()
            if not text:messagebox.showwarning("Warning","Please enter your goal!"); return
            if not self.api_key:self._prompt_api_key(); return
            if not self.api_key:return
            self.ai_loading=True
            today=datetime.now().strftime("%Y-%m-%d")
            raw_sp = PROMPTS.get(mode, PROMPTS["plan"])
            system_prompt = raw_sp.replace("{today}", today) if "{today}" in raw_sp else None
            call_mode = mode

        self.ai_status.config(text="⏳  Analyzing...")
        for w in self.ai_result.winfo_children():w.destroy()

        _mode=mode; _text=text; _sp=system_prompt; _cm=call_mode
        def _work():
            result=AIClient.ask(_cm,_text,self.api_key,system_prompt=_sp)
            self.win.after(0,lambda:self._show_ai_result(_mode,result,_text))

        threading.Thread(target=_work,daemon=True).start()

    def _show_ai_result(self,mode,result,raw_text):
        self.ai_loading=False; self.ai_status.config(text="")
        if "error" in result:
            messagebox.showerror("AI Error",result["error"]); return
        for w in self.ai_result.winfo_children():w.destroy()

        if mode in ("plan","replan"):
            card=Card(self.ai_result,title="📋  Plan Result",icon=""); card.pack(fill="x",pady=(6,10))
            info_f=tk.Frame(card,bg=COLORS["bg_card"]); info_f.pack(fill="x",pady=(0,10))
            info_items=[
                ("📌 Title",result.get("title","")),
                ("📅 Deadline",result.get("deadline","")),
                ("⏱ Hours",f"{result.get('hours',0)}h"),
                ("🏷 Type",result.get("type","")),
                ("⭐ Importance",f"{result.get('importance','?')}/5"),
                ("🔥 Urgency",f"{result.get('urgency','?')}/5"),
                ("🎯 Priority",f"{result.get('priority','?')}"),
            ]
            for i,(lb,vl) in enumerate(info_items):
                if vl and vl!="?/5" and vl!="?":
                    tk.Label(info_f,text=f"{lb}: {vl}",font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_main"]).grid(row=i//3,column=i%3,sticky="w",padx=4,pady=2)

            wt=result.get("weekly_theme","")
            if wt:
                wtf=tk.Frame(card,bg=COLORS["bg_accent"]); wtf.pack(fill="x",pady=(4,10))
                tk.Label(wtf,text=f"🎯  Weekly Theme: {wt}",font=("Segoe UI",12,"bold"),bg=COLORS["bg_accent"],fg=COLORS["purple"]).pack(padx=14,pady=8)

            plan=result.get("plan",[])
            if plan:
                plan_card=Card(self.ai_result,title=f"📅  Daily Plan ({len(plan)} days)",icon=""); plan_card.pack(fill="x",pady=(4,8))
                for item in plan:
                    d=item.get("date",""); wd=""
                    try:wd=WEEKDAYS_CN[datetime.strptime(d,"%Y-%m-%d").weekday()]
                    except:pass
                    day_hdr=tk.Frame(plan_card,bg=COLORS["bg_card"]); day_hdr.pack(fill="x",pady=(6,2))
                    tk.Label(day_hdr,text=f"📅  {d} {wd}",font=("Segoe UI",12,"bold"),bg=COLORS["bg_card"],fg=COLORS["purple"]).pack(anchor="w")
                    sep=tk.Frame(plan_card,bg=COLORS["divider"],height=1); sep.pack(fill="x")

                    mf=item.get("main_focus",{}) if isinstance(item.get("main_focus"),dict) else {}
                    old_title=item.get("title","")
                    if old_title and not mf:
                        mf={"title":old_title,"hours":item.get("hours",0),"note":item.get("note","")}
                    if mf and mf.get("title"):
                        mf_row=tk.Frame(plan_card,bg=COLORS["bg_card"]); mf_row.pack(fill="x",pady=2)
                        tk.Label(mf_row,text="🔵 Focus",font=("Segoe UI",9,"bold"),bg=COLORS["blue"],fg="#FFF",padx=6,pady=2).pack(side="left",padx=(0,8))
                        tk.Label(mf_row,text=mf.get("title",""),font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"],anchor="w").pack(side="left",fill="x",expand=True)
                        mh=mf.get("hours",0)
                        if mh:tk.Label(mf_row,text=f"⏱ {mh}h",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(side="right")
                        mn=mf.get("note","")
                        if mn:
                            nt_row=tk.Frame(plan_card,bg=COLORS["bg_card"]); nt_row.pack(fill="x")
                            tk.Label(nt_row,text=f"    💡 {mn}",font=("Segoe UI",8),bg=COLORS["bg_card"],fg=COLORS["text_muted"]).pack(anchor="w")

                    qts=item.get("quick_tasks",[])
                    if qts:
                        for qt in qts:
                            qt_row=tk.Frame(plan_card,bg=COLORS["bg_card"]); qt_row.pack(fill="x",pady=1)
                            tk.Label(qt_row,text="🟢 Quick",font=("Segoe UI",9,"bold"),bg=COLORS["green"],fg="#FFF",padx=6,pady=2).pack(side="left",padx=(0,8))
                            tk.Label(qt_row,text=qt.get("title",""),font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_main"],anchor="w").pack(side="left",fill="x",expand=True)
                            qh=qt.get("hours",0)
                            if qh:tk.Label(qt_row,text=f"⏱ {qh}h",font=("Segoe UI",8),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(side="right")
                            qn=qt.get("note","")
                            if qn:tk.Label(qt_row,text=f"💡 {qn}",font=("Segoe UI",8),bg=COLORS["bg_card"],fg=COLORS["text_muted"]).pack(side="right",padx=6)

                import_btn=tk.Label(plan_card,text="✅  Import All Tasks",font=("Segoe UI",11,"bold"),bg=COLORS["green"],fg="#FFF",padx=20,pady=10,cursor="hand2")
                import_btn.pack(pady=(12,0))
                def _imp():
                    tl=[]
                    meta={"importance":result.get("importance",3),"urgency":result.get("urgency",3),
                          "priority":result.get("priority",50),"weekly_theme":result.get("weekly_theme","")}
                    for it in plan:
                        mf=it.get("main_focus",{}) if isinstance(it.get("main_focus"),dict) else {}
                        old_t=it.get("title","")
                        if old_t and not mf:
                            tl.append({"title":old_t,"subject":result.get("title",""),"deadline":result.get("deadline",""),
                                       "plan_date":it.get("date",""),"hours":it.get("hours",0),
                                       "task_type":"main_focus","importance":meta["importance"],
                                       "urgency":meta["urgency"],"priority":meta["priority"],
                                       "weekly_theme":meta["weekly_theme"]})
                        else:
                            if mf and mf.get("title"):
                                tl.append({"title":mf["title"],"subject":result.get("title",""),
                                           "deadline":result.get("deadline",""),"plan_date":it.get("date",""),
                                           "hours":mf.get("hours",0),"task_type":"main_focus",
                                           "importance":meta["importance"],"urgency":meta["urgency"],
                                           "priority":meta["priority"],"weekly_theme":meta["weekly_theme"]})
                            for qt in it.get("quick_tasks",[]):
                                tl.append({"title":qt["title"],"subject":result.get("title",""),
                                           "deadline":result.get("deadline",""),"plan_date":it.get("date",""),
                                           "hours":qt.get("hours",0),"task_type":"quick_task",
                                           "importance":max(1,meta["importance"]-1),
                                           "urgency":meta["urgency"],"priority":max(0,meta["priority"]-20),
                                           "weekly_theme":meta["weekly_theme"]})
                    self.db.add_tasks_batch(tl)
                    nf=sum(1 for t in tl if t['task_type']=='main_focus')
                    nq=sum(1 for t in tl if t['task_type']=='quick_task')
                    messagebox.showinfo("Imported",f"{len(tl)} tasks imported ({nf} focus + {nq} quick)!")
                import_btn.bind("<Button-1>",lambda e:_imp())

            adv=result.get("advice","")
            if adv:
                ac=Card(self.ai_result,title="💡  AI Advice",icon=""); ac.pack(fill="x",pady=(4,10))
                tk.Label(ac,text=adv,font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_main"],wraplength=1200).pack(anchor="w")
            if mode=="plan":
                self.ai_input.delete("1.0","end")

        elif mode=="diary":
            card=Card(self.ai_result,title="📊  Diary Analysis",icon=""); card.pack(fill="x",pady=(6,10))

            mood=result.get("mood",{})
            me={"happy":"😊","tired":"😫","anxious":"😰","sad":"😢","calm":"😌","excited":"🤩","bored":"😐"}.get(mood.get("primary",""),"😶")
            mr=tk.Frame(card,bg=COLORS["bg_card"]); mr.pack(fill="x",pady=4)
            tk.Label(mr,text=f"{me}  Mood",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"],width=12,anchor="w").pack(side="left")
            sc=mood.get("score",5)
            bar=tk.Frame(mr,bg=COLORS["bg_input"],height=18); bar.pack(side="left",fill="x",expand=True,padx=8)
            tk.Frame(bar,bg=COLORS["green"] if sc>=6 else COLORS["orange"],width=sc*30,height=18).place(x=0,y=0,width=sc*30,height=18)
            tk.Label(mr,text=f"{sc}/10",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(side="right")

            sleep=result.get("sleep",{})
            si={"good":"😴💤","ok":"😴","bad":"😫⚠️","unknown":"❓"}.get(sleep.get("quality",""),"❓")
            sr=tk.Frame(card,bg=COLORS["bg_card"]); sr.pack(fill="x",pady=4)
            tk.Label(sr,text=f"{si}  Sleep",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"],width=12,anchor="w").pack(side="left")
            tk.Label(sr,text=f"{sleep.get('hours',0)}h · {sleep.get('quality','')}",font=("Segoe UI",11),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(side="left")

            for label,items,color in [("✨ Highlights",result.get("highlights",[]),COLORS["green"]),("💔 Lowlights",result.get("lowlights",[]),COLORS["red"])]:
                if items:
                    fr=tk.Frame(card,bg=COLORS["bg_card"]); fr.pack(fill="x",pady=2)
                    tk.Label(fr,text=f"{label}",font=("Segoe UI",10,"bold"),bg=COLORS["bg_card"],fg=color,width=12,anchor="w").pack(side="left",anchor="n")
                    tf2=tk.Frame(fr,bg=COLORS["bg_card"]); tf2.pack(side="left",fill="x",expand=True)
                    for it in items:tk.Label(tf2,text=f"• {it}",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"],anchor="w").pack(anchor="w")

            reply=result.get("reply","")
            if reply:
                rc=Card(self.ai_result,title="💬  AI Says",icon=""); rc.pack(fill="x",pady=(8,10))
                tk.Label(rc,text=reply,font=("Segoe UI",11),bg=COLORS["bg_card"],fg=COLORS["purple"],wraplength=1200).pack(anchor="w")

            sugs=result.get("suggestions",[])
            if sugs:
                sc2=Card(self.ai_result,title="💡  Suggestions",icon=""); sc2.pack(fill="x",pady=(4,10))
                for s in sugs:tk.Label(sc2,text=f"• {s}",font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_main"],wraplength=1200,anchor="w").pack(anchor="w",pady=2)

            self.db.add_diary(raw_text,result)
            save_btn=tk.Label(self.ai_result,text="✅  Diary saved",font=("Segoe UI",10),bg=COLORS["bg_main"],fg=COLORS["green"])
            save_btn.pack(pady=(4,10))
            self.ai_input.delete("1.0","end")

    # ═══ 5. Vision ═══
    def _show_vision(self):
        self._clear_main(); _,__,inner=self._scroll(self.main_area)
        tk.Label(inner,text="🌟  Life Vision",font=("Segoe UI",20,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(fill="x",padx=28,pady=(18,4))
        tk.Label(inner,text="Write down who you want to become. AI helps you understand yourself.",font=("Segoe UI",10),bg=COLORS["bg_main"],fg=COLORS["text_sub"]).pack(fill="x",padx=28,pady=(0,14))

        in_card=Card(inner,title="✍️  Your Vision",icon=""); in_card.pack(fill="x",padx=28,pady=(0,12))
        tk.Label(in_card,text="e.g. I want to become an engineer who solves real problems with technology, maintain reading and exercise habits, have my own team before 30",
                 font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"]).pack(anchor="w",pady=(0,8))
        self.vision_input=tk.Text(in_card,height=3,font=("Segoe UI",12),bg=COLORS["bg_input"],fg=COLORS["text_main"],
                                  insertbackground=COLORS["text_main"],relief="flat",padx=12,pady=12,wrap="word")
        self.vision_input.pack(fill="x")
        go_f=tk.Frame(in_card,bg=COLORS["bg_card"]); go_f.pack(fill="x",pady=(10,0))
        self.vision_status=tk.Label(go_f,text="",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"])
        self.vision_status.pack(side="left",pady=(4,0))
        go_btn=tk.Label(go_f,text="🤖  Deep Analysis",font=("Segoe UI",12,"bold"),bg=COLORS["purple"],fg="#FFF",padx=20,pady=10,cursor="hand2")
        go_btn.pack(side="right")
        go_btn.bind("<Button-1>",lambda e:self._run_vision())

        self.vision_result=tk.Frame(inner,bg=COLORS["bg_main"])
        self.vision_result.pack(fill="both",padx=28)

        visions=self.db.get_visions()
        if visions:
            tc=Card(inner,title="📜  Vision Timeline",icon=""); tc.pack(fill="x",padx=28,pady=(12,20))
            for v in visions[:5]:
                a=v.get("analysis",{})
                r=tk.Frame(tc,bg=COLORS["bg_card"]); r.pack(fill="x",pady=3)
                tk.Label(r,text=v.get("date",""),font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"],width=18,anchor="w").pack(side="left")
                themes=a.get("core_themes","") if isinstance(a,dict) else ""
                if themes:tk.Label(r,text=" · ".join(themes[:3]),font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["purple"],anchor="w").pack(side="left",fill="x",expand=True)

    def _run_vision(self):
        text=self.vision_input.get("1.0","end").strip()
        if not text:messagebox.showwarning("Warning","Please write your vision first!"); return
        if not self.api_key:self._prompt_api_key(); return
        if not self.api_key:return

        self.vision_status.config(text="⏳  Analyzing...")
        for w in self.vision_result.winfo_children():w.destroy()

        def _work():
            result=AIClient.ask("vision",text,self.api_key)
            self.win.after(0,lambda:self._show_vision_result(result,text))

        threading.Thread(target=_work,daemon=True).start()

    def _show_vision_result(self,result,raw):
        self.vision_status.config(text="")
        if "error" in result:
            messagebox.showerror("AI Error",result["error"]); return

        for w in self.vision_result.winfo_children():w.destroy()

        card=Card(self.vision_result,title="🔍  Deep Analysis",icon=""); card.pack(fill="x",pady=(6,10))
        themes=result.get("core_themes",[])
        if themes:
            tf=tk.Frame(card,bg=COLORS["bg_card"]); tf.pack(fill="x",pady=(0,8))
            for th in themes:
                tk.Label(tf,text=f"  {th}  ",font=("Segoe UI",11),bg=COLORS["bg_accent"],fg=COLORS["purple"],padx=10,pady=4).pack(side="left",padx=4)

        cp=result.get("career_path","")
        if cp:
            tk.Label(card,text="💼  Career Path",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(anchor="w",pady=(4,2))
            tk.Label(card,text=cp,font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_sub"],wraplength=1200).pack(anchor="w",pady=(0,8))

        gaps=result.get("habit_gaps",[])
        if gaps:
            tk.Label(card,text="📊  Current vs Vision",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(anchor="w",pady=(4,2))
            for g in gaps:
                r=tk.Frame(card,bg=COLORS["bg_card"]); r.pack(fill="x",pady=2)
                tk.Label(r,text=f"🎯 {g.get('goal','')}",font=("Segoe UI",10,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(side="left")
                tk.Label(r,text=f"→ {g.get('status','')}",font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["orange"]).pack(side="right")

        for label,items,icon in [("This Week",result.get("short_term",[]),"⚡"),("Milestones",result.get("mid_term",[]),"🎯")]:
            if items:
                ac=Card(self.vision_result,title=f"{icon}  {label}",icon=""); ac.pack(fill="x",pady=(8,8))
                for it in items:tk.Label(ac,text=f"• {it}",font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_main"],wraplength=1200,anchor="w").pack(anchor="w",pady=2)

        insp=result.get("inspiration","")
        if insp:
            ic=Card(self.vision_result,icon=""); ic.pack(fill="x",pady=(4,12))
            tk.Label(ic,text=f"💫 {insp}",font=("Segoe UI",12,"bold"),bg=COLORS["bg_card"],fg=COLORS["purple"],wraplength=1200).pack()

        self.db.add_vision(raw,result)
        self.vision_input.delete("1.0","end")
        messagebox.showinfo("Saved","Vision saved!\nScroll down to see your vision timeline.")

    # ═══ Run ═══
    def run(self):
        self.win.mainloop()


if __name__=="__main__":
    App().run()
