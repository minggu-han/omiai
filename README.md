# 💬 AI 聊天顾问系统

基于 **LangGraph** 多智能体协作系统，帮助用户分析聊天语境、生成个性化回复，并通过**人工审核机制**确保回复质量。

> 分析 → 生成 → 审核 → 润色 → 模拟，五步完成每次回复。

## 🛠 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Pinia |
| 后端 | FastAPI + LangGraph |
| 大模型 | OpenAI GPT-4 |
| 认证 | JWT + bcrypt |
| 状态持久化 | LangGraph AsyncPostgresSaver（PostgreSQL） |
| 数据库 | PostgreSQL + SQLAlchemy 2.0 async |

## 📁 项目结构

```
omiai/
├── backend/                  # FastAPI 后端
│   ├── main.py               # 应用入口 + API 路由（含登录/注册）
│   ├── run.py                # Windows 兼容启动脚本
│   ├── requirements.txt      # Python 依赖
│   ├── .env                  # 环境变量（API Key + DB + JWT）
│   └── src/
│       ├── state.py          # 状态类型定义
│       ├── llm_client.py     # LLM 客户端封装
│       ├── prompts.py        # Prompt 模板
│       ├── session.py        # 会话管理
│       ├── graph.py          # LangGraph 图定义
│       ├── database.py       # 异步数据库引擎
│       ├── models.py         # ORM 模型（omiai_users / omiai_sessions）
│       ├── auth.py           # JWT 认证 + 密码哈希
│       └── nodes/            # 4 个 AI 节点
│           ├── analyzer.py   # 意图情绪分析
│           ├── generator.py  # 候选回复生成
│           ├── refiner.py    # 回复润色
│           └── simulator.py  # 对方反应模拟
│
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── App.vue           # 主组件（含登录门控 + 存档列表）
│   │   ├── api/index.js      # API 客户端（自动附带 JWT）
│   │   ├── stores/
│   │   │   ├── session.js    # 会话状态管理
│   │   │   └── auth.js       # 认证状态管理
│   │   └── components/       # 6 个页面组件
│   │       ├── LoginForm.vue     # 登录/注册页
│   │       ├── SessionList.vue   # 历史存档列表
│   │       ├── ChatInput.vue
│   │       ├── AnalysisReport.vue
│   │       ├── CandidateReview.vue
│   │       └── FinalResult.vue
│   └── vite.config.js
│
└── project-requirement.md    # 原始需求文档
```

## 🚀 快速启动

### 0. 前置条件

- Python 3.10+
- Node.js 18+
- PostgreSQL 数据库（已有或新建）

### 1. 后端

```bash
cd backend

# 创建虚拟环境并安装依赖
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt

# 编辑 .env 填入配置
# OPENAI_API_KEY=sk-xxx
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
# JWT_SECRET=your-random-secret

# Windows 启动（推荐）
python run.py

# macOS / Linux 启动
uvicorn main:app --reload --port 8000
```

> **Windows 注意**：必须使用 `python run.py` 而非直接 `uvicorn`，否则 psycopg 异步事件循环会报错。

数据库表会在应用首次启动时自动创建（`omiai_users`、`omiai_sessions` 以及 LangGraph 的 checkpoint 表）。

API 文档自动生成：http://localhost:8000/docs

### 2. 前端

```bash
cd frontend

npm install
npm run dev                  # → http://localhost:5173
```

前端已配置 Vite 代理，`/api` 请求自动转发到后端。

### 3. 首次使用

1. 浏览器打开 http://localhost:5173
2. 在登录页点击「注册」，创建账号
3. 登录后即可使用全部功能

## 🔄 工作流

```
聊天记录输入
    ↓
① 意图分析 ──→ 情绪分数 · 对方意图 · 危险等级
    ↓
② 策略生成 ──→ 3 种风格回复（幽默 / 温暖 / 推拉）
    ↓
③ ⚠️ 人工审核 ← 在此中断，等待用户操作
    ↓
    ├── 接受 → ④ 润色优化 → ⑤ 模拟推演 → 输出
    ├── 修改 → ④ 润色优化 → ⑤ 模拟推演 → 输出
    └── 驳回 → 回到 ②（最多 3 次，超限强制退出）
```

