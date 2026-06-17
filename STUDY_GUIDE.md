# 🌱 Growth Assistant — 考试复习指南

> DeepSeek AI · Task Management · Timeline · Self-Awareness · Vision  
> 技术栈：Python 3 + tkinter/ttkbootstrap + DeepSeek API + JSON

---

## 目录

1. [具体使用说明](#1-具体使用说明)
2. [项目结构体现](#2-项目结构体现)
3. [重点技术体现](#3-重点技术体现)
4. [代码具体实现](#4-代码具体实现)

---

## 1. 具体使用说明

### 1.1 启动与初始配置

```bash
pip install ttkbootstrap requests    # 安装依赖
python main.py                       # 启动应用
```

首次启动会弹出 API Key 输入框，从 [platform.deepseek.com](https://platform.deepseek.com) 获取。Key 存在 `growth_data.json` 中，仅本地存储。

### 1.2 五大页面功能

#### 📊 Dashboard（仪表盘）

| 区域 | 功能 | 操作 |
|------|------|------|
| 统计卡片 | 总任务/待办/已完成/今日/逾期 | 只读 |
| Weekly Theme | 本周主题（AI 生成） | 自动显示 |
| Focus 区域 | 今日主攻任务 | ▶ 启动计时 / ✓ 一键完成 / ↩ 撤销 |
| Quick Tasks 区域 | 今日碎片任务 | 同上 |
| Latest Vision | 最新愿景快照 | 只读 |

**Pomodoro 计时器**：点击 ▶ 开始计时（秒级计数），再点停止 → 自动保存实际用时到任务。

#### 📋 Timeline（时间线表格）

| 功能 | 操作 |
|------|------|
| 周视图 | ◀ ▶ 切换周，Today 回本周 |
| 心情列 | 显示日记分析的心情 emoji + 分数 |
| 睡眠列 | 显示睡眠时长 + 质量 emoji |
| 截止任务列 | 当天到期的任务列表（最多3条） |
| 日记亮点列 | AI 分析出的 highligts |
| 底部摘要 | 本周日记数、截止任务数、平均心情分 |

#### ✅ Tasks（任务管理）

| 操作 | 方式 |
|------|------|
| 新增任务 | 填写 Task/Subject/Deadline → Add |
| 查看项目详情 | 点 ▼ 展开该 subject 下所有任务 |
| 完成单个任务 | 点 ✓ |
| 删除单个任务 | 点 ✕ |
| 删除整个项目 | 点 🗑（删除该 subject 下全部任务，含拆分的每日子任务） |

#### 🤖 AI Planner（AI 规划器）

| 模式 | 输入 | 做了什么 |
|------|------|----------|
| 🧠 Smart Plan | 手动输入目标描述 | AI 识别任务类型→评估优先级→提取截止日→分3阶段→生成每日 Focus+Quick 计划 |
| 🔄 Replan | 自动读取 pending 任务 | AI 按 subject 重组→重新分阶段→轮转分配 |
| 📝 Diary | 输入日记文字 | AI 分析心情/睡眠/亮点/低谷/社交 → 回复温暖建议 |

**Smart Plan 结果**：点击 "✅ Import All Tasks" 把计划导入任务列表。

#### 🌟 Vision（愿景管理）

| 区域 | 功能 |
|------|------|
| 输入框 | 写愿景 → 🤖 Deep Analysis |
| Timeline 列表 | 历史愿景卡片（日期+预览+核心主题标签） |
| 点击展开 | 完整分析：原文、核心主题、职业路径、习惯差距、本周行动、里程碑、励志语 |
| 删除 | 🗑 Delete this vision |

### 1.3 主题切换

侧边栏底部 🌙 Dark Mode / ☀️ Light Mode 一键切换，所有页面即时生效。

---

## 2. 项目结构体现

### 2.1 模块化设计（从单体到多模块）

```
拆分前：main.py（1214 行单文件）
拆分后：5 文件，职责清晰
```

```
smart-task-manager/
├── main.py          # 入口（5 行）
├── config.py        # 配置层：常量、颜色主题、AI Prompt 模板
├── services.py      # 服务层：AIClient（API 调用）+ DataManager（数据CRUD）
├── widgets.py       # 组件层：Card、StatCard、TaskRow（可复用UI组件）
├── app.py           # 应用层：App 主类（布局/导航/5页面/计时器）
├── growth_data.json # 数据存储
└── requirements.txt # 依赖
```

### 2.2 分层架构

```
┌─────────────────────────────────┐
│  main.py       入口层           │  from app import App
├─────────────────────────────────┤
│  app.py        应用/表现层      │  App 类：5个页面 + 布局 + 导航
├─────────────────────────────────┤
│  widgets.py    组件层           │  Card / StatCard / TaskRow
├─────────────────────────────────┤
│  services.py   业务逻辑层       │  AIClient + DataManager
├─────────────────────────────────┤
│  config.py     配置层           │  COLORS / PROMPTS / 常量
└─────────────────────────────────┘
```

### 2.3 导入依赖关系（无循环依赖）

```
main.py → app.py → config.py
                → services.py → config.py
                → widgets.py  → config.py
```

### 2.4 类设计

| 文件 | 类 | 职责 |
|------|-----|------|
| `services.py` | `AIClient` | DeepSeek API 封装：get_api_key / ask |
| `services.py` | `DataManager` | JSON 数据持久化：CRUD / 统计 / 日记 / 愿景 |
| `widgets.py` | `Card` | 浮动卡片容器（标题 + 分隔线）|
| `widgets.py` | `StatCard` | 统计数值卡片（图标 + 数字 + 标签）|
| `widgets.py` | `TaskRow` | 单任务行（状态点 + 标题 + 星级 + 优先级徽章 + 操作按钮）|
| `app.py` | `App` | 主应用（窗口 / 侧栏 / 5页面 / 计时器 / 主题）|

---

## 3. 重点技术体现

### 3.1 设计模式

#### ① MVC 变体（分层架构）
- **Model**：`DataManager`（数据模型 + 持久化）
- **View**：`Card` / `StatCard` / `TaskRow`（可复用组件）
- **Controller**：`App` 类（页面逻辑 + 事件处理）

#### ② 单一职责原则
每个文件/类只做一件事：配置只管常量，服务只管数据/API，组件只管渲染。

#### ③ 静态方法模式
`AIClient` 使用 `@staticmethod`，无需实例化即可调用：
```python
result = AIClient.ask(mode, text, api_key)
```

### 3.2 核心技术点

#### ① AI 集成（DeepSeek API）
- REST API 调用 (`requests.post`)
- System/User 双角色 prompt 设计
- JSON 解析 + Markdown 清洗（正则去 ``` 标记）
- 异常分类处理：Timeout / ConnectionError / JSONDecodeError
- 多线程异步调用，不阻塞 UI

#### ② 数据持久化（JSON）
- 文件读写 + 异常容错（文件不存在时返回默认值）
- 向后兼容：加载时自动补充缺失字段（`defaults` 字典）
- `ensure_ascii=False` 支持中文

#### ③ GUI 技术（tkinter + ttkbootstrap）
- **ttkbootstrap**：现代化主题（flatly / darkly）
- **Canvas**：自定义状态圆点
- **Scroll**：Canvas + Scrollbar 组合实现可滚动区域
- **MouseWheel**：跨平台滚轮事件绑定
- **lambda 闭包**：事件处理中捕获循环变量
- **动态主题切换**：`config.COLORS.update()` 原地修改字典，所有组件即时生效

#### ④ 计时器实现
- `time.time()` 记录开始时间
- `window.after(1000, callback)` 每秒刷新显示
- 停止时计算 elapsed，保存到 DataManager

#### ⑤ 多线程
- `threading.Thread(target=..., daemon=True)` 异步 AI 调用
- `window.after(0, callback)` 回到主线程更新 UI

### 3.3 数据流

```
用户输入 → App._run_ai()
  → threading.Thread → AIClient.ask()
  → DeepSeek API → JSON 响应
  → window.after(0, ...) → App._show_ai_result()
  → DataManager.add_tasks_batch() → JSON 文件
```

---

## 4. 代码具体实现

### 4.1 入口文件 `main.py`

```python
from app import App

if __name__ == "__main__":
    App().run()
```

**关键点**：`if __name__ == "__main__"` 确保只有直接运行时才启动，import 时不启动。

### 4.2 配置层 `config.py`

```python
# 颜色主题——双层设计
DARK_COLORS = {
    "bg_main": "#000000",    # L0 底层
    "bg_card": "#0F1F3A",    # L1 卡片层
    "bg_input": "#02050C",   # L2 内容层
    "purple": "#A186F1",
    ...
}
LIGHT_COLORS = { ... }
COLORS = LIGHT_COLORS.copy()  # 默认浅色
```

**关键点**：`COLORS` 是可变字典，主题切换时 `.update()` 原地修改 → 所有引用该字典的组件自动更新颜色，无需重新创建对象。

**PROMPTS 字典**：4 个 AI prompt 模板，使用 `{today}` `{tasks_list}` 等占位符，运行时 `.replace()` 替换。

### 4.3 服务层 `services.py`

#### AIClient — API 调用

```python
class AIClient:
    @staticmethod
    def ask(prompt_type, user_text, api_key, system_prompt=None):
        sp = system_prompt or PROMPTS.get(prompt_type, PROMPTS["plan"])
        resp = requests.post(DEEPSEEK_URL, headers={...}, json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": sp},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.7, "max_tokens": 4000,
        }, timeout=30)
        content = resp.json()["choices"][0]["message"]["content"]
        # 清洗 Markdown 代码块
        content = re.sub(r"^```\w*\n?", "", content.strip())
        content = re.sub(r"\n?```$", "", content)
        return json.loads(content)
```

**关键点**：
- `@staticmethod` — 无需实例化
- `system_prompt or PROMPTS.get(...)` — 优先用传入的，否则从配置取
- `timeout=30` — 防止无限等待
- 正则清洗 — DeepSeek 有时返回 ```json ... ``` 包裹的内容
- 异常分层处理

#### DataManager — 数据管理

```python
class DataManager:
    def _load(self):
        defaults = {"importance": 3, "urgency": 3, ...}
        if os.path.exists(self.filename):
            data = json.load(f)
            for t in data.get("tasks", []):
                for k, v in defaults.items():
                    if k not in t: t[k] = v   # 向后兼容
            return data
        return {"tasks": [], "next_id": 1, ...}  # 默认结构
```

**关键点**：
- `_load()` 私有方法 + 异常容错
- 向后兼容：新字段自动补默认值
- 每个写操作后立即 `self.save()` 保证数据不丢失
- `add_tasks_batch()` 批量导入（AI 结果导入用）
- `delete_tasks_by_subject()` 按项目级联删除

### 4.4 组件层 `widgets.py`

#### Card — 浮动卡片

```python
class Card(tk.Frame):
    def __init__(self, parent, title="", icon="", pad=20, **kw):
        super().__init__(parent, bg=COLORS["bg_card"], padx=pad, pady=pad, **kw)
        self.configure(highlightbackground=COLORS["border"], highlightthickness=2)
        if title:
            h = tk.Frame(self, bg=COLORS["bg_card"])
            tk.Label(h, text=f"{icon}  {title}", font=(...)).pack(anchor="w")
            tk.Frame(h, bg=COLORS["divider"], height=1).pack(fill="x")  # 分隔线
```

**关键点**：继承 `tk.Frame`，`highlightthickness=2` 制造浮动边框效果。

#### StatCard — 统计卡片

```python
class StatCard(tk.Frame):
    def set(self, val):
        self.v.config(text=str(val))  # 动态更新数值
```

**关键点**：暴露 `set()` 方法供外部更新。

#### TaskRow — 任务行

状态点逻辑：
```python
if done:        dc = COLORS["green"]
elif is_overdue: dc = COLORS["red"]
elif main_focus: dc = COLORS["blue"]
else:           dc = COLORS["orange"]
```

优先级徽章颜色：
```python
if pr >= 80:    pc = COLORS["red"]
elif pr >= 50:  pc = COLORS["orange"]
else:           pc = COLORS["green"]
```

### 4.5 应用层 `app.py`

#### 初始化流程

```python
class App:
    def __init__(self):
        self.db = DataManager()             # ① 加载数据
        self.win = ttk.Window(themename="flatly")  # ② 创建窗口
        self._build_layout()                # ③ 构建侧栏+主区域
        self._nav_to_page("dashboard")      # ④ 默认进入 Dashboard
        if not self.api_key:
            self.win.after(500, self._prompt_api_key)  # ⑤ 延时弹窗
```

#### 导航系统

```python
def _nav_to_page(self, key):
    self.current_page = key
    for k, b in self.nav_btns.items():
        a = (k == key)
        b.configure(
            bg=COLORS["purple_dark"] if a else COLORS["bg_side"],  # 紫色高亮
            fg="#FFF" if a else COLORS["text_sub"]
        )
    self._clear_main()  # 清空主区域
    routes = {           # 路由字典 → 方法
        "dashboard": self._show_dashboard,
        "timeline":  self._show_timeline,
        "tasks":     self._show_tasks,
        "ai":        self._show_ai,
        "vision":    self._show_vision,
    }
    routes[key]()
```

**关键点**：字典路由映射（比 if-elif 更优雅），先清空再渲染。

#### 主题切换

```python
def _toggle_theme(self):
    self.is_dark = not self.is_dark
    self.win.style.theme_use("darkly" if self.is_dark else "flatly")
    config.COLORS.update(DARK_COLORS if self.is_dark else LIGHT_COLORS)
    # 重建侧栏 + 重渲染当前页面
    self._build_sidebar_content()
    self._nav_to_page(self.current_page)
```

**关键点**：`COLORS.update()` 原地修改 → 所有组件自动感知颜色变化。

#### 计时器

```python
def _start_timer(self, tid, label, act_label=None):
    self.timers[tid] = {"start": time.time(), "label": label, "running": True}
    self._tick_timer(tid)

def _tick_timer(self, tid):
    t = self.timers.get(tid)
    if not t or not t.get("running"): return
    elapsed = int(time.time() - t["start"])
    mins, secs = divmod(elapsed, 60)
    t["label"].config(text=f"⏱ {mins:02d}:{secs:02d}")
    self.win.after(1000, lambda: self._tick_timer(tid))  # 递归每秒刷新

def _stop_timer(self, tid):
    t = self.timers.pop(tid, None)
    elapsed = int(time.time() - t["start"])
    mins = max(1, round(elapsed / 60, 1))
    self.db.add_time(tid, mins)  # 持久化保存
```

**关键点**：`after(1000, callback)` 实现每秒刷新，非阻塞。`divmod` 计算分秒。

#### AI 异步调用

```python
def _run_ai(self):
    self.ai_loading = True        # 防止重复点击
    self.ai_status.config(text="⏳ Analyzing...")

    def _work():
        result = AIClient.ask(call_mode, text, self.api_key, system_prompt=sp)
        self.win.after(0, lambda: self._show_ai_result(mode, result, text))
        # ↑ after(0, ...) 回到主线程更新 UI

    threading.Thread(target=_work, daemon=True).start()
    # ↑ daemon=True: 主线程退出时自动结束
```

**关键点**：`threading.Thread(daemon=True)` 异步执行 + `after(0)` 回到 GUI 主线程。

#### 滚动区域

```python
def _scroll(self, parent):
    cv = tk.Canvas(parent, bg=COLORS["bg_main"], highlightthickness=0)
    sb = ttk.Scrollbar(parent, orient="vertical", command=cv.yview)
    inner = tk.Frame(cv, bg=COLORS["bg_main"])
    cv.create_window((0, 0), window=inner, anchor="nw")
    cv.configure(yscrollcommand=sb.set)

    def _wh(e):
        cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
    inner.bind("<Enter>", lambda e: cv.bind_all("<MouseWheel>", _wh))
    inner.bind("<Leave>", lambda e: cv.unbind_all("<MouseWheel>"))
    return cv, sb, inner
```

**关键点**：Canvas + Scrollbar + inner Frame 组合。`bind_all` + `unbind_all` 只在鼠标进入时绑定滚轮。

#### Timeline 核心实现

```python
# 获取数据
diary_map = self.db.get_diary_map()  # {date: diary_entry}

for i in range(7):
    d = monday + timedelta(days=i)
    ds = d.strftime("%Y-%m-%d")

    # 心情列
    diary_entry = diary_map.get(ds)
    if diary_entry:
        analysis = diary_entry.get("analysis", {})
        mood = analysis.get("mood", {})
        emoji = {"happy": "😊", "tired": "😫", ...}.get(mood["primary"], "😶")
        mood_text = f"{emoji} {score}/10"

    # 截止任务列
    deadline_tasks = self.db.get_deadline_tasks(ds)
    for t in deadline_tasks[:3]:
        tk.Label(task_frame, text=f"● {title}", ...).pack()
```

#### Vision 点击展开

```python
# Timeline 行绑定点击事件
r.bind("<Button-1>", lambda e, v=v: self._show_vision_detail(v))

def _show_vision_detail(self, v):
    # 清空 detail 面板 → 重建完整分析卡片
    for w in self.vision_detail.winfo_children():
        w.destroy()

    a = v.get("analysis", {})
    # 依次渲染：原文 → 核心主题 → 职业路径 → 习惯差距 → 短期行动 → 里程碑 → 励志语
```

### 4.6 lambda 闭包注意事项

```python
# ❌ 错误写法 — 所有按钮绑定到最后一个 tid
for t in tasks:
    btn.bind("<Button-1>", lambda e: do_something(t["id"]))

# ✅ 正确写法 — 默认参数捕获当前值
for t in tasks:
    btn.bind("<Button-1>", lambda e, tid=t["id"]: do_something(tid))
```

---

## 5. 复习自检清单

- [ ] 能画出 5 文件结构和依赖关系
- [ ] 能解释 `COLORS.update()` 如何实现主题切换
- [ ] 能写出 AIClient.ask() 的核心流程
- [ ] 能解释 `DataManager._load()` 的向后兼容设计
- [ ] 能说出 Smart Plan vs Replan 的区别
- [ ] 能解释计时器的 `after(1000)` 递归模式
- [ ] 能解释多线程 + `after(0)` 的异步模式
- [ ] 能解释 `lambda` 闭包中默认参数的必要性
- [ ] 能说出 Card / StatCard / TaskRow 的继承和定制点
- [ ] 能解释 Timeline 如何整合日记分析 + 截止任务
