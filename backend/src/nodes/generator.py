"""节点2：多风格回复生成器。"""

from src.state import OverallState
from src.llm_client import chat_completion_parsed
from src.prompts import GENERATOR_SYSTEM, build_generator_user_prompt


def generator_node(state: OverallState) -> dict:
    """生成 3 条不同风格的候选回复（幽默/温暖/推拉）。

    读取：
        - analysis_report
        - user_persona
        - user_goal
        - retry_count
        - human_modified_text（作为驳回时的反馈信息）
    写入：
        - candidates: CandidateReply 列表
    """
    analysis = state.get("analysis_report") or {}
    persona = state.get("user_persona")
    goal = state.get("user_goal")
    retry = state.get("retry_count", 0)

    # 如果是重试，将用户修改文本作为反馈传递给 LLM
    feedback = None
    if retry > 0:
        feedback = state.get("human_modified_text") or "用户希望换一种风格重新生成"

    user_prompt = build_generator_user_prompt(
        analysis_report=analysis,
        user_persona=persona,
        user_goal=goal,
        retry_count=retry,
        previous_feedback=feedback,
    )

    try:
        result = chat_completion_parsed(GENERATOR_SYSTEM, user_prompt, temperature=0.8)
    except Exception as e:
        return {
            "candidates": [
                {
                    "style": "幽默",
                    "reply": "生成失败，请重试",
                    "strategy_explain": f"错误：{str(e)}",
                }
            ],
            "error_message": str(e),
        }

    candidates = result.get("candidates", [])
    # 确保始终有 3 条候选回复
    if len(candidates) < 3:
        default_styles = ["幽默", "温暖", "推拉"]
        for i in range(len(candidates), 3):
            candidates.append({
                "style": default_styles[i],
                "reply": "（生成不完整，请重试）",
                "strategy_explain": "LLM 输出不完整，建议驳回重来",
            })

    return {
        "candidates": candidates[:3],
    }