## 🛑 中断机制详解

整个流程的核心是 LangGraph 的 **interrupt + checkpointer** 机制——图跑到特定节点前自动暂停，等用户做完决定后从中断点继续执行。

### 中断在哪里触发？

图编译时通过 `interrupt_before` 声明中断点（`backend/src/graph.py:106-109`）：

```python
checkpointer = MemorySaver()
return graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_review"],  # ← 在 human_review 节点之前暂停
)
```

执行流程：

```
START → analyzer → generator → ⏸️ interrupt_before=["human_review"] ⏸️
                                    │
                      graph.stream() 在这里阻塞并返回
                      前端拿到 candidates 展示给用户
                                    │
                      POST /api/review 提交用户决定
                                    ↓
                            human_review（透传节点）
                                    │
                      route_after_review() 条件路由
                          ┌─ accept  ──→ refiner → simulator → END
                          ├─ modify  ──→ refiner → simulator → END
                          └─ reject  ──→ retry<3? → generator（重新走一轮）
                                          retry≥3? → END（强制退出）
```

### API 如何配合？

整个交互分 **两步 API 调用**，对应图的「暂停」和「恢复」：

#### 第一步：`POST /api/analyze`（触发中断）

`backend/main.py:113-131`：

```python
# 运行图 —— 跑到 human_review 之前自动停下
events = list(_graph.stream(initial_state, config))

# 读取中断后的快照
snapshot = _graph.get_state(config)
state_dict = dict(snapshot.values)
is_interrupted = snapshot.next is not None   # next 非空 = 图在等人
```

返回的 `state` 中已经包含 `analysis_report` 和 `candidates`（3 条候选回复），`is_interrupted: true` 告诉前端「等用户做决定」。

#### 第二步：`POST /api/review`（恢复执行）

`backend/main.py:134-173`：

```python
# 1. 把用户的选择写入状态
update = {
    "human_decision": req.decision,       # accept / modify / reject
    "human_selected_index": req.selected_index,
    "human_modified_text": req.modified_text,  # modify 时才有
}
_graph.update_state(config, update)

# 2. 从中断点继续执行（传入 None 表示接着跑）
events = list(_graph.stream(None, config))
```

`update_state` 把用户的决策注入到当前 thread 的状态中，然后 `stream(None, config)` 从 `human_review` 节点继续往下跑，经过条件路由走向 `refiner` 或 `generator`。

### 路由逻辑

`backend/src/graph.py:44-61` — `route_after_review()` 函数：

| 用户选择 | retry_count | 去向 |
|---------|-------------|------|
| `accept` | — | `refiner` → `simulator` → END |
| `modify` | — | `refiner` → `simulator` → END |
| `reject` | < 3 | 回到 `generator` 重新生成 |
| `reject` | ≥ 3 | 直接 END（防死循环） |

### Checkpointer 的作用

`AsyncPostgresSaver`（`langgraph.checkpoint.postgres.aio`）是 LangGraph 的 PostgreSQL 异步检查点保存器，负责：

- 每个 `thread_id` 对应一个独立的会话状态
- `graph.astream()` 中断时自动保存快照到 PostgreSQL
- `graph.aget_state(config)` 随时从数据库读取当前状态
- `graph.aupdate_state(config, update)` 在恢复前注入用户决策
- **服务重启不丢数据**：所有 checkpoint 持久化在 PostgreSQL 中

## 💾 存档读档机制

系统支持 **服务重启** 和 **浏览器关闭** 后的会话恢复。

### 工作原理

1. 用户登录后，每次创建/操作会话都会在 `omiai_sessions` 表中留下记录
2. LangGraph 的每个中间状态都通过 `AsyncPostgresSaver` 存入 PostgreSQL 的 checkpoint 表
3. 用户重新登录后，侧边栏显示所有历史存档
4. 点击任意存档即可恢复到中断时的节点继续操作

### 数据库表结构

所有数据存储在 PostgreSQL 中，服务重启不丢失。

