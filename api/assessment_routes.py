"""评估测验 API 路由

提供答案分析、测验生成等接口
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from models.assessment import (
    AnalysisRequest,
    AnalysisResponse,
    GenerateQuizRequest,
    GenerateQuizResponse,
)
from core.assessment.analysis_response import analysis_answer
from core.assessment.generate_quiz import generate_quiz
from utils.helpers import ResponseFormatter
from utils.node_monitor import node_state
from utils.database import init_db, close_db, ensure_db

router = APIRouter(prefix="/agent/v1", tags=["评估测验"])


@router.get("/analysis_answers", response_model=AnalysisResponse)
async def analyze_answer(
    question_id: int,
    course_id: int,
    student_id: int,
    answer: str,
    courseware_id: Optional[int] = None,
):
    """分析学生答案

    分析学生的答案，给出反馈和学习建议。

    Args:
        question_id: 题目ID
        course_id: 课程ID
        student_id: 学生ID
        answer: 学生的回答
        courseware_id: 课件ID（可选）

    Returns:
        答案分析和学习情况
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        node_state(
            "api.assess",
            "analysis_answers",
            phase="enter",
            extra={"question_id": question_id, "course_id": course_id, "student_id": student_id},
        )
        result = await analysis_answer(
            question_id=question_id,
            course_id=course_id,
            student_id=student_id,
            answer=answer,
            courseware_id=courseware_id,
        )
        node_state("api.assess", "analysis_answers", phase="exit")
        return result
    except Exception as e:
        node_state("api.assess", "analysis_answers", phase="error", message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-quiz", response_model=GenerateQuizResponse)
async def create_quiz(request: GenerateQuizRequest):
    """生成测验题目

    为当前章节生成测验题目。

    Args:
        request: 生成测验请求

    Returns:
        题目列表和答案列表
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        node_state("api.assess", "generate_quiz", phase="enter", extra={"course_id": request.course_id})
        result = await generate_quiz(request)
        node_state("api.assess", "generate_quiz", phase="exit")
        return result
    except Exception as e:
        node_state("api.assess", "generate_quiz", phase="error", message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quiz-record/{quiz_id}")
async def get_quiz_record(quiz_id: int):
    """获取测验记录

    Args:
        quiz_id: 测验ID

    Returns:
        测验记录
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        from utils.database import Quiz, Question

        node_state("api.assess", "quiz_record", phase="enter", extra={"quiz_id": quiz_id})
        quiz = await Quiz.get_or_none(id=quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="测验不存在")

        questions = await Question.filter(quiz_id=quiz_id)
        node_state("api.assess", "quiz_record", phase="exit", extra={"questions": len(questions)})

        return ResponseFormatter.success_response({
            "quiz_id": quiz_id,
            "course_id": quiz.course_id,
            "student_id": quiz.student_id,
            "questions": questions,
            "score": quiz.score,
            "created_at": quiz.create_time.isoformat() if quiz.create_time else None,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-quiz")
async def submit_quiz(quiz_id: int, answers: list[dict]):
    """提交测验答案

    Args:
        quiz_id: 测验ID
        answers: 答案列表 [{"question_id": 1, "answer": "xxx"}]

    Returns:
        提交结果
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        from utils.database import Quiz, Question
        from datetime import datetime

        node_state("api.assess", "submit_quiz", phase="enter", extra={"quiz_id": quiz_id, "answers": len(answers)})
        quiz = await Quiz.get_or_none(id=quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="测验不存在")

        for ans in answers:
            question_id = ans.get("question_id")
            student_answer = ans.get("answer")

            question = await Question.get_or_none(id=question_id, quiz_id=quiz_id)
            if question:
                question.student_answer = student_answer
                question.is_correct = (student_answer == question.answer)
                question.submitted_at = datetime.now()
                await question.save()

        all_questions = await Question.filter(quiz_id=quiz_id)
        correct_count = sum(1 for q in all_questions if q.is_correct)
        score = (correct_count / len(all_questions) * 100) if all_questions else 0

        quiz.score = score
        await quiz.save()
        node_state("api.assess", "submit_quiz", phase="exit", extra={"score": score})

        return ResponseFormatter.success_response({
            "quiz_id": quiz_id,
            "score": score,
            "correct_count": correct_count,
            "total_count": len(all_questions),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
