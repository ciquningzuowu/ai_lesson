"""调整学习节奏模块

接口：/agent/v1/adjust-rhythm (POST)

功能：根据学生学习状况调整后续讲解的节奏和内容。

输入：
1. student_id: 学生 id
2. course_id: 课程 id (可选)

输出：
1. rhythm_signal: 节奏信号 (keep/up/supplement)
2. supplement_script: 补充讲解脚本（可选）

内部逻辑：
使用学生id获取学生学习状况、答题历史、问答历史
依据这三份信息调用大语言模型生成节奏调整策略，将节奏调整策略返回后端。
"""

from typing import Optional
from pydantic import BaseModel, Field

from utils.llm_client import async_generate
from utils.database import (
    Student,
    Quiz,
    Question,
    ChatHistory,
    LearningProgress,
    LearningAnalytics,
)
from utils.node_monitor import node_state


RHYTHM_ADJUSTMENT_PROMPT = """你是智能学习节奏调整助手，负责分析学生的学习状态并调整教学节奏。

=== 学生学习状况 ===
学生ID：{student_id}
学习进度：{progress}%
完成测验数：{quizzes_completed}
历史平均分：{avg_score}
学习风格：{learning_style}

=== 答题历史（最近5次）===
{quiz_history}

=== 问答历史（最近5次）===
{qa_history}

请分析学生的学习状态，判断应该进行的节奏调整策略：

节奏信号定义：
- keep: 保持当前节奏，学习状态良好
- up: 加速，学习者掌握较快，可以推进
- supplement: 需要补充讲解，学习者可能存在理解困难

分析要点：
1. 历史答题正确率
2. 问答中反复出现的知识点
3. 学习进度与掌握程度的匹配度
4. 需要加强的薄弱环节

安全约束：
- 仅输出教育相关的内容
- 禁止任何歧视性、偏见性或不当言论
- 保持客观公正的评价态度

请以JSON格式返回：
{{
    "rhythm_signal": "keep/up/supplement",
    "supplement_script": "补充讲解脚本（仅当rhythm_signal为supplement时需要填写）",
    "reasoning": "判断理由"
}}

请确保JSON格式正确。"""


SUPPLEMENT_SCRIPT_PROMPT = """根据学生学习中的薄弱环节，请生成补充讲解脚本。

=== 需要补充的知识点 ===
{weak_points}

=== 原课件摘要 ===
{lesson_summary}

=== 学生学习状况 ===
学习风格：{learning_style}

请生成一段针对薄弱环节的补充讲解，要求：
1. 解释清晰，举例说明
2. 难度适中，符合学生水平
3. 长度约300-500字
4. 语言生动，便于理解

安全约束：
- 禁止生成任何涉及政治敏感、个人隐私或不当内容
- 保持客观专业的教育态度

请直接输出脚本内容。"""


class RhythmAdjustmentResponse(BaseModel):
    """节奏调整响应"""
    rhythm_signal: str = Field(..., description="节奏信号: keep/up/supplement")
    supplement_script: Optional[str] = Field(default=None, description="补充讲解脚本")


async def get_student_learning_status(student_id: int) -> dict:
    """获取学生学习状态

    Args:
        student_id: 学生ID

    Returns:
        学习状态字典
    """
    node_state("adapt.rhythm", "db_student", phase="checkpoint", level="debug", extra={"student_id": student_id})
    student = await Student.get_or_none(id=student_id)
    if not student:
        return {
            "student_id": student_id,
            "progress": 0,
            "lessons_completed": 0,
            "quizzes_completed": 0,
            "avg_score": 0,
            "learning_style": "综合",
        }

    progress_obj = await LearningProgress.filter(student_id=student_id).first()
    progress = progress_obj.progress if progress_obj else 0

    quizzes = await Quiz.filter(student_id=student_id).count()
    analytics = await LearningAnalytics.filter(student_id=student_id).first()
    avg_score = analytics.status_data.get("avg_score", 0) if analytics and analytics.status_data else 0
    learning_style = analytics.status_data.get("learning_style", "综合") if analytics and analytics.status_data else "综合"

    return {
        "student_id": student_id,
        "progress": progress,
        "lessons_completed": progress // 10,
        "quizzes_completed": quizzes,
        "avg_score": avg_score,
        "learning_style": learning_style,
    }


async def get_quiz_history(student_id: int, limit: int = 5) -> str:
    """获取答题历史

    Args:
        student_id: 学生ID
        limit: 返回数量

    Returns:
        格式化的问题历史字符串
    """
    node_state("adapt.rhythm", "db_quiz_history", phase="checkpoint", level="debug", extra={"student_id": student_id, "limit": limit})
    quizzes = await Quiz.filter(student_id=student_id).order_by("-create_time").limit(limit)

    history_parts = []
    for quiz in quizzes:
        questions = await Question.filter(quiz_id=quiz.id).all()
        for q in questions:
            status = "正确" if q.is_correct else "错误"
            student_ans = q.student_answer or "未作答"
            history_parts.append(
                f"- 题目: {q.content[:50]}... | 学生答案: {student_ans[:30]}... | {status}"
            )

    return "\n".join(history_parts) if history_parts else "暂无答题历史"


