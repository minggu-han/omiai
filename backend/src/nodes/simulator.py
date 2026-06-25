"""节点5：反应模拟器 —— 预测对方可能的回复。"""

from src.state import OverallState
from src.llm_client import chat_completion_parsed
from src.prompts import SIMULATOR_SYSTEM, build_simulator_user_prompt


def simulator_node(state: OverallState) -> dict:
    """模拟对方收到最终回复后的 3 种可能反应。

    读取：
        - chat_history
        - final_reply
    写入：
        - simulation: SimulationResult 字典
    """
    # 构建聊天记录文本
    lines = []
    for msg in state.get("chat_history", []):
        speaker_label = "对方" if msg["speaker"] == "other" else "我"
        lines.append(f"{speaker_label}：{msg['content']}")
    chat_text = "\n".join(lines)

    final_reply = state.get("final_reply") or "（无回复内容）"

    user_prompt = build_simulator_user_prompt(
        chat_history_text=chat_text,
        final_reply=final_reply,
    )

    try:
        result = chat_completion_parsed(SIMULATOR_SYSTEM, user_prompt, temperature=0.7)
    except Exception as e:
        return {
            "simulation": {
                "best_case": "模拟失败",
                "normal_case": "模拟失败",
                "worst_case": "模拟失败",
                "fallback_suggestion": f"LLM 调用失败：{str(e)}，请重试。",
            },
            "error_message": str(e),
        }

    return {
        "simulation": {
            "best_case": str(result.get("best_case", "")),
            "normal_case": str(result.get("normal_case", "")),
            "worst_case": str(result.get("worst_case", "")),
            "fallback_suggestion": str(result.get("fallback_suggestion", "")),
        }
    }
