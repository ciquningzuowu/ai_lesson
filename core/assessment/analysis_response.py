"""答案分析模块

接口：/agent/v1/analysis_answers (GET)

功能：分析学生的答案，给出反馈和学习建议。

输入：
1. question_id: 题目 id
2. course_id: 课程 id
3. courseware_id: 课件 id (可选)
4. student_id: 学生 id
5. answer: 学生的回答

输出：
1. analysis: 答案分析(str)
2. answer_condition: 学生学习情况分析(str)

内部逻辑：
依据 question_id 从数据库获取题目与答案，依据 course_id 从数据库获取课程解析，依据 student_id 从数据库获取学生学习状况，
依据这三份信息调用大语言模型生成答案分析，将答案分析返回后端。
"""

from typing import Optional
from pydantic import BaseModel, Field

from utils.llm_client import async_generate
from utils.database import Question, Quiz, Student, Course, Courseware, LearningProgress, LearningAnalytics
from utils.node_monitor import node_state


ANSWER_ANALYSIS_PROMPT = """你是一位专业的学习分析师，负责评估学生的答案并提供个性化反馈。

请根据以下信息分析学生的答案：

=== 题目信息 ===
题目内容：{question_content}
正确答案：{correct_answer}

=== 学生答案 ===
学生回答：{student_answer}

=== 课件解析 ===
{lesson_analysis}

=== 学生学习状况 ===
学习进度：{progress}%
平均得分：{avg_score}
完成测验数：{quiz_count}

请分析学生答案并提供：
1. 答案分析：指出答案的正确性、优缺点
2. 学习情况：分析学生对相关知识的掌握程度
3. 学习建议：提供针对性的改进建议

安全约束：
1. 回答内容控制在200-400字以内
2. 禁止任何歧视性、偏见性或不当言论
3. 保持客观公正的评价态度
4. 仅输出教育相关的内容

请以JSON格式返回：
{{
    "analysis": "答案详细分析",
    "answer_condition": "学习情况评估"
}}

请确保JSON格式正确。"""


CONDITION_ONLY_PROMPT = """请评估学生对以下题目的回答：

题目：{question_content}
正确答案：{correct_answer}
学生回答：{student_answer}

分析学生的回答，给出简要评估和后续学习建议。"""


class AnswerAnalysisResponse(BaseModel):
    """答案分析响应"""
    analysis: str = Field(..., description="答案分析")
    answer_condition: str = Field(..., description="学习情况")


async def get_question_info(question_id: int) -> Optional[dict]:
    """获取题目信息

    Args:
        question_id: 题目ID

    Returns:
        题目信息字典
    """
    question = await Question.get_or_none(id=question_id)
    if not question:
        return None

    return {
        "content": question.content,
        "answer": question.answer,
        "student_answer": question.student_answer,
    }


async def get_student_info(student_id: int) -> Optional[dict]:
    """获取学生信息

    Args:
        student_id: 学生ID

    Returns:
        学生信息字典
    """
    student = await Student.get_or_none(id=student_id)
    if not student:
        return None

    progress_obj = await LearningProgress.filter(student_id=student_id).first()
    progress = progress_obj.progress if progress_obj else 0

    quizzes = await Quiz.filter(student_id=student_id).count()
    analytics = await LearningAnalytics.filter(student_id=student_id).first()
    avg_score = analytics.status_data.get("avg_score", 0) if analytics and analytics.status_data else 0
    learning_style = analytics.status_data.get("learning_style") if analytics and analytics.status_data else None

    return {
        "name": student.name,
        "progress": progress,
        "avg_score": avg_score,
        "quiz_count": quizzes,
        "learning_style": learning_style,
    }


async def get_lesson_analysis(course_id: int, courseware_id: Optional[int] = None) -> Optional[dict]:
    """获取课件解析

    Args:
        course_id: 课程ID
        courseware_id: 课件ID（可选）

    Returns:
        课件解析字典
    """
    if courseware_id:
        courseware = await Courseware.get_or_none(id=courseware_id)
        if courseware and courseware.parse_result:
            return courseware.parse_result

    coursewares = await Courseware.filter(course_id=course_id).all()
    for cw in coursewares:
        if cw.parse_result:
            return cw.parse_result

    return None


async def analysis_answer(
    question_id: int,
    course_id: int,
    student_id: int,
    answer: str,
    courseware_id: Optional[int] = None,
) -> AnswerAnalysisResponse:
    """分析学生答案

    Args:
        question_id: 题目ID
        course_id: 课程ID
        student_id: 学生ID
        answer: 学生答案
        courseware_id: 课件ID（可选）

    Returns:
        分析响应
    """
    node_state(
        "assess.analysis",
        "entry",
        phase="enter",
        extra={"question_id": question_id, "course_id": course_id, "student_id": student_id},
        message="答案分析开始",
    )

    question_info = await get_question_info(question_id)
    if not question_info:
        node_state("assess.analysis", "no_question", phase="error", extra={"question_id": question_id})
        return AnswerAnalysisResponse(
            analysis="无法获取题目信息",
            answer_condition="系统错误",
        )

    lesson_analysis = await get_lesson_analysis(course_id, courseware_id)
    analysis_text = ""
    if lesson_analysis:
        analysis_text = lesson_analysis.get("summary", "")
        if not analysis_text:
            analysis_text = str(lesson_analysis)[:1000]

    student_info = await get_student_info(student_id)
    progress = 0
    avg_score = 0
    quiz_count = 0

    if student_info:
        progress = student_info["progress"]
        avg_score = student_info["avg_score"]
        quiz_count = student_info["quiz_count"]

    prompt = ANSWER_ANALYSIS_PROMPT.format(
        question_content=question_info["content"],
        correct_answer=question_info["answer"],
        student_answer=answer,
        lesson_analysis=analysis_text or "无课件解析",
        progress=progress,
        avg_score=avg_score,
        quiz_count=quiz_count,
    )

    node_state("assess.analysis", "llm_invoke", phase="checkpoint")
    result = await async_generate(prompt=prompt)
    node_state("assess.analysis", "llm_done", phase="checkpoint", extra={"raw_len": len(result)})

    import json
    try:
        data = json.loads(result)
        node_state("assess.analysis", "exit", phase="exit", message="JSON 解析成功")
        return AnswerAnalysisResponse(
            analysis=data.get("analysis", result),
            answer_condition=data.get("answer_condition", ""),
        )
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            try:
                data = json.loads(json_match.group())
                node_state("assess.analysis", "exit_regex", phase="exit", message="正则提取 JSON 成功")
                return AnswerAnalysisResponse(
                    analysis=data.get("analysis", result),
                    answer_condition=data.get("answer_condition", ""),
                )
            except json.JSONDecodeError:
                pass

        node_state("assess.analysis", "fallback_text", phase="checkpoint", message="JSON 失败，返回原文")
        return AnswerAnalysisResponse(
            analysis=result,
            answer_condition="请参考上方的详细分析",
        )


async def quick_analysis(
    question: str,
    correct_answer: str,
    student_answer: str,
) -> AnswerAnalysisResponse:
    """快速分析答案（不查询数据库）

    Args:
        question: 题目内容
        correct_answer: 正确答案
        student_answer: 学生答案

    Returns:
        分析响应
    """
    prompt = CONDITION_ONLY_PROMPT.format(
        question_content=question,
        correct_answer=correct_answer,
        student_answer=student_answer,
    )

    result = await async_generate(prompt=prompt)

    return AnswerAnalysisResponse(
        analysis=result,
        answer_condition="基于题目分析",
    )
