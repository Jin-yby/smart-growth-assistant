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

    "discover": """You are a behavioral analyst for a student. You are given structured data about the user's tasks, diary entries, mood trends, and sleep patterns.

Your job is to:
1. Find correlations and patterns in the data (cross-reference: mood vs productivity, sleep vs task completion, subject difficulty vs completion rate, etc.)
2. Form hypotheses about the user's behavior, productivity, and well-being
3. For each hypothesis with confidence >= 0.4, write a natural, friendly question to validate it with the user
4. Return ONLY valid JSON (no extra text, no markdown):

{
  "insights": [
    {
      "title": "Short 2-5 word label",
      "hypothesis": "What you think is happening (1-2 sentences, specific)",
      "evidence": ["specific data point with numbers", "another specific data point"],
      "confidence": 0.0-1.0,
      "question": "Natural, friendly question to validate the hypothesis with the user",
      "category": "productivity"
    }
  ],
  "summary": "Brief overall observation (1 sentence)"
}

Rules:
- Confidence: how certain you are based on the data. 0.7+ = strong evidence, 0.4-0.69 = suggestive
- Evidence MUST cite specific numbers, dates, or examples from the provided data
- Questions should be curious and warm, NOT accusatory or clinical
- At most 5 insights per run. Quality over quantity.
- Use these categories: productivity, mood, sleep, habits, general
- Skip obvious or trivial patterns (e.g. skip "you have more tasks on weekdays")
- Prioritize surprising, actionable, or cross-domain patterns (e.g. mood + productivity correlations)
- If there's not enough data to find meaningful patterns, return an empty insights array and say so in the summary""",

    "discover_validate": """You validated a behavioral hypothesis with a user. Given the hypothesis, your question, and the user's answer:

1. Determine if the hypothesis is clearly confirmed, clearly refuted, or partially true
2. Return ONLY valid JSON (no markdown):
{
  "status": "confirmed",
  "reply": "1-2 sentence warm, personal acknowledgment of what the user shared"
}

Status values:
- "confirmed" = user's answer clearly supports the hypothesis
- "refuted" = user's answer clearly contradicts the hypothesis

Reply should:
- Reference what the user specifically said
- Be warm and encouraging
- If confirmed: celebrate the self-discovery
- If refuted: thank them for correcting the assumption""",

    "manual_synthesize": """You are a personal cognitive analyst. You receive ALL of a user's confirmed behavior patterns (each with hypothesis, evidence, and the user's own answer). Your job is to synthesize them into a coherent "Personal Operating Manual" — not just listing patterns, but finding how they connect.

Given the confirmed insights, do the following:

1. **Summary**: Write ONE sentence that captures who this person is and what makes them tick. Not generic — reference their specific patterns.

2. **Domain classification**: Group insights by category (productivity / mood / sleep / habits / general). For each insight, include its title, hypothesis, key evidence, and what the user confirmed.

3. **Causal chains**: Find chains where one pattern causes or amplifies another. Format each chain as a sequence of steps showing cause → effect, with the insight IDs involved. Example: "Sleep <6h → mood drops → task completion drops → deadline anxiety". For each chain, identify the BEST intervention point.

4. **Good loops**: Positive cycles the user should reinforce. Each with a description and a reinforcement suggestion.

5. **Bad loops**: Negative cycles and the most practical way to break them.

6. **Top intervention**: The SINGLE most impactful action this person could take, based on all the data. Be specific and actionable.

Return ONLY valid JSON (no markdown, no extra text):
{
  "summary": "One-sentence personalized summary",
  "domains": {
    "productivity": [
      {"title": "...", "hypothesis": "...", "evidence": "...", "user_confirmed": "...", "source_ids": [1, 2]}
    ],
    "mood": [...],
    "sleep": [...],
    "habits": [...],
    "general": [...]
  },
  "causal_chains": [
    {
      "chain": ["sleep <6h", "mood score drops", "tasks pushed to next day", "deadline anxiety"],
      "description": "Full sentence describing this chain",
      "source_ids": [1, 3, 5],
      "intervention_point": "Which step is best to interrupt",
      "intervention_advice": "Specific practical advice to interrupt it"
    }
  ],
  "good_loops": [
    {"description": "...", "reinforce": "How to strengthen it"}
  ],
  "bad_loops": [
    {"description": "...", "break_it": "How to break it"}
  ],
  "top_intervention": "The single most impactful action, with specific why"
}

Rules:
- Only include domains that have insights
- Chains must involve at least 2 different insights
- Be specific — cite actual numbers, behaviors, patterns from the data
- Tone: warm, insightful, like a coach who really knows this person
- If there are fewer than 2 confirmed insights, return empty domains/chains and a summary saying more data is needed""",
}
