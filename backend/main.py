"""FastAPI 应用 —— AI 聊天顾问系统后端服务。

启动方式：  uvicorn main:app --reload --port 8000
"""

import asyncio
import sys

# Windows 下 psycopg 异步需要 SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
from contextlib import asynccontextmanager
from typing import Optional, List, Literal

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.graph import build_graph
from src.session import create_initial_state, new_thread_id, make_config
from src.database import init_db, get_db
from src.models import User, Session
from src.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    verify_token,
)

load_dotenv()

# ---------------------------------------------------------------------------
# 全局图实例（通过 lifespan 初始化）
# ---------------------------------------------------------------------------

_graph = None
_saver = None  # 保留引用，用于 adelete_thread 等操作


def _pg_conn_string() -> str:
    """从 SQLAlchemy asyncpg URL 转换为 psycopg 连接字符串。"""
    raw = os.getenv("DATABASE_URL", "postgresql+asyncpg://mcp:mcp@172.18.1.76:5432/mcp")
    # postgresql+asyncpg:// → postgresql://
    return raw.replace("+asyncpg", "")


async def _init_graph_saver():
    """初始化 AsyncPostgresSaver + 编译图。"""
    global _graph, _saver
    conn_string = _pg_conn_string()
    conn = await psycopg.AsyncConnection.connect(conn_string, autocommit=True)
    _saver = AsyncPostgresSaver(conn)
    await _saver.setup()  # 创建 LangGraph checkpoint 表
    _graph = build_graph(checkpointer=_saver)


# ---------------------------------------------------------------------------
# FastAPI 生命周期
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动：初始化数据库表 + LangGraph PostgreSQL checkpointer。"""
    await init_db()  # 创建 omiai_users / omiai_sessions
    await _init_graph_saver()  # 创建 checkpoint 表 + 编译图
    yield


# ---------------------------------------------------------------------------
# FastAPI 应用实例
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI 聊天顾问系统 API",
    description="基于 LangGraph 的多智能体协作系统后端",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 请求 / 响应模型
# ---------------------------------------------------------------------------


class ChatMessageInput(BaseModel):
    speaker: Literal["me", "other"]
    content: str


class AnalyzeRequest(BaseModel):
    session_id: str
    chat_history: List[ChatMessageInput]
    user_persona: Optional[str] = None
    user_goal: Optional[str] = None


class ReviewRequest(BaseModel):
    session_id: str
    decision: Literal["accept", "modify", "reject"]
    selected_index: int = 0
    modified_text: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    username: str


class SessionResponse(BaseModel):
    session_id: str


class StateResponse(BaseModel):
    session_id: str
    state: dict
    is_interrupted: bool


class SessionItem(BaseModel):
    """存档列表中的单条会话。"""
    session_id: str
    thread_id: str
    title: str
    current_step: str
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionItem]


# ---------------------------------------------------------------------------
# 认证路由（无需登录）
# ---------------------------------------------------------------------------


@app.post("/api/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户。"""
    # 检查用户名是否已存在
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.username)
    return AuthResponse(token=token, username=user.username)


@app.post("/api/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录，返回 JWT token。"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(user.id, user.username)
    return AuthResponse(token=token, username=user.username)


# ---------------------------------------------------------------------------
# 会话管理路由（需登录）
# ---------------------------------------------------------------------------


@app.get("/api/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有存档会话。"""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.updated_at.desc())
    )
    sessions = result.scalars().all()
    return SessionListResponse(
        sessions=[
            SessionItem(
                session_id=s.thread_id,
                thread_id=s.thread_id,
                title=s.title or "无标题",
                current_step=s.current_step,
                created_at=s.created_at.isoformat() if s.created_at else "",
                updated_at=s.updated_at.isoformat() if s.updated_at else "",
            )
            for s in sessions
        ]
    )