| 表 | 前缀 | 管理方 | 存储内容 |
|---|---|---|---|
| `omiai_users` | ✅ `omiai_` | 业务代码 | 用户账号（id, username, password_hash, created_at） |
| `omiai_sessions` | ✅ `omiai_` | 业务代码 | 会话存档（user_id, thread_id, title, current_step, created_at, updated_at） |
| `checkpoints` | ❌ 框架默认 | LangGraph | 每个 thread 的完整状态快照（chat_history, analysis_report, candidates, final_reply, simulation, retry_count 等） |
| `checkpoint_writes` | ❌ 框架默认 | LangGraph | 中断时待处理的写入队列 |
| `checkpoint_blobs` | ❌ 框架默认 | LangGraph | 大字段二进制数据 |

> `omiai_` 前缀仅用于我们自己创建的业务表。`checkpoints` / `checkpoint_writes` / `checkpoint_blobs` 三张表由 LangGraph 框架自动创建和管理，表名无法修改，无需修改。

### 关键代码文件索引

| 文件 | 职责 |
|------|------|
| `backend/src/graph.py:68-109` | 图构建 + `interrupt_before` 配置 |
| `backend/src/graph.py:25-37` | `human_review_node` — 透传节点，递增 retry_count |
| `backend/src/graph.py:44-61` | `route_after_review` — 条件路由 |
| `backend/main.py:93-131` | `POST /api/analyze` — 运行到中断 |
| `backend/main.py:134-173` | `POST /api/review` — 注入决策 + 恢复执行 |
| `backend/src/state.py:36-63` | `OverallState` — 完整状态定义 |

## 🔌 API 接口

### 认证接口（公开）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/register` | 注册新用户，返回 JWT token |
| `POST` | `/api/login` | 登录，返回 JWT token |

### 业务接口（需 Bearer token）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/session` | 创建新会话 |
| `POST` | `/api/analyze` | 提交聊天记录，运行至审核中断 |
| `POST` | `/api/review` | 提交审核决策（accept/modify/reject） |
| `GET` | `/api/state/{session_id}` | 查询会话状态 |
| `GET` | `/api/sessions` | 获取当前用户所有存档会话 |
| `DELETE` | `/api/sessions/{session_id}` | 删除指定存档 |
| `GET` | `/api/health` | 健康检查（公开） |

### 请求示例

```bash
# 0. 注册 / 登录
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "123456"}'
# → {"token": "eyJ...", "username": "alice"}

TOKEN="eyJ..."  # 后续请求带上这个 token

# 1. 创建会话
curl -X POST http://localhost:8000/api/session \
  -H "Authorization: Bearer $TOKEN"
# → {"session_id": "a1b2c3d4"}

# 2. 分析聊天记录
curl -X POST http://localhost:8000/api/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "a1b2c3d4",
    "chat_history": [
      {"speaker": "other", "content": "今天好累啊"},
      {"speaker": "me", "content": "怎么了？"}
    ],
    "user_persona": "内向理工男",
    "user_goal": "邀约见面"
  }'
# → 返回分析报告 + 3 条候选回复（is_interrupted: true）

# 3. 查看存档列表
curl http://localhost:8000/api/sessions \
  -H "Authorization: Bearer $TOKEN"

# 4. 选择第 1 条
curl -X POST http://localhost:8000/api/review \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "a1b2c3d4",
    "decision": "accept",
    "selected_index": 0
  }'
# → 返回润色后的最终回复 + 模拟推演

# 5. 删除存档
curl -X DELETE http://localhost:8000/api/sessions/a1b2c3d4 \
  -H "Authorization: Bearer $TOKEN"
```

## 🧪 运行测试

```bash
cd backend
venv\Scripts\python test_api.py
```



## 问题

