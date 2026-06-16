"""
🌱 学生成长助手 — AI 驱动的自我管理工具
==========================================
DeepSeek AI · 任务管理 · 日历规划 · 自我认知 · 人生愿景

运行: python main.py
依赖: pip install ttkbootstrap requests
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime, timedelta
import json, os, re, calendar, random, threading, requests

# ============================================================
#  配置
# ============================================================
APP_TITLE = "🌱 学生成长助手"
WINDOW_WIDTH, WINDOW_HEIGHT = 2400, 1600
MIN_WIDTH, MIN_HEIGHT = 2000, 1400
DATA_FILE = "growth_data.json"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SIDEBAR_W = 380

WEEKDAYS_CN = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
WEEKDAYS_SHORT = ["一","二","三","四","五","六","日"]

DARK_COLORS = {
    "bg_main":"#0F1117","bg_side":"#141622","bg_card":"#1C1E2A",
    "bg_input":"#252838","bg_hover":"#222640","bg_accent":"#1A1530",
    "purple":"#A78BFA","purple_dark":"#7C5CDB","green":"#34D399",
    "orange":"#FBBF24","red":"#F87171","blue":"#60A5FA","teal":"#2DD4BF",
    "text_main":"#E8ECF1","text_sub":"#94A3B8","text_muted":"#64748B",
    "border":"#2A2F42","divider":"#1E2235",
}
LIGHT_COLORS = {
    "bg_main":"#FAFBFC","bg_side":"#FFFFFF","bg_card":"#FFFFFF",
    "bg_input":"#F8F9FC","bg_hover":"#F1F3F9","bg_accent":"#F5F3FF",
    "purple":"#7C3AED","purple_dark":"#6C5CE7","green":"#10B981",
    "orange":"#F59E0B","red":"#EF4444","blue":"#3B82F6","teal":"#14B8A6",
    "text_main":"#111827","text_sub":"#6B7280","text_muted":"#9CA3AF",
    "border":"#E5E7EB","divider":"#F3F4F6",
}
COLORS = LIGHT_COLORS.copy()

PROMPTS = {
    "plan": """你是学生成长助手的规划师。用户描述一个目标或任务，请你：