async def get_qa_history(student_id: int, limit: int = 5) -> str:
    """获取问答历史

    Args:
        student_id: 学生ID
        limit: 返回数量

    Returns:
        格式化的问答历史字符串
    """
    node_state("adapt.rhythm", "db_qa_history", phase="checkpoint", level="debug", extra={"student_id": student_id, "limit": limit})
    conversations = await ChatHistory.filter(student_id=student_id).order_by("-timestamp").limit(limit)

    history_parts = []
    for conv in conversations:
        history_parts.append(
            f"- Q: {conv.question[:50]}... | A: {conv.answer[:50] if conv.answer else '未回复'}..."
        )

    return "\n".join(history_parts) if history_parts else "暂无问答历史"


async def adjust_rhythm(student_id: int, course_id: Optional[int] = None) -> RhythmAdjustmentResponse:
    """调整学习节奏

    Args:
        student_id: 学生ID
        course_id: 课程ID（可选）

    Returns:
        节奏调整响应
    """
    node_state("adapt.rhythm", "adjust_entry", phase="enter", extra={"student_id": student_id}, message="节奏调整开始")

    status = await get_student_learning_status(student_id)
    quiz_history = await get_quiz_history(student_id)
    qa_history = await get_qa_history(student_id)
    node_state(
        "adapt.rhythm",
        "context_ready",
        phase="checkpoint",
        extra={
            "student_id": student_id,
            "progress": status.get("progress"),
            "quizzes": status.get("quizzes_completed"),
        },
        message="学习画像与历史已聚合",
    )

    prompt = RHYTHM_ADJUSTMENT_PROMPT.format(
        student_id=student_id,
        progress=status["progress"],
        lessons_completed=status["lessons_completed"],
        quizzes_completed=status["quizzes_completed"],
        avg_score=status["avg_score"],
        learning_style=status["learning_style"],
        quiz_history=quiz_history,
        qa_history=qa_history,
    )

    node_state("adapt.rhythm", "llm_invoke", phase="checkpoint", message="调用 LLM 生成节奏策略")
    result = await async_generate(prompt=prompt)
    node_state("adapt.rhythm", "llm_done", phase="checkpoint", extra={"raw_len": len(result)})

    import json
    import re

    try:
        data = json.loads(result)
        rhythm_signal = data.get("rhythm_signal", "keep")
        supplement_script = data.get("supplement_script")

        if rhythm_signal == "supplement" and not supplement_script:
            node_state("adapt.rhythm", "supplement_branch", message="生成补充脚本")
            supplement_script = await _generate_supplement_script(student_id)

        node_state(
            "adapt.rhythm",
            "adjust_exit",
            phase="exit",
            extra={"rhythm_signal": rhythm_signal, "has_supplement": bool(supplement_script)},
        )
        return RhythmAdjustmentResponse(
            rhythm_signal=rhythm_signal,
            supplement_script=supplement_script,
        )
    except json.JSONDecodeError:
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            try:
                data = json.loads(json_match.group())
                rhythm_signal = data.get("rhythm_signal", "keep")
                supplement_script = data.get("supplement_script")

                if rhythm_signal == "supplement" and not supplement_script:
                    supplement_script = await _generate_supplement_script(student_id)

                node_state(
                    "adapt.rhythm",
                    "adjust_exit_regex",
                    phase="exit",
                    extra={"rhythm_signal": rhythm_signal, "has_supplement": bool(supplement_script)},
                )
                return RhythmAdjustmentResponse(
                    rhythm_signal=rhythm_signal,
                    supplement_script=supplement_script,
                )
            except json.JSONDecodeError:
                pass

    node_state("adapt.rhythm", "fallback_keep", phase="checkpoint", message="JSON 解析失败，默认 keep")
    return RhythmAdjustmentResponse(
        rhythm_signal="keep",
        supplement_script=None,
    )


async def _generate_supplement_script(student_id: int) -> Optional[str]:
    """生成补充讲解脚本

    Args:
        student_id: 学生ID

    Returns:
        补充讲解脚本
    """
    status = await get_student_learning_status(student_id)
    quiz_history = await get_quiz_history(student_id, limit=3)

    weak_points = "根据答题历史，可能存在理解不透彻的知识点，建议加强基础概念的讲解。"

    prompt = SUPPLEMENT_SCRIPT_PROMPT.format(
        weak_points=weak_points,
        lesson_summary="核心知识点讲解",
        learning_style=status["learning_style"],
    )

    return await async_generate(prompt=prompt)


async def quick_adjust(
    quiz_accuracy: float,
    avg_response_quality: str = "一般",
) -> RhythmAdjustmentResponse:
    """快速节奏调整（不查询数据库）

    Args:
        quiz_accuracy: 答题正确率 (0-1)
        avg_response_quality: 平均回答质量

    Returns:
        节奏调整响应
    """
    if quiz_accuracy >= 0.8:
        return RhythmAdjustmentResponse(
            rhythm_signal="up",
            supplement_script=None,
        )
    elif quiz_accuracy >= 0.5:
        return RhythmAdjustmentResponse(
            rhythm_signal="keep",
            supplement_script=None,
        )
    else:
        prompt = """学生学习效果不佳，请生成一段补充讲解脚本，帮助学生理解基础知识。

要求：
1. 内容简洁明了，易于理解
2. 长度控制在200-300字
3. 语言专业且友好
4. 优先讲解核心基础概念

安全约束：
- 仅输出教育相关的内容
- 禁止任何不当言论

请直接输出脚本内容。"""

        return RhythmAdjustmentResponse(
            rhythm_signal="supplement",
            supplement_script=await async_generate(prompt=prompt),
        )
