"""OpenAI LLM 客户端封装，为 AI 约会助攻顾问提供统一的大模型调用接口。"""

import json
import os
from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# 单例客户端 —— 首次导入时创建，后续复用
# ---------------------------------------------------------------------------

_client: Optional[OpenAI] = None
_model: str = os.getenv("LLM_MODEL", "gpt-4o")


def get_client() -> OpenAI:
    """获取（或创建）共享的 OpenAI 客户端实例。"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        _client = OpenAI(
            api_key=api_key or "sk-placeholder",
            base_url=base_url or None,
        )
    return _client


def set_api_key(key: str, base_url: Optional[str] = None) -> None:
    """运行时动态更新 API Key（以及可选的自定义 Base URL）。"""
    global _client
    _client = OpenAI(
        api_key=key,
        base_url=base_url or None,
    )


# ---------------------------------------------------------------------------
# 对话补全辅助函数
# ---------------------------------------------------------------------------

def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    response_json: bool = True,
) -> str:
    """调用大模型并返回响应文本。

    参数
    ----------
    system_prompt : str
        系统级指令。
    user_prompt : str
        具体的任务 / 用户消息。
    temperature : float
        采样温度。
    max_tokens : int
        最大输出 token 数。
    response_json : bool
        是否开启 JSON 输出模式（模型需支持）。

    返回
    -------
    str
        LLM 响应的原始文本内容。
    """
    client = get_client()
    kwargs = dict(
        model=_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if response_json:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def chat_completion_parsed(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> dict:
    """调用 LLM（JSON 模式）并返回解析后的字典。

    如果 JSON 解析失败，会将原始文本包装在 `{"raw": "..."}` 中，
    以便调用方仍然可以检查输出内容。
    """
    raw = chat_completion(
        system_prompt, user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        response_json=True,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 优雅降级：返回原始文本，让调用方自主处理
        return {"raw": raw, "parse_error": True}
