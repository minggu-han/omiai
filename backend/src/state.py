"""AI 约会助攻顾问 LangGraph 工作流的状态定义。"""

from typing import List, Optional, Literal
from typing_extensions import TypedDict


class ChatMessage(TypedDict):
    """单条聊天消息。"""
    speaker: Literal["me", "other"]
    content: str


class CandidateReply(TypedDict):
    """一条 AI 生成的候选回复。"""
    style: str          # "幽默" | "温暖" | "推拉"
    reply: str
    strategy_explain: str


class AnalysisReport(TypedDict):
    """意图分析节点的输出。"""
    emotion_score: float       # 0-1，越高代表对方情绪越正向
    intent: str                # 例如："分享日常"、"测试反应"
    risk_level: str            # "低" | "中" | "高"
    key_insight: str           # 给用户的可操作建议


class SimulationResult(TypedDict):
    """模拟推演节点的输出。"""
    best_case: str
    normal_case: str
    worst_case: str
    fallback_suggestion: str


class OverallState(TypedDict):
    """贯穿整个 LangGraph 工作流的完整状态。"""

    # === 输入层 ===
    chat_history: List[ChatMessage]
    user_persona: Optional[str]
    user_goal: Optional[str]

    # === 节点1：意图分析输出 ===
    analysis_report: Optional[AnalysisReport]

    # === 节点2：策略生成输出 ===
    candidates: Optional[List[CandidateReply]]

    # === 节点3：人工审核输出 ===
    human_decision: Optional[Literal["accept", "modify", "reject"]]
    human_selected_index: Optional[int]
    human_modified_text: Optional[str]

    # === 节点4：回复润色输出 ===
    final_reply: Optional[str]

    # === 节点5：模拟推演输出 ===
    simulation: Optional[SimulationResult]

    # === 控制字段 ===
    retry_count: int
    error_message: Optional[str]
