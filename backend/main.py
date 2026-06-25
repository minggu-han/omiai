"""FastAPI 应用 —— AI 约会助攻顾问后端服务。

启动方式：  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Literal
from dotenv import load_dotenv

from src.graph import build_graph
from src.session import create_initial_state, new_thread_id, make_config

load_dotenv()

# ---------------------------------------------------------------------------
# FastAPI 应用实例
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI 约会助攻顾问 API",
    description="基于 LangGraph 的多智能体协作系统后端",
    version="1.0.0",
)

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 全局图实例（启动时编译一次，所有请求共享 checkpointer）
# ---------------------------------------------------------------------------

_graph = build_graph()


# ---------------------------------------------------------------------------
# 请求 / 响应模型
# ---------------------------------------------------------------------------

class ChatMessageInput(BaseModel):
    """聊天消息输入。"""
    speaker: Literal["me", "other"]
    content: str


class AnalyzeRequest(BaseModel):
    """分析请求。"""
    session_id: str
    chat_history: List[ChatMessageInput]
    user_persona: Optional[str] = None
    user_goal: Optional[str] = None


class ReviewRequest(BaseModel):
    """审核请求。"""
    session_id: str
    decision: Literal["accept", "modify", "reject"]
    selected_index: int = 0
    modified_text: Optional[str] = None


class SessionResponse(BaseModel):
    """会话创建响应。"""
    session_id: str


class StateResponse(BaseModel):
    """状态查询响应。"""
    session_id: str
    state: dict
    is_interrupted: bool


# ---------------------------------------------------------------------------
# API 路由
# ---------------------------------------------------------------------------


@app.post("/api/session", response_model=SessionResponse)
async def create_session():
    """创建新的分析会话，返回 session_id。"""
    session_id = new_thread_id()
    return SessionResponse(session_id=session_id)


@app.post("/api/analyze", response_model=StateResponse)
async def analyze(req: AnalyzeRequest):
    """输入聊天记录，运行分析 + 生成节点，在人工审核节点前中断。

    返回当前状态（包含分析报告和候选回复），前端据此展示审核界面。
    """
    # 构建初始状态
    chat_text = "\n".join(
        f"{'对方' if m.speaker == 'other' else '我'}：{m.content}"
        for m in req.chat_history
    )
    initial_state = create_initial_state(
        chat_history_text=chat_text,
        user_persona=req.user_persona,
        user_goal=req.user_goal,
    )

    config = make_config(req.session_id)

    try:
        # 运行图，直到 human_review 中断点
        events = list(_graph.stream(initial_state, config))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图执行失败：{str(e)}")

    # 读取中断后的状态
    snapshot = _graph.get_state(config)
    if snapshot is None or snapshot.values is None:
        raise HTTPException(status_code=500, detail="无法读取图状态")

    state_dict = dict(snapshot.values)
    # 检查是否处于中断状态
    is_interrupted = snapshot.next is not None and len(snapshot.next) > 0

    return StateResponse(
        session_id=req.session_id,
        state=state_dict,
        is_interrupted=is_interrupted,
    )


@app.post("/api/review", response_model=StateResponse)
async def review(req: ReviewRequest):
    """提交人工审核结果，恢复图执行并返回最终状态。"""
    config = make_config(req.session_id)

    # 检查会话是否存在
    snapshot = _graph.get_state(config)
    if snapshot is None or snapshot.values is None:
        raise HTTPException(status_code=404, detail="会话不存在，请先创建会话并进行分析")

    # 构建状态更新
    update = {
        "human_decision": req.decision,
        "human_selected_index": req.selected_index,
    }
    if req.decision == "modify" and req.modified_text:
        update["human_modified_text"] = req.modified_text

    # 更新状态
    _graph.update_state(config, update)

    # 恢复图执行
    try:
        events = list(_graph.stream(None, config))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图恢复执行失败：{str(e)}")

    # 读取最终状态
    snapshot = _graph.get_state(config)
    if snapshot is None or snapshot.values is None:
        raise HTTPException(status_code=500, detail="无法读取图状态")

    state_dict = dict(snapshot.values)
    is_interrupted = snapshot.next is not None and len(snapshot.next) > 0

    return StateResponse(
        session_id=req.session_id,
        state=state_dict,
        is_interrupted=is_interrupted,
    )


@app.get("/api/state/{session_id}", response_model=StateResponse)
async def get_state(session_id: str):
    """查询指定会话的当前状态。"""
    config = make_config(session_id)
    snapshot = _graph.get_state(config)

    if snapshot is None or snapshot.values is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    state_dict = dict(snapshot.values)
    is_interrupted = snapshot.next is not None and len(snapshot.next) > 0

    return StateResponse(
        session_id=session_id,
        state=state_dict,
        is_interrupted=is_interrupted,
    )


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    """健康检查端点。"""
    return {"status": "ok"}