1. 识别任务类型（考试备考/习惯养成/阅读计划/项目任务）
2. 提取截止日期、预估工时
3. 如果有子任务描述，按描述分配；如果没有，按工作日均分
4. 返回JSON格式，不要任何其他文字：
{
  "type": "类型（中文）",
  "title": "任务总标题",
  "deadline": "YYYY-MM-DD",
  "hours": 数字（小时）,
  "plan": [
    {"date": "YYYY-MM-DD", "title": "当天任务名", "hours": 数字, "note": "简短提示"}
  ],
  "advice": "给用户的一句执行建议"
}""",

    "diary": """你是学生成长助手的心理分析师。分析用户日记，返回JSON：
{
  "mood": {"primary": "情绪词", "score": 1-10},
  "sleep": {"hours": 数字, "quality": "good/ok/bad"},
  "highlights": ["正面事件"],
  "lowlights": ["负面事件"],
  "social": "社交情况简述",
  "suggestions": ["3条个性化建议"],
  "reply": "一段温暖有共情力的回应，像朋友一样，2-3句"
}""",

    "vision": """你是学生成长助手的人生教练。分析用户的人生愿景，结合其当前情况给出深度剖析。返回JSON：
{
  "core_themes": ["核心主题词1", "主题词2", "主题词3"],
  "career_path": "职业方向分析",
  "habit_gaps": [{"goal": "愿景中的习惯目标", "status": "当前状态"}],
  "short_term": ["本周3个可执行的行动建议"],
  "mid_term": ["本学期/今年的里程碑建议"],
  "inspiration": "一句激励话语"
}""",
}


# ============================================================
#  AI 客户端
# ============================================================
class AIClient:
    """DeepSeek API 调用封装。"""

    @staticmethod
    def get_api_key():
        """从数据文件读取 API Key，没有则弹窗询问。"""
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
    def ask(prompt_type, user_text, api_key):
        """发送请求到 DeepSeek，返回解析后的结果。"""
        if not api_key:
            return {"error": "请先设置 DeepSeek API Key"}

        system_prompt = PROMPTS.get(prompt_type, PROMPTS["plan"])

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
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
                timeout=30,
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            # 提取 JSON
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```\w*\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            return json.loads(content)
        except requests.exceptions.Timeout:
            return {"error": "请求超时，请检查网络连接"}
        except requests.exceptions.ConnectionError:
            return {"error": "无法连接 DeepSeek，请检查网络"}
        except json.JSONDecodeError:
            return {"error": f"AI 返回格式异常：{content[:200]}..."}
        except Exception as e:
            return {"error": f"请求失败：{str(e)}"}


# ============================================================
#  数据管理
# ============================================================
class DataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    return json.load(f)
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

    # 任务
    def get_tasks(self, date_str=None):
        tasks = self.data.get("tasks",[])
        return [t for t in tasks if t.get("plan_date")==date_str] if date_str else tasks

    def add_task(self, title, subject, deadline, plan_date=None, hours=0):
        t = {"id":self.data["next_id"], "title":title, "subject":subject or "其他",
             "deadline":deadline or "", "plan_date":plan_date or datetime.now().strftime("%Y-%m-%d"),
             "estimated_hours":hours, "status":"pending",
             "created":datetime.now().strftime("%Y-%m-%d %H:%M")}
        self.data["tasks"].append(t)
        self.data["next_id"]+=1
        self.save()
        return t

    def add_tasks_batch(self, items):
        for it in items:
            self.add_task(it.get("title",""),it.get("subject",""),it.get("deadline",""),
                         it.get("plan_date",""),it.get("hours",0))

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
        r={}
        for t in self.data["tasks"]:
            pd=t.get("plan_date","")
            if pd and pd.startswith(f"{y}-{m:02d}"):
                d=int(pd.split("-")[2]); r[d]=r.get(d,0)+1
        return r

    # 日记
    def add_diary(self, text, analysis):
        e={"date":datetime.now().strftime("%Y-%m-%d"),"raw":text,"analysis":analysis}
        self.data["diary"].append(e); self.save()

    def get_diary(self, limit=30):
        return sorted(self.data.get("diary",[]), key=lambda x:x.get("date",""), reverse=True)[:limit]

    # 人生愿景
    def add_vision(self, text, analysis):
        v={"date":datetime.now().strftime("%Y-%m-%d %H:%M"),"raw":text,"analysis":analysis}
        self.data["visions"].append(v); self.save()

    def get_visions(self):
        return sorted(self.data.get("visions",[]), key=lambda x:x.get("date",""), reverse=True)


# ============================================================
#  UI 组件
# ============================================================
class Card(tk.Frame):
    """高级感卡片容器。"""
    def __init__(self, parent, title="", icon="", pad=20, **kw):
        super().__init__(parent, bg=COLORS["bg_card"], padx=pad, pady=pad, **kw)
        self.configure(highlightbackground=COLORS["border"],highlightthickness=1)
        if title:
            h=tk.Frame(self, bg=COLORS["bg_card"])
            h.pack(fill="x", pady=(0,pad-6))
            tk.Label(h, text=f"{icon}  {title}", font=("Segoe UI",13,"bold"),
                     bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(anchor="w")
            tk.Frame(h, bg=COLORS["divider"],height=1).pack(fill="x",pady=(8,0))


class StatCard(tk.Frame):
    def __init__(self, parent, icon, label, color, **kw):
        super().__init__(parent, bg=COLORS["bg_card"], padx=18, pady=14, **kw)
        self.configure(highlightbackground=COLORS["border"],highlightthickness=1)
        tk.Label(self,text=icon,font=("Segoe UI Emoji",20),bg=COLORS["bg_card"],fg=color).pack(anchor="w")
        self.v=tk.Label(self,text="0",font=("Segoe UI",26,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"])
        self.v.pack(anchor="w",pady=(2,0))
        tk.Label(self,text=label,font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(anchor="w")
    def set(self,val): self.v.config(text=str(val))


class TaskRow(tk.Frame):
    def __init__(self,parent,task,on_done,on_del):
        super().__init__(parent,bg=COLORS["bg_card"],padx=12,pady=8)
        self.configure(highlightbackground=COLORS["border"],highlightthickness=1)
        done=task["status"]=="completed"
        dc=COLORS["green"] if done else COLORS["orange"]
        c=tk.Canvas(self,width=8,height=8,bg=COLORS["bg_card"],highlightthickness=0)
        c.create_oval(1,1,7,7,fill=dc,outline=""); c.pack(side="left",padx=(0,8))
        ts=("Segoe UI",11,"overstrike") if done else ("Segoe UI",11,"bold")
        tf=COLORS["text_sub"] if done else COLORS["text_main"]
        tk.Label(self,text=task["title"],font=ts,bg=COLORS["bg_card"],fg=tf,anchor="w").pack(side="left",fill="x",expand=True)
        tk.Label(self,text=f" {task['subject']} ",font=("Segoe UI",8),bg=COLORS["purple_dark"],fg="#FFF",padx=6,pady=1).pack(side="left",padx=6)
        pd=task.get("plan_date","")
        if pd: tk.Label(self,text=f"📅 {pd}",font=("Segoe UI",8),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(side="left",padx=4)
        if not done:
            b=tk.Label(self,text=" ✓ ",font=("Segoe UI",9,"bold"),bg=COLORS["green"],fg="#FFF",padx=8,pady=3,cursor="hand2"); b.pack(side="right",padx=1)
            b.bind("<Button-1>",lambda e:on_done(task["id"]))
        b2=tk.Label(self,text=" ✕ ",font=("Segoe UI",9),bg=COLORS["red"],fg="#FFF",padx=8,pady=3,cursor="hand2"); b2.pack(side="right",padx=1)
        b2.bind("<Button-1>",lambda e:on_del(task["id"]))


# ============================================================
#  主应用
# ============================================================
class App:
    def __init__(self):
        self.db=DataManager()
        self.is_dark=False
        self.api_key=self.db.get_api_key()

        # 窗口
        self.win=ttk.Window(themename="flatly")
        self.win.title(APP_TITLE)
        self.win.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.win.minsize(MIN_WIDTH,MIN_HEIGHT)
        self.win.configure(bg=COLORS["bg_main"])

        self.current_page=None
        self.ai_loading=False

        self._build_layout()
        self._nav_to_page("dashboard")

        # 没有 API Key 时提示
        if not self.api_key:
            self.win.after(500, self._prompt_api_key)

    # ═══ 布局 ═══
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
        tk.Label(lf,text="学生成长助手",font=("Segoe UI",15,"bold"),bg=COLORS["bg_side"],fg=COLORS["text_main"]).pack(anchor="w",pady=(4,0))
        tk.Label(lf,text="AI-Powered Growth",font=("Segoe UI",8),bg=COLORS["bg_side"],fg=COLORS["text_muted"]).pack(anchor="w")
        tk.Frame(self.sidebar,bg=COLORS["divider"],height=1).pack(fill="x",padx=18,pady=(0,14))

        # 导航
        self.nav_btns={}
        for key,text in [("dashboard","📊  总览"),("calendar","📅  日历"),("tasks","✅  任务"),
                          ("ai","🤖  AI 助手"),("vision","🌟  人生愿景")]:
            b=tk.Label(self.sidebar,text=text,font=("Segoe UI",12),bg=COLORS["bg_side"],
                       fg=COLORS["text_sub"],anchor="w",padx=24,pady=11,cursor="hand2")
            b.pack(fill="x")
            b.bind("<Button-1>",lambda e,k=key:self._nav_to_page(k))
            b.bind("<Enter>",lambda e,b=b:b.configure(bg=COLORS["bg_hover"]))
            b.bind("<Leave>",lambda e,b=b,k=key:
                b.configure(bg=COLORS["bg_hover"] if self.current_page==k else COLORS["bg_side"]))
            self.nav_btns[key]=b

        # 主题切换
        sp=tk.Frame(self.sidebar,bg=COLORS["bg_side"]); sp.pack(fill="both",expand=True)
        tk.Frame(self.sidebar,bg=COLORS["border"],height=1).pack(fill="x",padx=16,pady=(0,12))
        self.theme_btn=tk.Frame(self.sidebar,bg=COLORS["bg_side"],padx=16,pady=10,cursor="hand2")
        self.theme_btn.pack(fill="x",pady=(0,16))
        self.theme_icon=tk.Label(self.theme_btn,text="🌙",font=("Segoe UI Emoji",14),bg=COLORS["bg_side"],fg=COLORS["text_sub"])
        self.theme_icon.pack(side="left",padx=(0,12))
        self.theme_text=tk.Label(self.theme_btn,text="暗色模式",font=("Segoe UI",11),bg=COLORS["bg_side"],fg=COLORS["text_sub"],anchor="w")
        self.theme_text.pack(side="left")
        for w in[self.theme_btn,self.theme_icon,self.theme_text]:w.bind("<Button-1>",lambda e:self._toggle_theme())

        # API Key 设置
        self.api_btn=tk.Label(self.sidebar,text="⚙️  API设置",font=("Segoe UI",10),bg=COLORS["bg_side"],
                              fg=COLORS["text_muted"],anchor="w",padx=24,pady=6,cursor="hand2")
        self.api_btn.pack(fill="x",pady=(0,8))
        self.api_btn.bind("<Button-1>",lambda e:self._prompt_api_key())

    # ═══ 导航 & 主题 ═══
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
        self.theme_text.config(text="亮色模式" if self.is_dark else "暗色模式")
        self._nav_to_page(self.current_page)

    def _prompt_api_key(self):
        key=simpledialog.askstring("DeepSeek API Key",
            "请输入 DeepSeek API Key：\n\n"
            "1. 访问 platform.deepseek.com 注册\n"
            "2. 在「API Keys」页面创建 Key\n"
            "3. 新用户有免费额度\n\n"
            "（本地存储，不会上传）",
            parent=self.win)
        if key:
            self.api_key=key.strip()
            self.db.set_api_key(self.api_key)
            messagebox.showinfo("成功","API Key 已保存！\n现在可以使用 AI 助手了。")

    # ═══ 滚动容器 ═══
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

    # ═══ 1. 总览 ═══
    def _show_dashboard(self):
        self._clear_main()
        stats=self.db.get_stats()
        today=datetime.now().strftime("%Y-%m-%d")
        _,__,inner=self._scroll(self.main_area)

        h=datetime.now().hour
        g="早上好！☀️" if h<12 else ("下午好！🌤️" if h<18 else "晚上好！🌙")
        tk.Label(inner,text=g,font=("Segoe UI",24,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(fill="x",padx=30,pady=(22,2))
        tk.Label(inner,text=f"{today}  {WEEKDAYS_CN[datetime.now().weekday()]}",font=("Segoe UI",11),bg=COLORS["bg_main"],fg=COLORS["text_sub"]).pack(fill="x",padx=30,pady=(0,20))

        # 统计卡
        cards=tk.Frame(inner,bg=COLORS["bg_main"]); cards.pack(fill="x",padx=30,pady=4)
        for i in range(4):cards.columnconfigure(i,weight=1,uniform="c")
        for i,(ic,lb,val,cl) in enumerate([
            ("📋","全部",stats["total"],COLORS["purple"]),
            ("⏳","待完成",stats["pending"],COLORS["orange"]),
            ("✅","已完成",stats["completed"],COLORS["green"]),
            ("📅","今日",f"{stats['today_done']}/{stats['today_total']}",COLORS["blue"]),
        ]):
            c=StatCard(cards,ic,lb,cl); c.grid(row=0,column=i,sticky="nsew",padx=4); c.set(val)

        # 今日任务
        td_tasks=self.db.get_tasks(today)
        c1=Card(inner,title="今日任务",icon="📅"); c1.pack(fill="x",padx=30,pady=(18,10))
        if td_tasks:
            for t in td_tasks:
                r=tk.Frame(c1,bg=COLORS["bg_card"]); r.pack(fill="x",pady=2)
                dn=t["status"]=="completed"; dc=COLORS["green"] if dn else COLORS["orange"]
                cc=tk.Canvas(r,width=8,height=8,bg=COLORS["bg_card"],highlightthickness=0)
                cc.create_oval(1,1,7,7,fill=dc,outline=""); cc.pack(side="left",padx=(0,8))
                ts=("Segoe UI",10,"overstrike") if dn else ("Segoe UI",10)
                tf=COLORS["text_sub"] if dn else COLORS["text_main"]
                tk.Label(r,text=t["title"],font=ts,bg=COLORS["bg_card"],fg=tf,anchor="w").pack(side="left",fill="x",expand=True)
                hh=t.get("estimated_hours",0)
                if hh:tk.Label(r,text=f"⏱ {hh}h",font=("Segoe UI",8),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(side="right",padx=6)
        else:
            tk.Label(c1,text="今天还没有安排，去「AI 助手」规划吧 ✨",font=("Segoe UI",11),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(pady=10)

        # Visions 快照
        visions=self.db.get_visions()
        if visions:
            c2=Card(inner,title="🌟  最新愿景",icon=""); c2.pack(fill="x",padx=30,pady=(12,20))
            v=visions[0]
            a=v.get("analysis",{})
            themes=a.get("core_themes","") if isinstance(a,dict) else ""
            if themes:
                tk.Label(c2,text=" · ".join(themes),font=("Segoe UI",11),bg=COLORS["bg_card"],fg=COLORS["purple"],wraplength=1200).pack(anchor="w")
            tk.Label(c2,text=v.get("date",""),font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"]).pack(anchor="w",pady=(6,0))

    # ═══ 2. 日历 ═══
    def _show_calendar(self):
        self._clear_main()
        today=datetime.now(); self.cal_y=today.year; self.cal_m=today.month

        top=tk.Frame(self.main_area,bg=COLORS["bg_main"]); top.pack(fill="x",padx=24,pady=(16,8))
        tk.Label(top,text="📅  日历",font=("Segoe UI",20,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(side="left")
        nav=tk.Frame(top,bg=COLORS["bg_main"]); nav.pack(side="right")
        self.cal_title=tk.Label(nav,text="",font=("Segoe UI",14,"bold"),bg=COLORS["bg_main"],fg=COLORS["purple"])
        self.cal_title.pack(side="left",padx=16)
        body=tk.Frame(self.main_area,bg=COLORS["bg_main"]); body.pack(fill="both",expand=True,padx=24,pady=(0,12))
        week_f=Card(self.main_area,title="本周概览",icon="📋"); week_f.pack(fill="x",padx=24,pady=(0,16))
        self._draw_cal(body,week_f)

    def _draw_cal(self,parent,week_f):
        for w in parent.winfo_children():w.destroy()
        self.cal_title.config(text=f"{self.cal_y}年  {self.cal_m}月")
        mt=self.db.get_month_tasks(self.cal_y,self.cal_m)
        today=datetime.now()
        weeks=calendar.Calendar(firstweekday=0).monthdayscalendar(self.cal_y,self.cal_m)

        hdr=tk.Frame(parent,bg=COLORS["bg_main"]); hdr.pack(fill="x",pady=(6,2))
        for i,wd in enumerate(WEEKDAYS_SHORT):
            hdr.columnconfigure(i,weight=1,uniform="cal")
            tk.Label(hdr,text=wd,font=("Segoe UI",10,"bold"),bg=COLORS["bg_main"],fg=COLORS["red"] if i>=5 else COLORS["text_sub"]).grid(row=0,column=i,sticky="ew")

        for wk in weeks:
            row=tk.Frame(parent,bg=COLORS["bg_main"]); row.pack(fill="x",pady=1)
            for i in range(7):row.columnconfigure(i,weight=1,uniform="cal")
            for di,day in enumerate(wk):
                if day==0:
                    tk.Frame(row,bg=COLORS["bg_main"],padx=4,pady=4).grid(row=0,column=di,sticky="nsew"); continue
                ist=(day==today.day and self.cal_m==today.month and self.cal_y==today.year)
                cb=COLORS["purple_dark"] if ist else COLORS["bg_card"]
                cell=tk.Frame(row,bg=cb,padx=4,pady=4,highlightbackground=COLORS["border"],highlightthickness=1)
                cell.grid(row=0,column=di,sticky="nsew")
                tk.Label(cell,text=str(day),font=("Segoe UI",11,"bold"),bg=cb,fg="#FFF" if ist else COLORS["text_main"]).pack(anchor="ne")
                cnt=mt.get(day,0)
                if cnt:
                    dots=tk.Frame(cell,bg=cb); dots.pack(anchor="sw",pady=(4,0))
                    for j in range(min(cnt,4)):
                        dc=COLORS["green"] if j<cnt//2 else COLORS["orange"]
                        c=tk.Canvas(dots,width=6,height=6,bg=cb,highlightthickness=0)
                        c.create_oval(1,1,5,5,fill=dc,outline=""); c.pack(side="left",padx=1)
                cell.bind("<Button-1>",lambda e,d=day:self._day_detail(d))
                for ch in cell.winfo_children():ch.bind("<Button-1>",lambda e,d=day:self._day_detail(d))

        # 周视图
        for w in week_f.winfo_children():
            if isinstance(w,tk.Frame) and w!=week_f: continue
        # clear old week content
        for w in list(week_f.winfo_children()):
            if w not in [c for c in week_f.winfo_children() if isinstance(c,tk.Label) and c.cget("text").startswith("📋")]:
                w.destroy()
        # find the week frame after title
        wf_content=tk.Frame(week_f,bg=COLORS["bg_card"]); wf_content.pack(fill="x",padx=0,pady=(6,4))
        # Actually simpler: just rebuild the week part
        monday=today-timedelta(days=today.weekday())
        for i in range(7):wf_content.columnconfigure(i,weight=1,uniform="wk")
        for i in range(7):
            d=monday+timedelta(days=i); ds=d.strftime("%Y-%m-%d")
            dt=self.db.get_tasks(ds); ist=d.date()==today.date()
            cell=tk.Frame(wf_content,bg=COLORS["bg_card"],padx=6,pady=6,highlightbackground=COLORS["border"],highlightthickness=1)
            cell.grid(row=0,column=i,sticky="nsew",padx=2)
            dd=COLORS["purple"] if ist else COLORS["text_main"]
            tk.Label(cell,text=f"周{WEEKDAYS_SHORT[i]}\n{d.day}",font=("Segoe UI",9,"bold"),bg=COLORS["bg_card"],fg=dd).pack(pady=(0,4))
            if dt:
                dn=sum(1 for t in dt if t["status"]=="completed")
                tk.Label(cell,text=f"✅ {dn}/{len(dt)}",font=("Segoe UI",8),bg=COLORS["bg_card"],fg=COLORS["green"] if dn==len(dt) else COLORS["orange"]).pack()
            else:
                tk.Label(cell,text="—",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"]).pack()

    def _day_detail(self,day):
        ds=f"{self.cal_y}-{self.cal_m:02d}-{day:02d}"; tasks=self.db.get_tasks(ds)
        w=tk.Toplevel(self.win); w.title(f"📅 {ds}"); w.geometry("620x520"); w.configure(bg=COLORS["bg_card"]); w.transient(self.win)
        try:wd=WEEKDAYS_CN[datetime.strptime(ds,"%Y-%m-%d").weekday()]
        except:wd=""
        tk.Label(w,text=f"📅  {ds}  {wd}",font=("Segoe UI",14,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(padx=20,pady=(20,14))
        if tasks:
            for t in tasks:
                r=tk.Frame(w,bg=COLORS["bg_card"]); r.pack(fill="x",padx=20,pady=3)
                dn=t["status"]=="completed"; dc=COLORS["green"] if dn else COLORS["orange"]
                cc=tk.Canvas(r,width=8,height=8,bg=COLORS["bg_card"],highlightthickness=0)
                cc.create_oval(1,1,7,7,fill=dc,outline=""); cc.pack(side="left",padx=(0,8))
                ts=("Segoe UI",11,"overstrike") if dn else ("Segoe UI",11)
                tf=COLORS["text_sub"] if dn else COLORS["text_main"]
                tk.Label(r,text=t["title"],font=ts,bg=COLORS["bg_card"],fg=tf,anchor="w").pack(side="left",fill="x",expand=True)
                def _tg(tid=t["id"]):
                    ns="pending" if t["status"]=="completed" else "completed"
                    self.db.update_task(tid,status=ns); w.destroy(); self._day_detail(day)
                bt="↩ 撤销" if dn else "✓ 完成"; bc=COLORS["orange"] if dn else COLORS["green"]
                b=tk.Label(r,text=bt,font=("Segoe UI",9),bg=bc,fg="#FFF",padx=10,pady=3,cursor="hand2")
                b.pack(side="right"); b.bind("<Button-1>",lambda e,cb=_tg:cb())
        else:
            tk.Label(w,text="📭 这天还没有任务",font=("Segoe UI",12),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(expand=True)

    # ═══ 3. 任务管理 ═══
    def _show_tasks(self):
        self._clear_main(); _,__,inner=self._scroll(self.main_area)
        tk.Label(inner,text="✅  任务管理",font=("Segoe UI",20,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(fill="x",padx=28,pady=(18,14))

        form=Card(inner,title="添加新任务",icon="➕"); form.pack(fill="x",padx=28,pady=(0,14))
        ff=tk.Frame(form,bg=COLORS["bg_card"]); ff.pack(fill="x")
        for i in range(4):ff.columnconfigure(i,weight=[2,1,1,0][i],uniform="f")
        tk.Label(ff,text="任务",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).grid(row=0,column=0,sticky="w")
        e_title=tk.Entry(ff,font=("Segoe UI",11),bg=COLORS["bg_input"],fg=COLORS["text_main"],insertbackground=COLORS["text_main"],relief="flat")
        e_title.grid(row=1,column=0,sticky="ew",padx=(0,6),ipady=2)
        tk.Label(ff,text="科目",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).grid(row=0,column=1,sticky="w")
        e_subj=tk.Entry(ff,font=("Segoe UI",11),bg=COLORS["bg_input"],fg=COLORS["text_main"],insertbackground=COLORS["text_main"],relief="flat")
        e_subj.grid(row=1,column=1,sticky="ew",padx=3,ipady=2)
        tk.Label(ff,text="截止",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).grid(row=0,column=2,sticky="w")
        e_date=tk.Entry(ff,font=("Segoe UI",11),bg=COLORS["bg_input"],fg=COLORS["text_main"],insertbackground=COLORS["text_main"],relief="flat")
        e_date.insert(0,datetime.now().strftime("%Y-%m-%d")); e_date.grid(row=1,column=2,sticky="ew",padx=3,ipady=2)
        add_btn=tk.Label(ff,text="  添加  ",font=("Segoe UI",10,"bold"),bg=COLORS["purple"],fg="#FFF",padx=16,pady=7,cursor="hand2")
        add_btn.grid(row=1,column=3,padx=(6,0))

        lf=tk.Frame(inner,bg=COLORS["bg_main"]); lf.pack(fill="both",expand=True,padx=28)
        def _refresh():
            for w in lf.winfo_children():w.destroy()
            ts=sorted(self.db.get_tasks(),key=lambda t:(t["status"]!="pending",t["id"]))
            if not ts:tk.Label(lf,text="🎉 暂无任务",font=("Segoe UI",12),bg=COLORS["bg_main"],fg=COLORS["text_sub"]).pack(pady=30)
            else:
                for t in ts:
                    TaskRow(lf,t,
                        lambda tid:(self.db.update_task(tid,status="completed"),_refresh()),
                        lambda tid:(messagebox.askyesno("确认","删除？") and (self.db.delete_task(tid),_refresh()))
                    ).pack(fill="x",pady=1)
        def _add(e=None):
            t=e_title.get().strip()
            if not t:messagebox.showwarning("提示","请输入任务名称！"); return
            self.db.add_task(t,e_subj.get().strip() or "其他",e_date.get().strip()); e_title.delete(0,"end"); e_subj.delete(0,"end"); _refresh()
        add_btn.bind("<Button-1>",_add); e_title.bind("<Return>",_add); _refresh()

    # ═══ 4. AI 助手 ═══
    def _show_ai(self):
        self._clear_main(); _,__,inner=self._scroll(self.main_area)
        tk.Label(inner,text="🤖  AI 智能助手",font=("Segoe UI",20,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(fill="x",padx=28,pady=(18,4))
        tk.Label(inner,text="DeepSeek 驱动 · 输入目标/日记/愿景，AI 自动识别并分析",font=("Segoe UI",10),bg=COLORS["bg_main"],fg=COLORS["text_sub"]).pack(fill="x",padx=28,pady=(0,8))

        # 模式选择
        mode_f=tk.Frame(inner,bg=COLORS["bg_main"]); mode_f.pack(fill="x",padx=28,pady=(0,12))
        self.ai_mode=tk.StringVar(value="plan")
        for text,mode,bg in [("🧠 智能规划","plan",COLORS["bg_card"]),("📝 日记分析","diary",COLORS["bg_card"])]:
            b=tk.Label(mode_f,text=text,font=("Segoe UI",11),bg=bg,fg=COLORS["text_sub"],padx=16,pady=8,cursor="hand2",
                       highlightbackground=COLORS["border"],highlightthickness=1)
            b.pack(side="left",padx=(0,8))
            b.bind("<Button-1>",lambda e,m=mode,b1=b:(self.ai_mode.set(m),[b2.configure(bg=COLORS["bg_card"],fg=COLORS["text_sub"]) for b2 in [b1]+[c for c in mode_f.winfo_children() if c!=b1]], b1.configure(bg=COLORS["purple"],fg="#FFF")))

        # 输入
        in_card=Card(inner,title="✍️  告诉我你的想法",icon=""); in_card.pack(fill="x",padx=28,pady=(0,12))
        self.ai_input=tk.Text(in_card,height=4,font=("Segoe UI",12),bg=COLORS["bg_input"],fg=COLORS["text_main"],
                              insertbackground=COLORS["text_main"],relief="flat",padx=12,pady=12,wrap="word")
        self.ai_input.pack(fill="x")
        go_f=tk.Frame(in_card,bg=COLORS["bg_card"]); go_f.pack(fill="x",pady=(12,0))
        go_btn=tk.Label(go_f,text="🤖  AI 分析",font=("Segoe UI",12,"bold"),bg=COLORS["purple"],fg="#FFF",padx=20,pady=10,cursor="hand2")
        go_btn.pack(side="right")
        go_btn.bind("<Button-1>",lambda e:self._run_ai())
        self.ai_status=tk.Label(go_f,text="",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"])
        self.ai_status.pack(side="left",pady=(4,0))

        # 快捷入口
        tips=tk.Frame(inner,bg=COLORS["bg_main"]); tips.pack(fill="x",padx=28,pady=(0,8))
        for tip in ["6月30号计组考试，周一复习课本，周二周三做真题"]:
            t=tk.Label(tips,text=f"💡 试试：{tip}",font=("Segoe UI",9),bg=COLORS["bg_main"],fg=COLORS["text_muted"],cursor="hand2")
            t.pack(anchor="w"); t.bind("<Button-1>",lambda e,tx=tip:(self.ai_input.delete("1.0","end"),self.ai_input.insert("1.0",tx)))

        # 结果
        self.ai_result=tk.Frame(inner,bg=COLORS["bg_main"])
        self.ai_result.pack(fill="both",padx=28)

    def _run_ai(self):
        if self.ai_loading: return
        text=self.ai_input.get("1.0","end").strip()
        if not text:messagebox.showwarning("提示","请先输入内容！"); return
        if not self.api_key:self._prompt_api_key(); return
        if not self.api_key:return

        self.ai_loading=True; mode=self.ai_mode.get()
        self.ai_status.config(text="⏳ AI 分析中...")
        for w in self.ai_result.winfo_children():w.destroy()

        def _work():
            result=AIClient.ask(mode,text,self.api_key)
            self.win.after(0,lambda:self._show_ai_result(mode,result,text))

        threading.Thread(target=_work,daemon=True).start()

    def _show_ai_result(self,mode,result,raw_text):
        self.ai_loading=False; self.ai_status.config(text="")
        if "error" in result:
            messagebox.showerror("AI 错误",result["error"]); return

        # 清除旧结果
        for w in self.ai_result.winfo_children():w.destroy()

        if mode=="plan":
            # 规划结果
            card=Card(self.ai_result,title="📋  智能规划结果",icon=""); card.pack(fill="x",pady=(6,10))
            info_f=tk.Frame(card,bg=COLORS["bg_card"]); info_f.pack(fill="x",pady=(0,10))
            items=[("📌 任务",result.get("title","")),("📅 截止",result.get("deadline","")),
                   ("⏱ 工时",f"{result.get('hours',0)}小时"),("🏷️ 类型",result.get("type",""))]
            for i,(lb,vl) in enumerate(items):
                if vl:tk.Label(info_f,text=f"{lb}：{vl}",font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_main"]).grid(row=i//2,column=i%2,sticky="w",padx=4,pady=2)

            plan=result.get("plan",[])
            if plan:
                plan_card=Card(self.ai_result,title=f"📅  每日计划（共{len(plan)}天）",icon=""); plan_card.pack(fill="x",pady=(4,8))
                for item in plan:
                    r=tk.Frame(plan_card,bg=COLORS["bg_card"]); r.pack(fill="x",pady=2)
                    d=item.get("date",""); wd=""
                    try:wd=WEEKDAYS_CN[datetime.strptime(d,"%Y-%m-%d").weekday()]
                    except:pass
                    tk.Label(r,text=f"📅 {d} {wd}",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"],width=22,anchor="w").pack(side="left")
                    tk.Label(r,text=f"▎{item.get('title','')}",font=("Segoe UI",10,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"],anchor="w").pack(side="left",fill="x",expand=True)
                    h=item.get("hours",0)
                    if h:tk.Label(r,text=f"⏱ {h}h",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(side="right")
                    nt=item.get("note","")
                    if nt:tk.Label(r,text=f"💡 {nt}",font=("Segoe UI",8),bg=COLORS["bg_card"],fg=COLORS["text_muted"]).pack(side="right",padx=8)

                import_btn=tk.Label(plan_card,text="✅  一键导入到任务列表",font=("Segoe UI",11,"bold"),bg=COLORS["green"],fg="#FFF",padx=20,pady=10,cursor="hand2")
                import_btn.pack(pady=(12,0))
                def _imp():
                    tl=[{"title":it["title"],"subject":result.get("title",""),"deadline":result.get("deadline",""),"plan_date":it["date"],"hours":it.get("hours",0)} for it in plan]
                    self.db.add_tasks_batch(tl); messagebox.showinfo("导入成功",f"已添加 {len(tl)} 条计划！")
                import_btn.bind("<Button-1>",lambda e:_imp())

            adv=result.get("advice","")
            if adv:
                ac=Card(self.ai_result,title="💡  AI 建议",icon=""); ac.pack(fill="x",pady=(4,10))
                tk.Label(ac,text=adv,font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_main"],wraplength=1200).pack(anchor="w")

        elif mode=="diary":
            # 日记分析
            card=Card(self.ai_result,title="📊  日记分析",icon=""); card.pack(fill="x",pady=(6,10))

            # 情绪
            mood=result.get("mood",{})
            me={"happy":"😊","tired":"😫","anxious":"😰","sad":"😢","calm":"😌","excited":"🤩","bored":"😐"}.get(mood.get("primary",""),"😶")
            mr=tk.Frame(card,bg=COLORS["bg_card"]); mr.pack(fill="x",pady=4)
            tk.Label(mr,text=f"{me} 情绪",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"],width=12,anchor="w").pack(side="left")
            sc=mood.get("score",5)
            bar=tk.Frame(mr,bg=COLORS["bg_input"],height=18); bar.pack(side="left",fill="x",expand=True,padx=8)
            tk.Frame(bar,bg=COLORS["green"] if sc>=6 else COLORS["orange"],width=sc*30,height=18).place(x=0,y=0,width=sc*30,height=18)
            tk.Label(mr,text=f"{sc}/10",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(side="right")

            # 睡眠
            sleep=result.get("sleep",{})
            si={"good":"😴💤","ok":"😴","bad":"😫⚠️","unknown":"❓"}.get(sleep.get("quality",""),"❓")
            sr=tk.Frame(card,bg=COLORS["bg_card"]); sr.pack(fill="x",pady=4)
            tk.Label(sr,text=f"{si} 睡眠",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"],width=12,anchor="w").pack(side="left")
            tk.Label(sr,text=f"{sleep.get('hours',0)}小时 · {sleep.get('quality','')}",font=("Segoe UI",11),bg=COLORS["bg_card"],fg=COLORS["text_sub"]).pack(side="left")

            # 高亮/低谷
            for label,items,color in [("✨ 亮点",result.get("highlights",[]),COLORS["green"]),("💔 低谷",result.get("lowlights",[]),COLORS["red"])]:
                if items:
                    fr=tk.Frame(card,bg=COLORS["bg_card"]); fr.pack(fill="x",pady=2)
                    tk.Label(fr,text=f"{label}",font=("Segoe UI",10,"bold"),bg=COLORS["bg_card"],fg=color,width=12,anchor="w").pack(side="left",anchor="n")
                    tf2=tk.Frame(fr,bg=COLORS["bg_card"]); tf2.pack(side="left",fill="x",expand=True)
                    for it in items:tk.Label(tf2,text=f"• {it}",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"],anchor="w").pack(anchor="w")

            # AI 回复
            reply=result.get("reply","")
            if reply:
                rc=Card(self.ai_result,title="💬  AI 对你说",icon=""); rc.pack(fill="x",pady=(8,10))
                tk.Label(rc,text=reply,font=("Segoe UI",11),bg=COLORS["bg_card"],fg=COLORS["purple"],wraplength=1200).pack(anchor="w")

            # 建议
            sugs=result.get("suggestions",[])
            if sugs:
                sc2=Card(self.ai_result,title="💡  建议",icon=""); sc2.pack(fill="x",pady=(4,10))
                for s in sugs:tk.Label(sc2,text=f"• {s}",font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_main"],wraplength=1200,anchor="w").pack(anchor="w",pady=2)

            # 保存
            self.db.add_diary(raw_text,result)
            save_btn=tk.Label(self.ai_result,text="✅  日记已自动保存",font=("Segoe UI",10),bg=COLORS["bg_main"],fg=COLORS["green"])
            save_btn.pack(pady=(4,10))

        self.ai_input.delete("1.0","end")

    # ═══ 5. 人生愿景 ═══
    def _show_vision(self):
        self._clear_main(); _,__,inner=self._scroll(self.main_area)
        tk.Label(inner,text="🌟  人生愿景",font=("Segoe UI",20,"bold"),bg=COLORS["bg_main"],fg=COLORS["text_main"]).pack(fill="x",padx=28,pady=(18,4))
        tk.Label(inner,text="记录你想成为的样子，AI 帮你剖析自己，找到成长的路径",font=("Segoe UI",10),bg=COLORS["bg_main"],fg=COLORS["text_sub"]).pack(fill="x",padx=28,pady=(0,14))

        # 输入区
        in_card=Card(inner,title="✍️  写下你的人生愿景",icon=""); in_card.pack(fill="x",padx=28,pady=(0,12))
        tk.Label(in_card,text="例如：我想成为一个能用技术解决实际问题的工程师，保持阅读和运动的习惯，30岁前有自己的团队",
                 font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"]).pack(anchor="w",pady=(0,8))
        self.vision_input=tk.Text(in_card,height=3,font=("Segoe UI",12),bg=COLORS["bg_input"],fg=COLORS["text_main"],
                                  insertbackground=COLORS["text_main"],relief="flat",padx=12,pady=12,wrap="word")
        self.vision_input.pack(fill="x")
        go_f=tk.Frame(in_card,bg=COLORS["bg_card"]); go_f.pack(fill="x",pady=(10,0))
        self.vision_status=tk.Label(go_f,text="",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_muted"])
        self.vision_status.pack(side="left",pady=(4,0))
        go_btn=tk.Label(go_f,text="🤖  AI 深度分析",font=("Segoe UI",12,"bold"),bg=COLORS["purple"],fg="#FFF",padx=20,pady=10,cursor="hand2")
        go_btn.pack(side="right")
        go_btn.bind("<Button-1>",lambda e:self._run_vision())

        # 结果
        self.vision_result=tk.Frame(inner,bg=COLORS["bg_main"])
        self.vision_result.pack(fill="both",padx=28)

        # 历史愿景时间线
        visions=self.db.get_visions()
        if visions:
            tc=Card(inner,title="📜  愿景时间线",icon=""); tc.pack(fill="x",padx=28,pady=(12,20))
            for v in visions[:5]:
                a=v.get("analysis",{})
                r=tk.Frame(tc,bg=COLORS["bg_card"]); r.pack(fill="x",pady=3)
                tk.Label(r,text=v.get("date",""),font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["text_sub"],width=18,anchor="w").pack(side="left")
                themes=a.get("core_themes","") if isinstance(a,dict) else ""
                if themes:tk.Label(r,text=" · ".join(themes[:3]),font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["purple"],anchor="w").pack(side="left",fill="x",expand=True)
                tk.Label(r,text="🔍 详情",font=("Segoe UI",9),bg=COLORS["bg_card"],fg=COLORS["blue"],cursor="hand2").pack(side="right")
                # 绑定查看详情

    def _run_vision(self):
        text=self.vision_input.get("1.0","end").strip()
        if not text:messagebox.showwarning("提示","请先写下你的愿景！"); return
        if not self.api_key:self._prompt_api_key(); return
        if not self.api_key:return

        self.vision_status.config(text="⏳ AI 深度分析中...")
        for w in self.vision_result.winfo_children():w.destroy()

        def _work():
            result=AIClient.ask("vision",text,self.api_key)
            self.win.after(0,lambda:self._show_vision_result(result,text))

        threading.Thread(target=_work,daemon=True).start()

    def _show_vision_result(self,result,raw):
        self.vision_status.config(text="")
        if "error" in result:
            messagebox.showerror("AI 错误",result["error"]); return

        for w in self.vision_result.winfo_children():w.destroy()

        # 核心主题
        card=Card(self.vision_result,title="🔍  AI 深度剖析",icon=""); card.pack(fill="x",pady=(6,10))
        themes=result.get("core_themes",[])
        if themes:
            tf=tk.Frame(card,bg=COLORS["bg_card"]); tf.pack(fill="x",pady=(0,8))
            for th in themes:
                tk.Label(tf,text=f"  {th}  ",font=("Segoe UI",11),bg=COLORS["bg_accent"],fg=COLORS["purple"],padx=10,pady=4).pack(side="left",padx=4)

        # 职业路径
        cp=result.get("career_path","")
        if cp:
            tk.Label(card,text="💼 职业方向",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(anchor="w",pady=(4,2))
            tk.Label(card,text=cp,font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_sub"],wraplength=1200).pack(anchor="w",pady=(0,8))

        # 习惯差距
        gaps=result.get("habit_gaps",[])
        if gaps:
            tk.Label(card,text="📊  现状 vs 愿景",font=("Segoe UI",11,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(anchor="w",pady=(4,2))
            for g in gaps:
                r=tk.Frame(card,bg=COLORS["bg_card"]); r.pack(fill="x",pady=2)
                tk.Label(r,text=f"🎯 {g.get('goal','')}",font=("Segoe UI",10,"bold"),bg=COLORS["bg_card"],fg=COLORS["text_main"]).pack(side="left")
                tk.Label(r,text=f"→ {g.get('status','')}",font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["orange"]).pack(side="right")

        # 行动建议
        for label,items,icon in [("本周行动",result.get("short_term",[]),"⚡"),("近期里程碑",result.get("mid_term",[]),"🎯")]:
            if items:
                ac=Card(self.vision_result,title=f"{icon}  {label}",icon=""); ac.pack(fill="x",pady=(8,8))
                for it in items:tk.Label(ac,text=f"• {it}",font=("Segoe UI",10),bg=COLORS["bg_card"],fg=COLORS["text_main"],wraplength=1200,anchor="w").pack(anchor="w",pady=2)

        # 激励
        insp=result.get("inspiration","")
        if insp:
            ic=Card(self.vision_result,icon=""); ic.pack(fill="x",pady=(4,12))
            tk.Label(ic,text=f"💫 {insp}",font=("Segoe UI",12,"bold"),bg=COLORS["bg_card"],fg=COLORS["purple"],wraplength=1200).pack()

        # 保存
        self.db.add_vision(raw,result)
        self.vision_input.delete("1.0","end")
        messagebox.showinfo("保存成功","愿景已保存！\n在页面下方可以查看愿景时间线。")

    # ═══ 运行 ═══
    def run(self):
        self.win.mainloop()


if __name__=="__main__":
    App().run()
