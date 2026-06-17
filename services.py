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
                return data
            except Exception:
                pass
        return {"tasks": [], "next_id": 1, "diary": [], "visions": [], "api_key": ""}

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

    # ── Vision ────────────────────────────────────────

    def add_vision(self, text, analysis):
        v = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "raw": text, "analysis": analysis}
        self.data["visions"].append(v)
        self.save()

    def get_visions(self):
        return sorted(self.data.get("visions", []), key=lambda x: x.get("date", ""), reverse=True)
