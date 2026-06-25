# 💘 AI 约会助攻顾问 (AI Dating Coach)

基于 **LangGraph** 多智能体协作系统，帮助用户分析聊天语境、生成个性化回复，并通过**人工审核机制**确保回复符合用户真实人设。

> 分析 → 生成 → 审核 → 润色 → 模拟，五步搞定每次回复。

## 🛠 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Pinia |
| 后端 | FastAPI + LangGraph |
| 大模型 | OpenAI GPT-4 |
| 状态持久化 | LangGraph MemorySaver |

## 📁 项目结构

```
omiai/
├── backend/                  # FastAPI 后端
│   ├── main.py               # 应用入口 + API 路由
│   ├── requirements.txt      # Python 依赖
│   ├── .env                  # 环境变量（API Key）
│   └── src/
│       ├── state.py          # 状态类型定义
│       ├── llm_client.py     # LLM 客户端封装
│       ├── prompts.py        # Prompt 模板
│       ├── session.py        # 会话管理
│       ├── graph.py          # LangGraph 图定义
│       └── nodes/            # 4 个 AI 节点
│           ├── analyzer.py   # 意图情绪分析
│           ├── generator.py  # 候选回复生成
│           ├── refiner.py    # 回复润色
│           └── simulator.py  # 对方反应模拟
│
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── App.vue           # 主组件
│   │   ├── api/index.js      # API 客户端
│   │   ├── stores/session.js # Pinia 状态管理
│   │   └── components/       # 4 个页面组件
│   └── vite.config.js
│
└── project-requirement.md    # 原始需求文档
```

## 🚀 快速启动

### 1. 后端

```bash
cd backend

# 创建虚拟环境并安装依赖
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt

# 编辑 .env 填入 API Key
# OPENAI_API_KEY=sk-xxx

# 启动（默认 :8000）
uvicorn main:app --reload --port 8000
```

API 文档自动生成：http://localhost:8000/docs

### 2. 前端

```bash
cd frontend

npm install
npm run dev                  # → http://localhost:5173
```

前端已配置 Vite 代理，`/api` 请求自动转发到后端。

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

## 🔌 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/session` | 创建新会话 |
| `POST` | `/api/analyze` | 提交聊天记录，运行至审核中断 |
| `POST` | `/api/review` | 提交审核决策（accept/modify/reject） |
| `GET` | `/api/state/{session_id}` | 查询会话状态 |
| `GET` | `/api/health` | 健康检查 |

### 请求示例

```bash
# 1. 创建会话
curl -X POST http://localhost:8000/api/session
# → {"session_id": "a1b2c3d4"}

# 2. 分析聊天记录
curl -X POST http://localhost:8000/api/analyze \
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

# 3. 选择第 1 条
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "a1b2c3d4",
    "decision": "accept",
    "selected_index": 0
  }'
# → 返回润色后的最终回复 + 模拟推演
```

## 🧪 运行测试

```bash
cd backend
venv\Scripts\python test_api.py
```