```mark
> backend后端项目我用pycharm打开，但是py文件中有的依赖还是有红色下划线，但是命令行uvicorn main:app --reload --port
  8000也是可以运行成的

  Thought for 8s (ctrl+o to expand)

● 这是 PyCharm 的 Python 解释器配置问题，不是代码问题。代码本身没问题（命令行能跑通就是证明）。

  原因： PyCharm 没有识别到 backend/venv/ 里的 Python 解释器，所以依赖包显示红色下划线。

  修复步骤：

  1. PyCharm 右下角点击当前的 Python 解释器名称
  2. 选择 Add New Interpreter → Add Local Interpreter
  3. 选 Existing，路径选 backend\venv\Scripts\python.exe
  4. 确认后 PyCharm 会重新索引，红色下划线消失

  或者通过菜单：File → Settings → Project → Python Interpreter → 齿轮图标 → Add → Existing → 选
  backend\venv\Scripts\python.exe。
  
  
  > 还是有的

  Thought for 11s (ctrl+o to expand)

● 这是 PyCharm 的源根目录配置问题。看一下你的项目结构：

  omiai/              ← 如果 PyCharm 打开的是这个根目录
    backend/
      main.py         ← from src.state import ...（这里 src 找不到）
      src/
        state.py

  解决办法：在 PyCharm 中右键点击 backend 目录 → Mark Directory as → Sources Root。

  这样 main.py 里的 from src.state import ... 就能被 PyCharm 正确识别了。做完后如果还有个别红色下划线，试试 File →
  Invalidate Caches → Invalidate and Restart。
  
  
  
  > 现在main.py没问题了，但是src文件夹下的py文件，还有nodes文件夹下的py文件还是有红色下划线的

  Thought for 14s (ctrl+o to expand)

● 这是因为 PyCharm 的源根和包解析有多层嵌套。main.py 从 backend 找 src 没问题，但 src/ 内部的互相引用需要额外配置。

  两步解决：

  1. 把 src 也标记为源根： 右键 backend/src → Mark Directory as → Sources Root（蓝色文件夹图标）

  2. 确认解释器： File → Settings → Project → Python Interpreter → 确认选的是
  backend\venv\Scripts\python.exe，包列表里能看到 langgraph、openai、fastapi 等

  这样 src/ 下的 from src.state import ... 和 from src.llm_client import ... 两种引用路径 PyCharm 都能正确解析。


> 解决了。然后启动只能命令行uvicorn main:app --reload --port 8000 还可以在pycharm直接运行吗

  Thought for 3s, read 1 file (ctrl+o to expand)

● 可以。在 main.py 末尾加一段代码，就能直接点 PyCharm 的绿色运行按钮启动。

  Thought for 2s, read 1 file (ctrl+o to expand)

● Update(backend\main.py)
  ⎿  Added 9 lines
      200  async def health():
      201      """健康检查端点。"""
      202      return {"status": "ok"}
      203 +
      204 +
      205 +# ---------------------------------------------------------------------------
      206 +# 直接运行入口（PyCharm 右键 Run 或点绿色 ▶ 按钮）
      207 +# ---------------------------------------------------------------------------
      208 +
      209 +if __name__ == "__main__":
      210 +    import uvicorn
      211 +    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

  Thought for 2s (ctrl+o to expand)

● 搞定。现在在 PyCharm 里右键 main.py → Run 'main' 或者直接点绿色 ▶ 按钮就能启动了。
```



## 使用案例

### 1、新建会话

```mark
POST http://localhost:5173/api/session
[Request]
NA

[Respose]
{"session_id":"98bb23fa"}

```



### 2.1、开始分析

