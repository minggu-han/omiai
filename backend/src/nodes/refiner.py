"""节点4：回复润色器 —— 优化用户选中或修改后的回复。"""

from src.state import OverallState
from src.llm_client import chat_completion_parsed
from src.prompts import REFINER_SYSTEM, build_refiner_user_prompt


def refiner_node(state: OverallState) -> dict:
    """润色用户选中或手动修改后的回复。

    读取：
        - human_decision: "accept" | "modify"
        - human_selected_index
        - human_modified_text
        - candidates
        - user_persona
    写入：
        - final_reply: 润色后的最终回复文本
    """
    decision = state.get("human_decision", "accept")
    selected_idx = state.get("human_selected_index", 0)

    # 确定基础回复文本
    if decision == "modify":
        base_reply = state.get("human_modified_text") or ""
    else:
        candidates = state.get("candidates") or []
        if 0 <= selected_idx < len(candidates):
            base_reply = candidates[selected_idx].get("reply", "")
        else:
            base_reply = ""

    if not base_reply.strip():
        return {"final_reply": "（回复内容为空）"}

    persona = state.get("user_persona")
    user_prompt = build_refiner_user_prompt(
        selected_reply=base_reply,
        decision=decision,
        user_persona=persona,
    )

    try:
        result = chat_completion_parsed(REFINER_SYSTEM, user_prompt, temperature=0.5)
    except Exception as e:
        # 出错时返回未润色的原始版本
        return {"final_reply": base_reply, "error_message": str(e)}

    final = result.get("final_reply", base_reply)
    return {"final_reply": final.strip() or base_reply}
