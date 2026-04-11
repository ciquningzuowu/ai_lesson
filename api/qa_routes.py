"""问答交互 API 路由

提供问答、流式回答等接口
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional

from models.qa_interaction import StreamAnswerRequest, StreamAnswerResponse
from core.qa_interaction.stream_answer import answer_question, stream_answer
from utils.helpers import ResponseFormatter
from utils.node_monitor import node_state
from utils.database import init_db, close_db, ensure_db

router = APIRouter(prefix="/agent/v1", tags=["问答交互"])


@router.post("/stream-answer", response_model=StreamAnswerResponse)
async def ask_question(request: StreamAnswerRequest):
    """回答学生问题

    接收学生问题，结合课程上下文与学生学习状况生成回答。

    Args:
        request: 问题请求

    Returns:
        回答文本
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        node_state(
            "api.qa",
            "stream_answer",
            phase="enter",
            extra={"student_id": request.student_id, "course_id": request.course_id},
        )
        result = await answer_question(
            student_id=request.student_id,
            course_id=request.course_id,
            question=request.question,
            courseware_id=request.courseware_id,
        )
        node_state("api.qa", "stream_answer", phase="exit")
        return result
    except Exception as e:
        node_state("api.qa", "stream_answer", phase="error", message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream-answer/stream")
async def ask_question_stream(request: StreamAnswerRequest):
    """流式回答学生问题

    Args:
        request: 问题请求

    Yields:
        回答文本片段
    """
    await ensure_db()  # 确保数据库已初始化

    async def stream_generator():
        node_state(
            "api.qa",
            "stream_answer_sse",
            phase="enter",
            extra={"student_id": request.student_id, "course_id": request.course_id},
        )
        async for chunk in stream_answer(
            student_id=request.student_id,
            course_id=request.course_id,
            question=request.question,
            courseware_id=request.courseware_id,
        ):
            yield f"data: {chunk}\n\n"
        node_state("api.qa", "stream_answer_sse", phase="exit")

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )


@router.get("/conversation-history/{student_id}")
async def get_conversation(
    student_id: int,
    course_id: Optional[int] = None,
    limit: int = 10,
):
    """获取对话历史

    Args:
        student_id: 学生ID
        course_id: 课程ID（可选）
        limit: 返回数量

    Returns:
        对话历史列表
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        from core.qa_interaction.stream_answer import get_conversation_history

        node_state("api.qa", "conversation_history", phase="enter", extra={"student_id": student_id, "course_id": course_id})
        history = await get_conversation_history(student_id, course_id, limit)
        node_state("api.qa", "conversation_history", phase="exit")

        return ResponseFormatter.success_response({
            "student_id": student_id,
            "course_id": course_id,
            "history": history,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