```mark
POST http://localhost:5173/api/analyze
[Request]
{"session_id":"98bb23fa","chat_history":[{"speaker":"other","content":"今天好累啊"},{"speaker":"me","content":"怎么了？工作太忙了吗"},{"speaker":"other","content":"是啊，老板又加需求"},{"speaker":"me","content":"哈哈，IT行业的日常"},{"speaker":"other","content":"你倒是挺理解的嘛"}],"user_persona":"活泼搞笑女","user_goal":"邀约见面"}

[Respose]
{
    "session_id": "98bb23fa",
    "state": {
        "chat_history": [
            {
                "speaker": "other",
                "content": "今天好累啊"
            },
            {
                "speaker": "me",
                "content": "怎么了？工作太忙了吗"
            },
            {
                "speaker": "other",
                "content": "是啊，老板又加需求"
            },
            {
                "speaker": "me",
                "content": "哈哈，IT行业的日常"
            },
            {
                "speaker": "other",
                "content": "你倒是挺理解的嘛"
            }
        ],
        "user_persona": "活泼搞笑女",
        "user_goal": "邀约见面",
        "analysis_report": {
            "emotion_score": 0.68,
            "intent": "分享工作疲惫并寻求共情",
            "risk_level": "低",
            "key_insight": "对方虽然在抱怨工作，但最后一句带有轻松和认可意味，说明对你的回应不排斥。建议继续共情，可以顺着说“太懂了，需求一加就没完，你今天是不是被折腾惨了？”来延续话题。"
        },
        "candidates": [
            {
                "style": "幽默",
                "reply": "懂了，今天你是被需求追杀的一天😂下班我请你回血？",
                "strategy_explain": "用夸张比喻接住对方疲惫，再自然抛出见面邀约，轻松不突兀"
            },
            {
                "style": "温暖",
                "reply": "听着就累，今天辛苦啦。要不要出来吃点好吃的缓缓？",
                "strategy_explain": "先共情认可对方的辛苦，再用吃饭作为温柔邀约，降低压力"
            },
            {
                "style": "推拉",
                "reply": "看来你今天战损不低，勉强允许你见我充个电😏",
                "strategy_explain": "用轻微调侃和自信姿态制造互动感，把见面包装成有趣奖励"
            }
        ],
        "human_decision": null,
        "human_selected_index": null,
        "human_modified_text": null,
        "final_reply": null,
        "simulation": null,
        "retry_count": 0,
        "error_message": null
    },
    "is_interrupted": true
}
```



### 2.2、全部驳回，重新生成

```mark
POST http://localhost:5173/api/review
[Request]
{"session_id":"98bb23fa","decision":"reject","selected_index":0,"modified_text":null}

[Respose]
{
    "session_id": "98bb23fa",
    "state": {
        "chat_history": [
            {
                "speaker": "other",
                "content": "今天好累啊"
            },
            {
                "speaker": "me",
                "content": "怎么了？工作太忙了吗"
            },
            {
                "speaker": "other",
                "content": "是啊，老板又加需求"
            },
            {
                "speaker": "me",
                "content": "哈哈，IT行业的日常"
            },
            {
                "speaker": "other",
                "content": "你倒是挺理解的嘛"
            }
        ],
        "user_persona": "活泼搞笑女",
        "user_goal": "邀约见面",
        "analysis_report": {
            "emotion_score": 0.68,
            "intent": "分享工作疲惫并寻求共情",
            "risk_level": "低",
            "key_insight": "对方虽然在抱怨工作，但最后一句带有轻松和认可意味，说明对你的回应不排斥。建议继续共情，可以顺着说“太懂了，需求一加就没完，你今天是不是被折腾惨了？”来延续话题。"
        },
        "candidates": [
            {
                "style": "幽默",
                "reply": "听起来你今天被工作榨成甘蔗渣了😂要不要出来补点快乐糖分？",
                "strategy_explain": "用夸张比喻接住对方疲惫，再自然抛出见面邀约，轻松不施压"
            },
            {
                "style": "温暖",
                "reply": "辛苦啦，感觉你今天真的被折腾到了。晚上有空的话，我请你喝点放松的？",
                "strategy_explain": "先共情对方的累，再用温柔邀约提供陪伴和放松感"
            },
            {
                "style": "推拉",
                "reply": "你这状态适合被投喂一下，不过我只救值得救的人，今晚出来验收吗？",
                "strategy_explain": "带一点俏皮挑战和神秘感，把邀约包装成有趣互动，制造吸引力"
            }
        ],
        "human_decision": "reject",
        "human_selected_index": 0,
        "human_modified_text": null,
        "final_reply": null,
        "simulation": null,
        "retry_count": 1,
        "error_message": null
    },
    "is_interrupted": true
}
```



### 2.2、再次全部驳回，重新生成

