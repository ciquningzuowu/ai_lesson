"""数据库工具模块

核心功能：
- 异步数据库操作（使用 Tortoise ORM）
- 任务进度追踪（已移除 Redis，改为内存追踪）

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
import logging
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from tortoise import Tortoise
from tortoise.transactions import in_transaction

from config import DB_CONFIG as _DB_CONFIG


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
        except Exception:
            pass

    os.makedirs(".", exist_ok=True)
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


# 内存任务进度追踪（替代 Redis）
_task_progress: dict[str, dict] = {}


async def set_task_progress(task_id: str, progress: float, message: str = ""):
    """设置任务进度（内存存储）"""
    _task_progress[task_id] = {
        "task_id": task_id,
        "progress": progress,
        "message": message,
    }


async def get_task_progress(task_id: str) -> Optional[dict]:
    """获取任务进度（内存存储）"""
    return _task_progress.get(task_id)


async def delete_task_progress(task_id: str):
    """删除任务进度（内存存储）"""
    if task_id in _task_progress:
        del _task_progress[task_id]


__all__ = [
    "init_db",
    "close_db",
    "ensure_db",
    "get_db_session",
    "set_task_progress",
    "get_task_progress",
    "delete_task_progress",
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
]
