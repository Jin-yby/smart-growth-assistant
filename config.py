"""
🌱 Student Growth Assistant — AI-Powered Self-Management Tool
=============================================================
DeepSeek AI · Task Management · Calendar · Self-Awareness · Vision

Run: python main.py
Deps: pip install ttkbootstrap requests
"""

# ============================================================
#  App Configuration
# ============================================================
APP_TITLE = "🌱 Growth Assistant"
WINDOW_WIDTH, WINDOW_HEIGHT = 2400, 1600
MIN_WIDTH, MIN_HEIGHT = 2000, 1400
DATA_FILE = "growth_data.json"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SIDEBAR_W = 380

WEEKDAYS_CN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ============================================================
#  Color Themes
# ============================================================

DARK_COLORS = {
    # 3-layer depth: black base → blue cards → black content + white text
    "bg_main": "#000000",      # L0: pure black — deepest
    "bg_side": "#040810",      #    sidebar — near black
    "bg_card": "#0F1F3A",      # L1: DEEP BLUE card — data block divider
    "bg_input": "#02050C",     # L2: near-black content area inside blue card
    "bg_hover": "#132840",     #    hover on blue
    "bg_accent": "#16102E",    #    purple-tinted accent
    "purple": "#A186F1", "purple_dark": "#7C5EE0", "green": "#34D399",
    "orange": "#FBBF24", "red": "#F87171", "blue": "#60A5FA", "teal": "#2DD4BF",
    "text_main": "#E4E8F4", "text_sub": "#9098B0", "text_muted": "#5E667E",
    "border": "#1D3050", "divider": "#132038",  # blue-tinted edges
}

LIGHT_COLORS = {
    # Clean palette — soft purple accent
    "bg_main": "#FFFFFF", "bg_side": "#FFFFFF", "bg_card": "#FFFFFF",
    "bg_input": "#F9FAFB", "bg_hover": "#F6F8FA", "bg_accent": "#F5F0FF",
    "purple": "#A186F1", "purple_dark": "#7C5EE0", "green": "#10B981",
    "orange": "#F59E0B", "red": "#EF4444", "blue": "#3B82F6", "teal": "#14B8A6",
    "text_main": "#1A1A1A", "text_sub": "#6B7280", "text_muted": "#9CA3AF",
    "border": "#EBEBEB", "divider": "#F5F5F5",
}

COLORS = LIGHT_COLORS.copy()

# ============================================================
#  AI Prompts
# ============================================================

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
