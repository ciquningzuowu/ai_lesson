"""节点与流水线状态监控

与 TaskProgress（Redis）配合：进度写入面向产品/前端，本模块面向日志检索与断点调试。
统一格式便于 grep：`[node][模块][节点][phase=...]`
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

_LOG = logging.getLogger("ai_lesson.pipeline")


def _truncate_extra(value: Any, max_len: int = 200) -> Any:
    if isinstance(value, str) and len(value) > max_len:
        return value[:max_len] + "…"
    return value


def node_state(
    module: str,
    node_id: str,
    *,
    phase: str = "checkpoint",
    task_id: Optional[str] = None,
    progress: Optional[float] = None,
    message: str = "",
    extra: Optional[Mapping[str, Any]] = None,
    level: str = "info",
) -> None:
    """记录流水线节点状态。

    Args:
        module: 逻辑模块名，如 ``content.parse``、``api.content``。
        node_id: 节点标识，如 ``parse_text_01``、``llm_invoke``。
        phase: ``enter`` | ``exit`` | ``checkpoint`` | ``error``。
        task_id: 与 TaskProgress 一致的任务 ID（可选）。
        progress: 与 TaskProgress 一致的百分比（可选）。
        message: 人类可读说明。
        extra: 附加键值（字符串会截断便于日志体量可控）。
        level: ``info`` 或 ``debug``（基础设施高频调用建议 debug）。
    """
    parts = [f"[node][{module}][{node_id}][phase={phase}]"]
    if task_id is not None:
        parts.append(f"[task={task_id}]")
    if progress is not None:
        parts.append(f"[progress={progress}%]")
    if message:
        parts.append(message)
    line = " ".join(parts)
    if extra:
        safe = {k: _truncate_extra(v) for k, v in extra.items()}
        line = f"{line} | extra={safe}"

    if phase == "error":
        _LOG.error("%s", line)
    elif level == "debug":
        _LOG.debug("%s", line)
    else:
        _LOG.info("%s", line)


def configure_application_logging(level: int = logging.INFO) -> None:
    """配置根日志（在 uvicorn 已配置时仅调整级别，避免重复 handler）。"""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        root.setLevel(level)
    logging.getLogger("ai_lesson.pipeline").setLevel(level)
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


__all__ = ["node_state", "configure_application_logging"]