```mark
POST http://localhost:5173/api/review
[Request]
{"session_id":"98bb23fa","decision":"reject","selected_index":0,"modified_text":null}

[Respose]
{
    "session_id": "98bb23fa",
    "state": {
        "chat_history": [
            {
                "speaker": "other",
                "content": "今天好累啊"
            },
            {
                "speaker": "me",
                "content": "怎么了？工作太忙了吗"
            },
            {
                "speaker": "other",
                "content": "是啊，老板又加需求"
            },
            {
                "speaker": "me",
                "content": "哈哈，IT行业的日常"
            },
            {
                "speaker": "other",
                "content": "你倒是挺理解的嘛"
            }
        ],
        "user_persona": "活泼搞笑女",
        "user_goal": "邀约见面",
        "analysis_report": {
            "emotion_score": 0.68,
            "intent": "分享工作疲惫并寻求共情",
            "risk_level": "低",
            "key_insight": "对方虽然在抱怨工作，但最后一句带有轻松和认可意味，说明对你的回应不排斥。建议继续共情，可以顺着说“太懂了，需求一加就没完，你今天是不是被折腾惨了？”来延续话题。"
        },
        "candidates": [
            {
                "style": "幽默",
                "reply": "你这工作强度，建议下班立刻申请一顿饭疗愈，我可以当陪诊员😎",
                "strategy_explain": "用夸张的“饭疗愈”制造轻松感，同时自然把话题引到见面吃饭。"
            },
            {
                "style": "温暖",
                "reply": "听着都累，今天辛苦啦。要不要找天出来吃点好的，给你回血？",
                "strategy_explain": "先共情对方疲惫，再用照顾感提出邀约，让对方更容易接受。"
            },
            {
                "style": "推拉",
                "reply": "感觉你今天被工作拿捏了，不过我有个解压方案，见面再告诉你。",
                "strategy_explain": "轻轻调侃对方状态，同时留下悬念，把好奇心和见面邀约结合起来。"
            }
        ],
        "human_decision": "reject",
        "human_selected_index": 0,
        "human_modified_text": null,
        "final_reply": null,
        "simulation": null,
        "retry_count": 2,
        "error_message": null
    },
    "is_interrupted": true
}
```



### 2.4、选一条修改好提交

```mark
POST http://localhost:5173/api/review
[Request]
{"session_id":"98bb23fa","decision":"modify","selected_index":1,"modified_text":"先诅咒下资本家一下。听着都累，今天辛苦啦。要不要找天出来吃点好的，给你回血？"}

[Respose]
{
    "session_id": "98bb23fa",
    "state": {
        "chat_history": [
            {
                "speaker": "other",
                "content": "今天好累啊"
            },
            {
                "speaker": "me",
                "content": "怎么了？工作太忙了吗"
            },
            {
                "speaker": "other",
                "content": "是啊，老板又加需求"
            },
            {
                "speaker": "me",
                "content": "哈哈，IT行业的日常"
            },
            {
                "speaker": "other",
                "content": "你倒是挺理解的嘛"
            }
        ],
        "user_persona": "活泼搞笑女",
        "user_goal": "邀约见面",
        "analysis_report": {
            "emotion_score": 0.68,
            "intent": "分享工作疲惫并寻求共情",
            "risk_level": "低",
            "key_insight": "对方虽然在抱怨工作，但最后一句带有轻松和认可意味，说明对你的回应不排斥。建议继续共情，可以顺着说“太懂了，需求一加就没完，你今天是不是被折腾惨了？”来延续话题。"
        },
        "candidates": [
            {
                "style": "幽默",
                "reply": "你这工作强度，建议下班立刻申请一顿饭疗愈，我可以当陪诊员😎",
                "strategy_explain": "用夸张的“饭疗愈”制造轻松感，同时自然把话题引到见面吃饭。"
            },
            {
                "style": "温暖",
                "reply": "听着都累，今天辛苦啦。要不要找天出来吃点好的，给你回血？",
                "strategy_explain": "先共情对方疲惫，再用照顾感提出邀约，让对方更容易接受。"
            },
            {
                "style": "推拉",
                "reply": "感觉你今天被工作拿捏了，不过我有个解压方案，见面再告诉你。",
                "strategy_explain": "轻轻调侃对方状态，同时留下悬念，把好奇心和见面邀约结合起来。"
            }
        ],
        "human_decision": "modify",
        "human_selected_index": 1,
        "human_modified_text": "先诅咒下资本家一下。听着都累，今天辛苦啦。要不要找天出来吃点好的，给你回血？",
        "final_reply": "先浅浅诅咒一下资本家。听着都累，今天辛苦啦！要不要找天出来吃点好的，给你回血？",
        "simulation": {
            "best_case": "哈哈哈先替我狠狠诅咒一下！确实需要回血了，吃点好的可以安排～你有什么推荐吗？",
            "normal_case": "哈哈谢谢，今天确实有点累。吃饭再说吧，最近有点忙。",
            "worst_case": "资本家这个说法也太夸张了吧😂 而且我就是吐槽一下，倒也不用特意出来吃饭。",
            "fallback_suggestion": "如果对方觉得你说得太夸张或对邀约有点压力，可以马上放轻语气：'哈哈我就是顺着你吐槽一下，没有那么严肃～吃饭也不急，就是觉得你最近辛苦，想找机会请你吃点好吃的。你先好好休息，改天再说也行。' 这样既解释了玩笑，也降低了邀约压力。"
        },
        "retry_count": 2,
        "error_message": null
    },
    "is_interrupted": false
}
```



