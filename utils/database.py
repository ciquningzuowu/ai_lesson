"""数据库工具模块

核心功能：
- 异步数据库操作（使用 Tortoise ORM）
- Redis 缓存和任务队列支持
- 任务进度追踪

数据库模型已移至 models.database_models 模块：
- Teacher: 教师表
- Student: 学生表
- Course: 课程表
- Courseware: 课件表
- CoursewareVector: 课件向量表
- ChatHistory: 对话历史表
- LearningProgress: 学习进度表
- Quiz: 测验表
- Question: 题目表
- LearningAnalytics: 学习分析表
"""

import os
import json
import logging
from typing import Optional, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from tortoise import Tortoise
from tortoise.transactions import in_transaction
import redis.asyncio as redis

from config import DB_CONFIG as _DB_CONFIG, REDIS_CONFIG


# 从 models 模块导入数据库模型（保持向后兼容）
from models.database_models import (
    Teacher,
    Student,
    Course,
    Courseware,
    CoursewareVector,
    ChatHistory,
    LearningProgress,
    LearningAnalytics,
    Quiz,
    Question,
)


# ============= 数据库操作函数 =============

# 全局连接状态标志
_db_initialized = False


async def init_db():
    """初始化数据库连接（幂等操作）"""
    global _db_initialized

    if _db_initialized:
        # 检查连接是否仍然有效
        try:
            if Tortoise._connections and any(c is not None for c in Tortoise._connections.values()):
                return  # 连接有效，无需重新初始化
        except Exception as e:
            print(f"数据库连接问题：{e}")

    # 确保SQLite数据库文件所在目录存在（仅SQLite需要）
    if _DB_CONFIG.get("connections", {}).get("default", {}).get("engine") == "tortoise.backends.sqlite":
        db_path = _DB_CONFIG["connections"]["default"]["credentials"].get("file_path")
        if db_path:
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"确保数据库目录存在: {db_dir}")

    await Tortoise.init(config=_DB_CONFIG)
    # 不自动生成表结构，由外部迁移工具管理
    _db_initialized = True
    logger.info("数据库连接已初始化")


async def close_db():
    """关闭数据库连接"""
    global _db_initialized
    if _db_initialized:
        await Tortoise.close_connections()
        _db_initialized = False
        logger.info("数据库连接已关闭")


async def ensure_db():
    """确保数据库连接有效（可从路由中调用）

    使用实际查询验证连接状态，失效时自动重连。
    """
    global _db_initialized

    if not _db_initialized:
        await init_db()
        return

    # 尝试执行一个简单查询来验证连接
    try:
        # 使用 count() 验证连接是否可用（轻量级操作）
        await Teacher.all().count()
        return
    except Exception as e:
        logger.warning(f"数据库连接验证失败，准备重连: {e}")

    # 连接失效，强制重新初始化
    _db_initialized = False
    try:
        await Tortoise.close_connections()
    except Exception:
        pass
    await init_db()


@asynccontextmanager
async def get_db_session():
    """获取数据库会话上下文"""
    async with in_transaction():
        yield


# ============= Redis 工具 =============

class RedisCache:
    """Redis 缓存工具"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        """连接 Redis"""
        if self._client is None:
            cfg = {**REDIS_CONFIG, "decode_responses": True}
            self._client = redis.Redis(**cfg)

    async def close(self):
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        if self._client is None:
            await self.connect()
        return await self._client.get(key)

    async def set(self, key: str, value: Any, expire: int = 3600):
        """设置缓存值"""
        if self._client is None:
            await self.connect()
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        await self._client.set(key, value, ex=expire)

    async def delete(self, key: str):
        """删除缓存"""
        if self._client is None:
            await self.connect()
        await self._client.delete(key)

    async def get_json(self, key: str) -> Optional[Any]:
        """获取 JSON 缓存"""
        value = await self.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return json.loads(value)

    async def set_json(self, key: str, value: Any, expire: int = 3600):
        """设置 JSON 缓存"""
        await self.set(key, json.dumps(value, ensure_ascii=False), expire)


# ============= 任务进度追踪 =============

class TaskProgress:
    """任务进度追踪器"""

    def __init__(self, cache: RedisCache):
        self.cache = cache
        self.prefix = "task_progress:"

    async def set_progress(self, task_id: str, progress: float, message: str = ""):
        """设置任务进度"""
        data = {
            "task_id": task_id,
            "progress": progress,
            "message": message,
        }
        try:
            await self.cache.set_json(f"{self.prefix}{task_id}", data, expire=86400)
        except Exception as exc:
            logger.warning("任务进度写入 Redis 失败（已跳过）: %s", exc)

    async def get_progress(self, task_id: str) -> Optional[dict]:
        """获取任务进度"""
        try:
            return await self.cache.get_json(f"{self.prefix}{task_id}")
        except Exception as exc:
            logger.warning("任务进度读取 Redis 失败: %s", exc)
            return None

    async def delete_progress(self, task_id: str):
        """删除任务进度"""
        try:
            await self.cache.delete(f"{self.prefix}{task_id}")
        except Exception as exc:
            logger.warning("任务进度删除 Redis 失败: %s", exc)


# 全局 Redis 缓存实例
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """获取全局 Redis 缓存实例"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache


__all__ = [
    "init_db",
    "close_db",
    "ensure_db",
    "get_db_session",
    # 数据模型（从 models.database_models 导入）
    "Teacher",
    "Student",
    "Course",
    "Courseware",
    "CoursewareVector",
    "ChatHistory",
    "LearningProgress",
    "LearningAnalytics",
    "Quiz",
    "Question",
    # 工具类
    "RedisCache",
    "TaskProgress",
    "get_redis_cache",
]
