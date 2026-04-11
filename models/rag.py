"""RAG 服务相关的数据模型

定义检索增强生成所需的类结构。
"""

from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import math


@dataclass
class TextChunk:
    """文本块"""
    content: str
    index: int
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class TextSplitter:
    """文本分割器

    将长文本分割成较小的块，便于嵌入和检索
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", ".", "!", "?"]

    def split_text(self, text: str, source: str = "") -> List[TextChunk]:
        """分割文本"""
        chunks = []
        paragraphs = self._split_by_separators(text, self.separators[0])

        current_chunk = ""
        index = 0

        for para in paragraphs:
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(TextChunk(
                        content=current_chunk.strip(),
                        index=index,
                        source=source,
                    ))
                    index += 1

                while len(para) > self.chunk_size:
                    for sep in self.separators[1:]:
                        sub_parts = para.split(sep)
                        if len(sub_parts) > 1:
                            break

                    chunks.append(TextChunk(
                        content=para[:self.chunk_size],
                        index=index,
                        source=source,
                    ))
                    index += 1
                    para = para[self.chunk_size - self.chunk_overlap:]

                current_chunk = para + "\n"

        if current_chunk.strip():
            chunks.append(TextChunk(
                content=current_chunk.strip(),
                index=index,
                source=source,
            ))

        return chunks

    def _split_by_separators(self, text: str, separator: str) -> List[str]:
        """按分隔符分割"""
        if not separator:
            return [text]
        parts = text.split(separator)
        return [p + separator for p in parts[:-1]] + [parts[-1]] if parts else [text]


class VectorStore:
    """向量存储

    简单的内存向量存储，支持添加、检索操作
    """

    def __init__(self):
        self.chunks: List[TextChunk] = []
        self.embeddings: List[List[float]] = []

    def add_chunks(self, chunks: List[TextChunk], embeddings: List[List[float]]):
        """添加文本块和对应的嵌入向量"""
        self.chunks.extend(chunks)
        self.embeddings.extend(embeddings)

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[Tuple[TextChunk, float]]:
        """相似度搜索"""
        scores = self._cosine_similarity(query_embedding, self.embeddings)
        scored_chunks = sorted(
            zip(self.chunks, scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        if score_threshold:
            scored_chunks = [(c, s) for c, s in scored_chunks if s >= score_threshold]

        return scored_chunks

    def _cosine_similarity(
        self,
        vec1: List[float],
        vecs: List[List[float]],
    ) -> List[float]:
        """计算余弦相似度"""

        def normalize(v: List[float]) -> List[float]:
            norm = math.sqrt(sum(x * x for x in v))
            return [x / norm for x in v] if norm > 0 else v

        norm_vec1 = normalize(vec1)
        scores = []
        for vec in vecs:
            norm_vec = normalize(vec)
            score = sum(a * b for a, b in zip(norm_vec1, norm_vec))
            scores.append(score)
        return scores

    def clear(self):
        """清空向量存储"""
        self.chunks = []
        self.embeddings = []

    def __len__(self):
        return len(self.chunks)


class RAGService:
    """RAG 服务

    检索增强生成服务
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ):
        self.splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.vector_store = VectorStore()
        self.top_k = top_k
        self.score_threshold = score_threshold

    def index_content(self, content: str, source: str = "") -> List[TextChunk]:
        """索引内容（同步）

        注意：此方法使用 asyncio.run() 在同步上下文中创建事件循环，
        仅适用于单次调用场景。优先使用 aindex_content() 异步方法。
        """
        import asyncio
        from utils.embeddings import embed_texts

        chunks = self.splitter.split_text(content, source)
        texts = [chunk.content for chunk in chunks]
        # 使用 run_in_executor 在线程池中运行，避免阻塞事件循环
        loop = asyncio.new_event_loop()
        try:
            embeddings = loop.run_until_complete(embed_texts(texts))
        finally:
            loop.close()
        self.vector_store.add_chunks(chunks, embeddings)
        return chunks

    async def aindex_content(self, content: str, source: str = "") -> List[TextChunk]:
        """异步索引内容"""
        from utils.embeddings import embed_texts
        from utils.node_monitor import node_state

        node_state(
            "infra.rag",
            "aindex_enter",
            phase="enter",
            extra={"source": source, "content_chars": len(content)},
        )
        chunks = self.splitter.split_text(content, source)
        texts = [chunk.content for chunk in chunks]
        node_state("infra.rag", "aindex_split", phase="checkpoint", extra={"chunks": len(chunks)})
        embeddings = await embed_texts(texts)
        self.vector_store.add_chunks(chunks, embeddings)
        node_state("infra.rag", "aindex_exit", phase="exit", extra={"vectors": len(embeddings)})
        return chunks

    async def retrieve(self, query: str, top_k: Optional[int] = None) -> List[TextChunk]:
        """检索相关内容"""
        from utils.embeddings import embed_text
        from utils.node_monitor import node_state

        node_state(
            "infra.rag",
            "retrieve_enter",
            phase="enter",
            level="debug",
            extra={"q_len": len(query), "store_chunks": len(self.vector_store.chunks)},
        )
        query_embedding = await embed_text(query)
        top_k = top_k or self.top_k

        results = self.vector_store.similarity_search(
            query_embedding,
            top_k=top_k,
            score_threshold=self.score_threshold,
        )

        out = [chunk for chunk, _ in results]
        node_state(
            "infra.rag",
            "retrieve_exit",
            phase="exit",
            level="debug",
            extra={"hits": len(out), "top_k": top_k},
        )
        return out

    def build_context(self, chunks: List[TextChunk]) -> str:
        """构建检索上下文"""
        if not chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            part = f"[{i}] {chunk.content}"
            if chunk.source:
                part += f"\n来源: {chunk.source}"
            context_parts.append(part)

        return "\n\n".join(context_parts)

    def build_rag_prompt(
        self,
        query: str,
        system_prompt: str = "",
        async_retrieve_func=None,
    ) -> str:
        """构建 RAG 提示词（同步版本）

        Args:
            query: 查询文本
            system_prompt: 系统提示词模板，支持 {context} 和 {question} 占位符
            async_retrieve_func: 异步检索函数，在已有事件循环中调用

        注意：此方法尝试复用当前事件循环，避免创建新循环导致 Tortoise 上下文丢失。
        如果没有可用的事件循环且未提供 async_retrieve_func，返回不含上下文的提示词。
        """
        import asyncio
        import functools

        # 尝试在现有事件循环中执行异步检索
        try:
            loop = asyncio.get_running_loop()
            if async_retrieve_func is not None:
                # 使用提供的异步函数获取检索结果
                future = asyncio.ensure_future(async_retrieve_func(query))
                chunks = loop.run_until_complete(future)
            else:
                # 使用自身的 retrieve 方法（需要事件循环）
                future = asyncio.ensure_future(self.retrieve(query))
                chunks = loop.run_until_complete(future)
        except RuntimeError:
            # 没有正在运行的事件循环，使用同步检索
            chunks = self._sync_retrieve(query)
        except Exception:
            # 其他异常，返回空上下文
            chunks = []

        if not chunks:
            if "{context}" in system_prompt:
                return system_prompt.format(question=query, context="未找到相关内容")
            return query

        context = self.build_context(chunks)
        prompt = system_prompt
        prompt = prompt.replace("{context}", context)
        prompt = prompt.replace("{question}", query)
        return prompt

    def _sync_retrieve(self, query: str, top_k: Optional[int] = None) -> List[TextChunk]:
        """同步检索（不使用 asyncio.run，避免丢失 Tortoise 上下文）

        通过 HTTP API 或其他方式实现同步检索。
        当前实现返回空列表，上层调用应优先使用异步方法。
        """
        import asyncio
        from utils.embeddings import embed_text

        loop = asyncio.new_event_loop()
        try:
            query_embedding = loop.run_until_complete(embed_text(query))
        finally:
            loop.close()

        top_k = top_k or self.top_k
        results = self.vector_store.similarity_search(
            query_embedding,
            top_k=top_k,
            score_threshold=self.score_threshold,
        )
        return [chunk for chunk, _ in results]

    async def abuild_rag_prompt(
        self,
        query: str,
        system_prompt: str = "",
    ) -> str:
        """异步构建 RAG 提示词"""
        chunks = await self.retrieve(query)

        if not chunks:
            return system_prompt.format(question=query, context="未找到相关内容") if "{context}" in system_prompt else query

        context = self.build_context(chunks)
        prompt = system_prompt
        prompt = prompt.replace("{context}", context)
        prompt = prompt.replace("{question}", query)
        return prompt


# 全局 RAG 服务实例
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """获取全局 RAG 服务实例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