### 3、查看历史详情

```
POST http://localhost:5173/api/state/98bb23fa
[Request]
NA

[Respose]
{
    "session_id": "98bb23fa",
    "state": {
        "chat_history": [
            {
                "speaker": "other",
                "content": "今天好累啊"
            },
            {
                "speaker": "me",
                "content": "怎么了？工作太忙了吗"
            },
            {
                "speaker": "other",
                "content": "是啊，老板又加需求"
            },
            {
                "speaker": "me",
                "content": "哈哈，IT行业的日常"
            },
            {
                "speaker": "other",
                "content": "你倒是挺理解的嘛"
            }
        ],
        "user_persona": "活泼搞笑女",
        "user_goal": "邀约见面",
        "analysis_report": {
            "emotion_score": 0.68,
            "intent": "分享工作疲惫并寻求共情",
            "risk_level": "低",
            "key_insight": "对方虽然在抱怨工作，但最后一句带有轻松和认可意味，说明对你的回应不排斥。建议继续共情，可以顺着说“太懂了，需求一加就没完，你今天是不是被折腾惨了？”来延续话题。"
        },
        "candidates": [
            {
                "style": "幽默",
                "reply": "你这工作强度，建议下班立刻申请一顿饭疗愈，我可以当陪诊员😎",
                "strategy_explain": "用夸张的“饭疗愈”制造轻松感，同时自然把话题引到见面吃饭。"
            },
            {
                "style": "温暖",
                "reply": "听着都累，今天辛苦啦。要不要找天出来吃点好的，给你回血？",
                "strategy_explain": "先共情对方疲惫，再用照顾感提出邀约，让对方更容易接受。"
            },
            {
                "style": "推拉",
                "reply": "感觉你今天被工作拿捏了，不过我有个解压方案，见面再告诉你。",
                "strategy_explain": "轻轻调侃对方状态，同时留下悬念，把好奇心和见面邀约结合起来。"
            }
        ],
        "human_decision": "modify",
        "human_selected_index": 1,
        "human_modified_text": "先诅咒下资本家一下。听着都累，今天辛苦啦。要不要找天出来吃点好的，给你回血？",
        "final_reply": "先浅浅诅咒一下资本家。听着都累，今天辛苦啦！要不要找天出来吃点好的，给你回血？",
        "simulation": {
            "best_case": "哈哈哈先替我狠狠诅咒一下！确实需要回血了，吃点好的可以安排～你有什么推荐吗？",
            "normal_case": "哈哈谢谢，今天确实有点累。吃饭再说吧，最近有点忙。",
            "worst_case": "资本家这个说法也太夸张了吧😂 而且我就是吐槽一下，倒也不用特意出来吃饭。",
            "fallback_suggestion": "如果对方觉得你说得太夸张或对邀约有点压力，可以马上放轻语气：'哈哈我就是顺着你吐槽一下，没有那么严肃～吃饭也不急，就是觉得你最近辛苦，想找机会请你吃点好吃的。你先好好休息，改天再说也行。' 这样既解释了玩笑，也降低了邀约压力。"
        },
        "retry_count": 2,
        "error_message": null
    },
    "is_interrupted": false
}
```

