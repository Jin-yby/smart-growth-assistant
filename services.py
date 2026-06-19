"""
Backend services: AI client (DeepSeek API) and data manager (JSON persistence).
"""

import json
import os
import re
import requests
from datetime import datetime

from config import DATA_FILE, DEEPSEEK_URL, PROMPTS


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
        defaults = {"importance": 3, "urgency": 3, "priority": 50, "task_type": "normal",
                    "weekly_theme": "", "actual_minutes": 0}
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for t in data.get("tasks", []):
                    for k, v in defaults.items():
                        if k not in t:
                            t[k] = v
                # Backward-compat: ensure new fields exist
                if "insights" not in data:
                    data["insights"] = []
                if "discover_last_run" not in data:
                    data["discover_last_run"] = None
                return data
            except Exception:
                pass
        return {"tasks": [], "next_id": 1, "diary": [], "visions": [],
                "insights": [], "discover_last_run": None, "api_key": ""}

    def save(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def set_api_key(self, key):
        self.data["api_key"] = key
        self.save()

    def get_api_key(self):
        return self.data.get("api_key", "")

    # ── Tasks ──────────────────────────────────────────

    def get_tasks(self, date_str=None):
        tasks = self.data.get("tasks", [])
        return [t for t in tasks if t.get("plan_date") == date_str] if date_str else tasks

    def add_task(self, title, subject, deadline, plan_date=None, hours=0,
                 importance=3, urgency=3, priority=50, task_type="normal",
                 weekly_theme="", actual_minutes=0):
        t = {
            "id": self.data["next_id"], "title": title, "subject": subject or "Other",
            "deadline": deadline or "", "plan_date": plan_date or datetime.now().strftime("%Y-%m-%d"),
            "estimated_hours": hours, "status": "pending",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "importance": importance, "urgency": urgency, "priority": priority,
            "task_type": task_type, "weekly_theme": weekly_theme,
            "actual_minutes": actual_minutes,
        }
        self.data["tasks"].append(t)
        self.data["next_id"] += 1
        self.save()
        return t

    def add_time(self, tid, minutes):
        """Accumulate actual focused minutes on a task."""
        for t in self.data["tasks"]:
            if t["id"] == tid:
                t["actual_minutes"] = t.get("actual_minutes", 0) + minutes
                self.save()
                return True
        return False

    def add_tasks_batch(self, items, meta=None):
        for it in items:
            self.add_task(
                it.get("title", ""), it.get("subject", ""), it.get("deadline", ""),
                it.get("plan_date", ""), it.get("hours", 0),
                importance=it.get("importance", meta.get("importance", 3) if meta else 3),
                urgency=it.get("urgency", meta.get("urgency", 3) if meta else 3),
                priority=it.get("priority", meta.get("priority", 50) if meta else 50),
                task_type=it.get("task_type", "normal"),
                weekly_theme=it.get("weekly_theme", meta.get("weekly_theme", "") if meta else ""),
            )

    def update_task(self, tid, **kw):
        for t in self.data["tasks"]:
            if t["id"] == tid:
                t.update(kw)
                self.save()
                return True
        return False

    def delete_task(self, tid):
        self.data["tasks"] = [t for t in self.data["tasks"] if t["id"] != tid]
        self.save()

    def delete_tasks_by_subject(self, subject):
        """Delete all tasks under a given subject (project). Returns count deleted."""
        before = len(self.data["tasks"])
        self.data["tasks"] = [t for t in self.data["tasks"] if t.get("subject", "") != subject]
        after = len(self.data["tasks"])
        self.save()
        return before - after

    def get_stats(self):
        tasks = self.data["tasks"]
        total = len(tasks)
        pending = sum(1 for t in tasks if t["status"] == "pending")
        completed = sum(1 for t in tasks if t["status"] == "completed")
        today = datetime.now().strftime("%Y-%m-%d")
        td = self.get_tasks(today)
        td_done = sum(1 for t in td if t["status"] == "completed")
        return {
            "total": total, "pending": pending, "completed": completed,
            "rate": int(completed / total * 100) if total else 0,
            "today_total": len(td), "today_done": td_done,
        }

    def get_month_tasks(self, y, m):
        """Count tasks by deadline date (for calendar milestone markers)."""
        r = {}
        for t in self.data["tasks"]:
            dl = t.get("deadline", "")
            if dl and dl.startswith(f"{y}-{m:02d}"):
                d = int(dl.split("-")[2])
                r[d] = r.get(d, 0) + 1
        return r

    def get_month_deadline_groups(self, y, m):
        """Return {day: [{title, subject, status}, ...]} for calendar display."""
        from collections import defaultdict
        r = defaultdict(list)
        for t in self.data["tasks"]:
            dl = t.get("deadline", "")
            if dl and dl.startswith(f"{y}-{m:02d}"):
                d = int(dl.split("-")[2])
                r[d].append({
                    "title": t["title"],
                    "subject": t.get("subject", ""),
                    "status": t.get("status", "pending"),
                })
        return dict(r)

    def get_deadline_tasks(self, date_str):
        """Get tasks whose deadline matches this date (big milestones)."""
        return [t for t in self.data.get("tasks", []) if t.get("deadline", "") == date_str]

    def get_weekly_theme(self):
        tasks = self.data.get("tasks", [])
        for t in sorted(tasks, key=lambda x: x.get("created", ""), reverse=True):
            wt = t.get("weekly_theme", "")
            if wt:
                return wt
        return ""

    def get_pending_tasks(self):
        return [t for t in self.data.get("tasks", []) if t["status"] == "pending"]

    # ── Diary ─────────────────────────────────────────

    def add_diary(self, text, analysis):
        e = {"date": datetime.now().strftime("%Y-%m-%d"), "raw": text, "analysis": analysis}
        self.data["diary"].append(e)
        self.save()

    def get_diary(self, limit=30):
        return sorted(self.data.get("diary", []), key=lambda x: x.get("date", ""), reverse=True)[:limit]

    def get_diary_map(self):
        """Return {date_str: diary_entry} for O(1) lookup by date."""
        return {d["date"]: d for d in self.data.get("diary", [])}

    # ── Discover / Insights ──────────────────────────

    def add_insight(self, insight_data):
        """Create a new insight (hypothesis) from AI analysis."""
        existing = self.data.get("insights", [])
        iid = max([i.get("id", 0) for i in existing], default=0) + 1
        insight = {
            "id": iid,
            "type": insight_data.get("type", "hypothesis"),
            "title": insight_data.get("title", ""),
            "hypothesis": insight_data.get("hypothesis", ""),
            "evidence": insight_data.get("evidence", []),
            "confidence": insight_data.get("confidence", 0.5),
            "status": insight_data.get("status", "pending"),
            "question": insight_data.get("question", ""),
            "user_answer": insight_data.get("user_answer", None),
            "created": datetime.now().strftime("%Y-%m-%d"),
            "category": insight_data.get("category", "general"),
            "confirmed_at": insight_data.get("confirmed_at", None),
            "follow_up": insight_data.get("follow_up", None),
        }
        self.data.setdefault("insights", []).append(insight)
        self.save()
        return insight

    def update_insight(self, iid, **kw):
        """Partial update an insight by id."""
        for i in self.data.get("insights", []):
            if i["id"] == iid:
                i.update(kw)
                self.save()
                return True
        return False

    def get_insights(self, status=None):
        """Get all insights, optionally filtered by status."""
        insights = self.data.get("insights", [])
        if status:
            return [i for i in insights if i.get("status") == status]
        return sorted(insights, key=lambda x: x.get("id", 0), reverse=True)

    def get_pending_insight_count(self):
        """Return count of pending (unanswered) insights."""
        return len(self.get_insights("pending"))

    def set_discover_last_run(self, dt=None):
        self.data["discover_last_run"] = dt or datetime.now().strftime("%Y-%m-%d %H:%M")
        self.save()

    def get_discover_last_run(self):
        return self.data.get("discover_last_run")

    def aggregate_for_discover(self):
        """Aggregate user data into a structured summary for AI pattern analysis."""
        tasks = self.data.get("tasks", [])
        diaries = self.data.get("diary", [])
        from collections import defaultdict

        # ── Task completion stats ──
        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t["status"] == "completed")
        pending = total_tasks - completed

        # Completion by day-of-week
        dow_comp = defaultdict(lambda: {"total": 0, "done": 0})
        for t in tasks:
            pd_date = t.get("plan_date", "")
            if pd_date:
                try:
                    dow = datetime.strptime(pd_date, "%Y-%m-%d").strftime("%A")
                    dow_comp[dow]["total"] += 1
                    if t["status"] == "completed":
                        dow_comp[dow]["done"] += 1
                except Exception:
                    pass

        # Completion by subject
        subj_stats = defaultdict(lambda: {"total": 0, "done": 0})
        for t in tasks:
            subj = t.get("subject", "Other")
            subj_stats[subj]["total"] += 1
            if t["status"] == "completed":
                subj_stats[subj]["done"] += 1

        # Completion by priority band
        pbands = {"high (>=80)": {"total": 0, "done": 0},
                  "medium (50-79)": {"total": 0, "done": 0},
                  "low (<50)": {"total": 0, "done": 0}}
        for t in tasks:
            p = t.get("priority", 50)
            band = "high (>=80)" if p >= 80 else ("medium (50-79)" if p >= 50 else "low (<50)")
            pbands[band]["total"] += 1
            if t["status"] == "completed":
                pbands[band]["done"] += 1

        # Deadline adherence
        on_time = late = no_deadline = 0
        for t in tasks:
            dl = t.get("deadline", "")
            if not dl:
                no_deadline += 1
                continue
            try:
                if t["status"] == "completed":
                    created = t.get("created", "")[:10]
                    if created and created <= dl:
                        on_time += 1
                    else:
                        late += 1
            except Exception:
                pass

        # ── Diary trends (last 14 days) ──
        mood_trend = []
        sleep_trend = []
        for d in sorted(diaries, key=lambda x: x.get("date", ""))[-14:]:
            a = d.get("analysis", {})
            if isinstance(a, dict):
                mood = a.get("mood", {})
                if isinstance(mood, dict):
                    mood_trend.append({
                        "date": d["date"],
                        "score": mood.get("score"),
                        "primary": mood.get("primary"),
                    })
                slp = a.get("sleep", {})
                if isinstance(slp, dict):
                    sleep_trend.append({
                        "date": d["date"],
                        "hours": slp.get("hours"),
                        "quality": slp.get("quality"),
                    })

        # ── Time estimation accuracy ──
        est_vs_actual = []
        for t in tasks:
            est = t.get("estimated_hours", 0)
            act = t.get("actual_minutes", 0) / 60.0
            if est > 0:
                est_vs_actual.append({
                    "title": t["title"],
                    "estimated_h": est,
                    "actual_h": round(act, 1),
                })

        # ── Recent highlights ──
        recent_highlights = []
        for d in diaries[-7:]:
            a = d.get("analysis", {})
            if isinstance(a, dict):
                for h in a.get("highlights", []):
                    recent_highlights.append(f"{d['date']}: {h}")

        return {
            "total_tasks": total_tasks,
            "completed": completed,
            "pending": pending,
            "completion_rate": f"{int(completed / total_tasks * 100)}%" if total_tasks else "N/A",
            "day_of_week_completion": dict(dow_comp),
            "subject_stats": dict(subj_stats),
            "priority_band_completion": dict(pbands),
            "deadline_adherence": {"on_time": on_time, "late": late, "no_deadline": no_deadline},
            "mood_trend_last_14_days": mood_trend,
            "sleep_trend_last_14_days": sleep_trend,
            "time_estimation_samples": est_vs_actual[:10],
            "total_diary_entries": len(diaries),
            "recent_diary_highlights": recent_highlights[:10],
        }

    # ── Vision ────────────────────────────────────────

    def add_vision(self, text, analysis):
        v = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "raw": text, "analysis": analysis}
        self.data["visions"].append(v)
        self.save()

    def get_visions(self):
        return sorted(self.data.get("visions", []), key=lambda x: x.get("date", ""), reverse=True)
