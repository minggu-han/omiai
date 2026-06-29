"""会话管理器 —— 封装 LangGraph checkpointer 和线程生命周期。"""

import uuid
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver

from src.state import OverallState


# ---------------------------------------------------------------------------
# 全局内存 checkpointer（所有会话共享）
# ---------------------------------------------------------------------------

_checkpointer = MemorySaver()


def get_checkpointer() -> MemorySaver:
    """返回全局 MemorySaver 实例。"""
    return _checkpointer


# ---------------------------------------------------------------------------
# 线程（会话）辅助函数
# ---------------------------------------------------------------------------

def new_thread_id() -> str:
    """生成一个新的唯一线程 ID。"""
    #取前8位作为新会话id
    return str(uuid.uuid4())[:8]


def make_config(thread_id: str) -> dict:
    """为指定线程构建 LangGraph 配置字典。"""
    return {"configurable": {"thread_id": thread_id}}


# ---------------------------------------------------------------------------
# 初始状态工厂
# ---------------------------------------------------------------------------

def create_initial_state(
    chat_history_text: str,
    user_persona: Optional[str] = None,
    user_goal: Optional[str] = None,
) -> OverallState:
    """将原始聊天文本解析为初始 OverallState。

    期望格式：
        对方：xxx
        我：xxx
    """
    print(f'chat_history_text: {chat_history_text}')
    messages = []
    for line in chat_history_text.strip().split("\n"):
        line = line.strip()
        print(f'line: {line}')
        if not line:
            continue
        if line.startswith("对方："):
            messages.append({"speaker": "other", "content": line[3:]})
        elif line.startswith("我："):
            messages.append({"speaker": "me", "content": line[2:]})
        elif "：" in line:
            # 兜底：无法判断发送方时默认视为"对方"
            _, content = line.split("：", 1)
            messages.append({"speaker": "other", "content": content.strip()})

    for msg in messages:
        print('*' * 20)
        print(msg)
        print(f'speaker: {msg["speaker"]}')
        print(f'msg: {msg["content"]}')
        print('*' * 20)

    return OverallState(
        chat_history=messages,
        user_persona=user_persona,
        user_goal=user_goal,
        analysis_report=None,
        candidates=None,
        human_decision=None,
        human_selected_index=None,
        human_modified_text=None,
        final_reply=None,
        simulation=None,
        retry_count=0,
        error_message=None,
    )
