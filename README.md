# 🌱 Growth Assistant — AI-Powered Self-Management Tool

**Student Planner** with DeepSeek AI integration. Task management, calendar timeline, diary analysis, and life vision — all in one desktop app.

## Screenshots

```
📊  Dashboard   — Today's tasks, Pomodoro timer, stats overview
📋  Timeline    — Weekly table: mood, sleep, deadline tasks, diary highlights
✅  Tasks       — Project-based task management with batch operations
🤖  AI Planner  — Smart Plan / Replan / Diary analysis powered by DeepSeek
🌟  Vision      — Life vision tracking with AI deep analysis
```

## Features

- **📊 Dashboard** — Daily overview with stats, weekly theme, Focus/Quick task blocks, built-in Pomodoro timer (▶ count-up), one-click task completion
- **📋 Timeline** — Weekly table calendar combining diary analysis (mood/sleep) + deadline tasks + highlights in one view
- **✅ Tasks** — Add/edit/delete tasks grouped by subject. Delete entire project with all subtasks. Priority/importance/urgency tracking
- **🤖 AI Planner** — Three modes:
  - *Smart Plan* — Describe a goal, AI creates a daily study plan with phase scheduling
  - *Replan* — AI reorganizes pending tasks into a new schedule
  - *Diary* — AI analyzes diary entries for mood, sleep, highlights, and suggestions
- **🌟 Vision** — Write life goals, AI identifies core themes, career path, habit gaps, short/mid-term actions. Click any entry to see full analysis
- **🌙 Dark/Light Mode** — Toggle in sidebar

## Tech Stack

| Layer | Technology |
|-------|-----------|
| GUI | tkinter + ttkbootstrap |
| AI | DeepSeek API (deepseek-chat) |
| Data | Local JSON file (`growth_data.json`) |
| Language | Python 3 |

## Project Structure

```
smart-task-manager/
├── main.py          # Entry point
├── config.py        # Constants, color themes (light/dark), AI prompts
├── services.py      # AIClient (DeepSeek API) + DataManager (JSON CRUD)
├── widgets.py       # Reusable UI: Card, StatCard, TaskRow
├── app.py           # App class — layout, nav, all 5 pages, timer
├── growth_data.json # Local data storage (auto-created)
└── requirements.txt
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Get DeepSeek API Key
#    Sign up at https://platform.deepseek.com → API Keys → Create

# 3. Run
python main.py

# 4. On first launch, enter your API Key when prompted
#    (stored locally in growth_data.json, never uploaded)
```

## Dependencies

```
ttkbootstrap    # Modern themed tkinter widgets
requests        # HTTP client for DeepSeek API
```

## Data

All data is stored locally in `growth_data.json`:
- Tasks (with deadlines, priorities, Pomodoro time tracking)
- Diary entries + AI analysis results
- Vision entries + AI analysis results
- API Key (local only)

## License

MIT
