"""嵌入服务模块

核心功能：
- 提供统一的文本嵌入接口
- 支持多种嵌入模型（OpenAI、本地模型）
- 异步批处理支持
- 缓存嵌入结果

嵌入模型支持：
qwen-8b
"""

import os
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import EMBEDDING_CONFIG
from utils.node_monitor import node_state


class EmbeddingService:
    """嵌入服务类

    提供统一的文本嵌入接口，支持多种嵌入模型
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """初始化嵌入服务

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model_name: 模型名称
            timeout: 超时时间
        """
        self.api_key = api_key or EMBEDDING_CONFIG.get("api_key") or os.getenv("CHAT_API_KEY") or ""
        self.base_url = base_url or EMBEDDING_CONFIG.get("base_url", "")
        self.model_name = model_name or EMBEDDING_CONFIG.get("model_name", "qwen-8b")
        self.timeout = timeout

    async def embed_text(self, text: str) -> list[float]:
        """单条文本嵌入

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        node_state(
            "infra.embedding",
            "embed_text",
            phase="enter",
            level="debug",
            extra={"chars": len(text), "model": self.model_name},
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json={
                        "input": text,
                        "model": self.model_name,
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                vec = data["data"][0]["embedding"]
            node_state(
                "infra.embedding",
                "embed_text",
                phase="exit",
                level="debug",
                extra={"dim": len(vec)},
            )
            return vec
        except Exception as exc:
            node_state("infra.embedding", "embed_text", phase="error", message=str(exc))
            raise

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量文本嵌入

        Args:
            texts: 输入文本列表

        Returns:
            嵌入向量列表
        """
        node_state(
            "infra.embedding",
            "embed_texts",
            phase="enter",
            level="debug",
            extra={"batch": len(texts), "model": self.model_name},
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json={
                        "input": texts,
                        "model": self.model_name,
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                embeddings = sorted(data["data"], key=lambda x: x["index"])
                out = [item["embedding"] for item in embeddings]
            node_state(
                "infra.embedding",
                "embed_texts",
                phase="exit",
                level="debug",
                extra={"vectors": len(out)},
            )
            return out
        except Exception as exc:
            node_state("infra.embedding", "embed_texts", phase="error", message=str(exc))
            raise

    async def embed_lesson_content(self, content: str, title: str = "") -> list[float]:
        """课件内容嵌入

        将课件标题和内容拼接后进行嵌入

        Args:
            content: 课件内容
            title: 课件标题

        Returns:
            嵌入向量
        """
        combined_text = f"{title}\n{content}" if title else content
        node_state(
            "infra.embedding",
            "embed_lesson_content",
            phase="checkpoint",
            message="课件向量请求",
            extra={"title_len": len(title), "content_len": len(content)},
        )
        return await self.embed_text(combined_text)


# 全局嵌入服务实例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取全局嵌入服务实例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


async def embed_text(text: str) -> list[float]:
    """快捷函数：单条文本嵌入"""
    service = get_embedding_service()
    return await service.embed_text(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """快捷函数：批量文本嵌入"""
    service = get_embedding_service()
    return await service.embed_texts(texts)


async def embed_lesson_content(content: str, title: str = "") -> list[float]:
    """快捷函数：课件内容嵌入"""
    service = get_embedding_service()
    return await service.embed_lesson_content(content, title)


__all__ = [
    "EmbeddingService",
    "get_embedding_service",
    "embed_text",
    "embed_texts",
    "embed_lesson_content",
]
