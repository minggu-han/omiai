"""节点1：意图与情绪分析器。"""

import json

from src.state import OverallState
from src.llm_client import chat_completion_parsed
from src.prompts import ANALYZER_SYSTEM


def analyzer_node(state: OverallState) -> dict:
    """分析聊天记录，判断对方的情绪、意图和危险等级。

    读取：
        - chat_history: ChatMessage 列表
    写入：
        - analysis_report: AnalysisReport 字典
    """
    # 将聊天记录转换为文本表示
    lines = []
    for msg in state.get("chat_history", []):
        speaker_label = "对方" if msg["speaker"] == "other" else "我"
        lines.append(f"{speaker_label}：{msg['content']}")
    chat_text = "\n".join(lines)

    if not chat_text.strip():
        return {
            "analysis_report": {
                "emotion_score": 0.5,
                "intent": "未知",
                "risk_level": "低",
                "key_insight": "聊天记录为空，无法分析。请先输入聊天内容。",
            }
        }

    user_prompt = f"请分析以下聊天记录：\n\n{chat_text}"

    try:
        result = chat_completion_parsed(ANALYZER_SYSTEM, user_prompt, temperature=0.3)
    except Exception as e:
        return {
            "analysis_report": {
                "emotion_score": 0.5,
                "intent": "分析失败",
                "risk_level": "中",
                "key_insight": f"LLM 调用失败：{str(e)}，请重试。",
            },
            "error_message": str(e),
        }

    # 规范化输出结果
    return {
        "analysis_report": {
            "emotion_score": float(result.get("emotion_score", 0.5)),
            "intent": str(result.get("intent", "未知")),
            "risk_level": str(result.get("risk_level", "低")),
            "key_insight": str(result.get("key_insight", "")),
        }
    }
