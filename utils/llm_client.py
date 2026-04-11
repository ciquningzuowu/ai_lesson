"""LLM 客户端模块

使用 LangChain ``init_chat_model`` 统一注册聊天模型（OpenAI 兼容），供全项目 ``async_generate`` / ``astream`` 及后续 Agent/工具绑定使用。
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator, Optional, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from config import LLM_CONFIG
from utils.node_monitor import node_state


def _resolve_api_key() -> Optional[str]:
    key = os.getenv("CHAT_API_KEY") or LLM_CONFIG.get("CHAT_API_KEY")
    if key:
        return str(key).strip() or None
    return None


def _stringify_content(content: Any) -> str:
    """将 AIMessage / chunk 的 content 转为纯文本（兼容多模态块列表）。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                t = block.get("text")
                if isinstance(t, str):
                    parts.append(t)
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


_llm_instance: Optional[BaseChatModel] = None


def get_llm() -> BaseChatModel:
    """获取全局 Chat 模型（单例），由 ``init_chat_model`` 构建。"""
    global _llm_instance
    if _llm_instance is None:
        try:
            from langchain.chat_models import init_chat_model
        except ImportError as e:
            raise ImportError(
                "需要安装 langchain 与 langchain-openai：pip install langchain langchain-openai"
            ) from e

        kwargs: dict[str, Any] = {
            "temperature": LLM_CONFIG["temperature"],
            "max_tokens": LLM_CONFIG["max_tokens"],
            "timeout": LLM_CONFIG["timeout"],
            "max_retries": LLM_CONFIG["max_retries"],
        }
        base_url = LLM_CONFIG.get("base_url")
        if base_url:
            kwargs["base_url"] = base_url
        api_key = _resolve_api_key()
        if api_key:
            kwargs["api_key"] = api_key
        # 未传 api_key 时 ChatOpenAI 会读取环境变量 CHAT_API_KEY

        _llm_instance = init_chat_model(
            LLM_CONFIG["model"],
            model_provider=LLM_CONFIG["model_provider"],
            **kwargs,
        )
    return _llm_instance


def get_chat_model() -> BaseChatModel:
    """与 ``get_llm`` 同义，便于与 LangChain Agent/工具链命名一致。"""
    return get_llm()


async def async_generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """异步生成文本（基于 ``ainvoke``）。"""
    node_state(
        "infra.llm",
        "async_generate",
        phase="enter",
        extra={
            "prompt_chars": len(prompt),
            "has_system": bool(system_prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )
    llm = get_llm()
    messages: list[BaseMessage] = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    # bind() 返回 Runnable 链，仍支持 ainvoke(messages)
    bound: Union[BaseChatModel, Any] = llm
    bind_kw: dict[str, Any] = {}
    if temperature is not None:
        bind_kw["temperature"] = temperature
    if max_tokens is not None:
        bind_kw["max_tokens"] = max_tokens
    if bind_kw:
        bound = llm.bind(**bind_kw)

    try:
        ai_msg = await bound.ainvoke(messages)
        text = _stringify_content(getattr(ai_msg, "content", ai_msg))
        node_state(
            "infra.llm",
            "async_generate",
            phase="exit",
            extra={"out_chars": len(text) if text else 0},
        )
        return text
    except Exception as exc:
        node_state("infra.llm", "async_generate", phase="error", message=str(exc))
        raise


async def async_stream_generate(
    prompt: str,
    system_prompt: Optional[str] = None,
) -> AsyncIterator[str]:
    """异步流式生成文本片段。"""
    node_state(
        "infra.llm",
        "async_stream_generate",
        phase="enter",
        extra={"prompt_chars": len(prompt), "has_system": bool(system_prompt)},
    )
    llm = get_llm()
    messages: list[BaseMessage] = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    total = 0
    try:
        async for chunk in llm.astream(messages):
            piece = _stringify_content(getattr(chunk, "content", chunk))
            if piece:
                total += len(piece)
                yield piece
        node_state(
            "infra.llm",
            "async_stream_generate",
            phase="exit",
            extra={"stream_chars": total},
        )
    except Exception as exc:
        node_state("infra.llm", "async_stream_generate", phase="error", message=str(exc))
        raise


__all__ = ["get_llm", "get_chat_model", "async_generate", "async_stream_generate"]
