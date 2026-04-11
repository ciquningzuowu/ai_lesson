"""学习适应 API 路由

提供节奏调整等接口
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from models.learning_adaptation import (
    AdjustRhythmRequest,
    AdjustRhythmResponse,
)
from core.learning_adaptation.adjust_rhythm import adjust_rhythm
from utils.helpers import ResponseFormatter
from utils.node_monitor import node_state
from utils.database import init_db, close_db, ensure_db

router = APIRouter(prefix="/agent/v1", tags=["学习适应"])


@router.post("/adjust-rhythm", response_model=AdjustRhythmResponse)
async def adjust_learning_rhythm(request: AdjustRhythmRequest):
    """调整学习节奏

    根据学生学习状况调整后续讲解的节奏和内容。

    Args:
        request: 调整请求

    Returns:
        节奏调整信号和补充脚本
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        node_state("api.adapt", "adjust_rhythm", phase="enter", extra={"student_id": request.student_id})
        result = await adjust_rhythm(student_id=request.student_id, course_id=request.course_id)
        node_state("api.adapt", "adjust_rhythm", phase="exit", extra={"signal": str(result.rhythm_signal)})
        return result
    except Exception as e:
        node_state("api.adapt", "adjust_rhythm", phase="error", message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student-status/{student_id}")
async def get_student_status(student_id: int):
    """获取学生学习状态

    Args:
        student_id: 学生ID

    Returns:
        学生学习状态
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        from core.learning_adaptation.adjust_rhythm import get_student_learning_status

        node_state("api.adapt", "student_status", phase="enter", extra={"student_id": student_id})
        status = await get_student_learning_status(student_id)
        node_state("api.adapt", "student_status", phase="exit")

        return ResponseFormatter.success_response(status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quiz-history/{student_id}")
async def get_quiz_history(student_id: int, limit: int = 5):
    """获取答题历史

    Args:
        student_id: 学生ID
        limit: 返回数量

    Returns:
        答题历史
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        from core.learning_adaptation.adjust_rhythm import get_quiz_history

        node_state("api.adapt", "quiz_history", phase="enter", extra={"student_id": student_id, "limit": limit})
        history = await get_quiz_history(student_id, limit)
        node_state("api.adapt", "quiz_history", phase="exit")

        return ResponseFormatter.success_response({
            "student_id": student_id,
            "history": history,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qa-history/{student_id}")
async def get_qa_history(student_id: int, limit: int = 5):
    """获取问答历史

    Args:
        student_id: 学生ID
        limit: 返回数量

    Returns:
        问答历史
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        from core.learning_adaptation.adjust_rhythm import get_qa_history

        node_state("api.adapt", "qa_history", phase="enter", extra={"student_id": student_id, "limit": limit})
        history = await get_qa_history(student_id, limit)
        node_state("api.adapt", "qa_history", phase="exit")

        return ResponseFormatter.success_response({
            "student_id": student_id,
            "history": history,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