@app.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除指定存档会话。"""
    result = await db.execute(
        select(Session).where(
            Session.thread_id == session_id,
            Session.user_id == current_user.id,
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 同时删除 LangGraph 的 checkpoint 数据
    await _saver.adelete_thread(session_id)

    await db.delete(s)
    await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 分析路由（需登录）
# ---------------------------------------------------------------------------


@app.post("/api/session", response_model=SessionResponse)
async def create_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的分析会话，返回 session_id。"""
    thread_id = new_thread_id()

    session = Session(
        user_id=current_user.id,
        thread_id=thread_id,
        title="新建会话",
        current_step="input",
    )
    db.add(session)
    await db.commit()

    return SessionResponse(session_id=thread_id)


@app.post("/api/analyze", response_model=StateResponse)
async def analyze(
    req: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """输入聊天记录，运行分析 + 生成节点，在人工审核节点前中断。"""
    # 验证会话归属
    result = await db.execute(
        select(Session).where(Session.thread_id == req.session_id)
    )
    session = result.scalar_one_or_none()
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

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

    # 异步运行图，直到 human_review 中断点
    try:
        events = []
        async for event in _graph.astream(initial_state, config):
            events.append(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图执行失败：{str(e)}")

    # 读取中断后的状态
    snapshot = await _graph.aget_state(config)
    if snapshot is None or snapshot.values is None:
        raise HTTPException(status_code=500, detail="无法读取图状态")

    state_dict = dict(snapshot.values)
    is_interrupted = snapshot.next is not None and len(snapshot.next) > 0

    # 更新会话存档
    title = req.chat_history[-1].content[:50] if req.chat_history else "新建会话"
    session.title = f"对方：{title}"
    session.current_step = "review" if is_interrupted else "result"
    await db.commit()

    return StateResponse(
        session_id=req.session_id,
        state=state_dict,
        is_interrupted=is_interrupted,
    )


@app.post("/api/review", response_model=StateResponse)
async def review(
    req: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交人工审核结果，恢复图执行并返回最终状态。"""
    # 验证会话归属
    result = await db.execute(
        select(Session).where(Session.thread_id == req.session_id)
    )
    session = result.scalar_one_or_none()
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    config = make_config(req.session_id)

    # 检查会话是否存在
    snapshot = await _graph.aget_state(config)
    if snapshot is None or snapshot.values is None:
        raise HTTPException(status_code=404, detail="会话不存在，请先创建会话并进行分析")

    # 构建状态更新
    update = {
        "human_decision": req.decision,
        "human_selected_index": req.selected_index,
    }
    if req.decision == "modify" and req.modified_text:
        update["human_modified_text"] = req.modified_text

    # 异步更新状态
    await _graph.aupdate_state(config, update)

    # 异步恢复图执行
    try:
        events = []
        async for event in _graph.astream(None, config):
            events.append(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图恢复执行失败：{str(e)}")

    # 读取最终状态
    snapshot = await _graph.aget_state(config)
    if snapshot is None or snapshot.values is None:
        raise HTTPException(status_code=500, detail="无法读取图状态")

    state_dict = dict(snapshot.values)
    is_interrupted = snapshot.next is not None and len(snapshot.next) > 0

    # 更新会话存档
    final_reply = state_dict.get("final_reply")
    if final_reply and not is_interrupted:
        session.current_step = "result"
    elif state_dict.get("retry_count", 0) >= 3:
        session.current_step = "maxRetry"
    else:
        session.current_step = "review"
    await db.commit()

    return StateResponse(
        session_id=req.session_id,
        state=state_dict,
        is_interrupted=is_interrupted,
    )


@app.get("/api/state/{session_id}", response_model=StateResponse)
async def get_state(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询指定会话的当前状态。"""
    # 验证会话归属
    result = await db.execute(
        select(Session).where(Session.thread_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    config = make_config(session_id)
    snapshot = await _graph.aget_state(config)

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


# ---------------------------------------------------------------------------
# 直接运行入口（PyCharm 右键 Run 或点绿色 ▶ 按钮）
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, loop="asyncio")
