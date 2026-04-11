"""生成测验模块

接口：/agent/v1/generate-quiz (POST)

功能：为当前章节生成测验题目。

输入：
1. course_id: 课程 id
2. courseware_id: 课件 id (可选)
3. student_id: 学生 id
4. num: 题目数量
5. type: 题目类型 (fill_blank/qa)

输出：
1. questions: 题目列表(list[str])
2. answers: 答案列表(list[str])

内部逻辑：
依据 course_id 从数据库获取课程解析，依据student_id从数据库获取学生学习状况，
依据这两份信息调用大语言模型生成题目与答案，将题目与答案返回后端。
"""

from typing import Optional
from pydantic import BaseModel, Field
import json

from utils.llm_client import async_generate
from utils.database import Course, Courseware, Student, LearningProgress, LearningAnalytics
from utils.node_monitor import node_state
from models.assessment import (
    GenerateQuizRequest,
    GenerateQuizResponse,
    QuestionType,
)


FILL_BLANK_QUIZ_PROMPT = """你是一位专业的测验题目设计专家。请根据课件内容生成填空题。

=== 课件内容 ===
{lesson_content}

=== 学习者画像 ===
学习进度：{progress}%
历史平均分：{avg_score}
学习风格：{learning_style}

请生成 {num} 道填空题，要求：
1. 覆盖课件的主要知识点
2. 难度适中，适合学习者水平
3. 答案唯一且明确
4. 每道题留出空位用_____表示

请以JSON格式返回：
{{
    "questions": ["题目1_____答案1", "题目2_____答案2", ...],
    "answers": ["答案1", "答案2", ...]
}}

请确保JSON格式正确，可以被解析。"""


QA_QUIZ_PROMPT = """你是一位专业的测验题目设计专家。请根据课件内容生成问答题。

=== 课件内容 ===
{lesson_content}

=== 学习者画像 ===
学习进度：{progress}%
历史平均分：{avg_score}
学习风格：{learning_style}

请生成 {num} 道问答题，要求：
1. 覆盖课件的主要知识点
2. 考察理解与应用能力，而非单纯记忆
3. 适合学习者水平，难度适中
4. 问题清晰明确，答案有要点可循

请以JSON格式返回：
{{
    "questions": ["问题1", "问题2", ...],
    "answers": ["答案要点1|答案要点2|...", ...]
}}

请确保JSON格式正确，可以被解析。"""


async def get_lesson_content(course_id: int, courseware_id: Optional[int] = None) -> Optional[str]:
    """获取课件内容

    Args:
        course_id: 课程ID
        courseware_id: 课件ID（可选）

    Returns:
        课件内容字符串
    """
    if courseware_id:
        courseware = await Courseware.get_or_none(id=courseware_id)
        if courseware:
            if courseware.parse_result:
                content = courseware.parse_result.get("summary", "")
                if content:
                    return content
                key_concepts = courseware.parse_result.get("key_concepts", [])
                teaching_obj = courseware.parse_result.get("teaching_objectives", [])
                if key_concepts or teaching_obj:
                    return f"主要概念：{', '.join(key_concepts)}\n教学目标：{', '.join(teaching_obj)}"
            return courseware.content[:3000] if courseware.content else ""

    coursewares = await Courseware.filter(course_id=course_id).all()
    if coursewares:
        combined = []
        for cw in coursewares:
            if cw.parse_result:
                summary = cw.parse_result.get("summary", "")
                if summary:
                    combined.append(f"[{cw.title}]: {summary}")
        if combined:
            return "\n".join(combined)

        first_cw = coursewares[0]
        return first_cw.content[:3000] if first_cw.content else ""

    return None


async def get_student_profile(student_id: int) -> dict:
    """获取学生画像

    Args:
        student_id: 学生ID

    Returns:
        学生画像字典
    """
    student = await Student.get_or_none(id=student_id)
    if not student:
        return {
            "progress": 0,
            "avg_score": 0,
            "learning_style": "综合",
        }

    progress_obj = await LearningProgress.filter(student_id=student_id).first()
    progress = progress_obj.progress if progress_obj else 0

    analytics = await LearningAnalytics.filter(student_id=student_id).first()
    avg_score = analytics.status_data.get("avg_score", 0) if analytics and analytics.status_data else 0
    learning_style = analytics.status_data.get("learning_style", "综合") if analytics and analytics.status_data else "综合"

    return {
        "progress": progress,
        "avg_score": avg_score,
        "learning_style": learning_style,
    }


def parse_quiz_result(result_str: str, question_type: QuestionType) -> tuple[list[str], list[str]]:
    """解析测验生成结果

    Args:
        result_str: LLM 返回的 JSON 字符串
        question_type: 题目类型

    Returns:
        (题目列表, 答案列表)
    """
    try:
        data = json.loads(result_str)
        questions = data.get("questions", [])
        answers = data.get("answers", [])
        return questions, answers
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_str)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data.get("questions", []), data.get("answers", [])
            except json.JSONDecodeError:
                pass

    return [], []


async def generate_quiz(request: GenerateQuizRequest) -> GenerateQuizResponse:
    """生成测验题目

    Args:
        request: 生成测验请求

    Returns:
        测验响应
    """
    node_state(
        "assess.quiz",
        "entry",
        phase="enter",
        extra={
            "course_id": request.course_id,
            "student_id": request.student_id,
            "num": request.num,
            "type": str(request.type),
        },
        message="生成测验",
    )

    lesson_content = await get_lesson_content(request.course_id, request.courseware_id)
    if not lesson_content:
        node_state("assess.quiz", "no_lesson", phase="error", extra={"course_id": request.course_id})
        return GenerateQuizResponse(
            questions=[],
            answers=[],
        )

    student_profile = await get_student_profile(request.student_id)

    if request.type == QuestionType.FILL_BLANK:
        prompt = FILL_BLANK_QUIZ_PROMPT.format(
            lesson_content=lesson_content,
            progress=student_profile["progress"],
            avg_score=student_profile["avg_score"],
            learning_style=student_profile["learning_style"],
            num=request.num,
        )
    else:
        prompt = QA_QUIZ_PROMPT.format(
            lesson_content=lesson_content,
            progress=student_profile["progress"],
            avg_score=student_profile["avg_score"],
            learning_style=student_profile["learning_style"],
            num=request.num,
        )

    node_state("assess.quiz", "llm_invoke", phase="checkpoint")
    result = await async_generate(prompt=prompt)
    node_state("assess.quiz", "llm_done", phase="checkpoint", extra={"raw_len": len(result)})

    questions, answers = parse_quiz_result(result, request.type)

    if not questions:
        node_state("assess.quiz", "parse_fallback", phase="checkpoint", message="使用默认题目")
        default_questions = [
            f"请简述本节课的主要内容。",
            f"请说明{lesson_content[:50]}...的核心要点。",
        ]
        default_answers = [
            "主要涉及课件讲解的核心概念和关键知识点",
            "需要学生自行总结",
        ]
        resp = GenerateQuizResponse(
            questions=default_questions[:request.num],
            answers=default_answers[:request.num],
        )
        node_state("assess.quiz", "exit", phase="exit", extra={"questions": len(resp.questions)})
        return resp

    resp = GenerateQuizResponse(
        questions=questions[:request.num],
        answers=answers[:request.num],
    )
    node_state("assess.quiz", "exit", phase="exit", extra={"questions": len(resp.questions)})
    return resp


async def quick_generate(
    lesson_content: str,
    num: int = 5,
    question_type: QuestionType = QuestionType.QA,
) -> GenerateQuizResponse:
    """快速生成测验（不查询数据库）

    Args:
        lesson_content: 课件内容
        num: 题目数量
        question_type: 题目类型

    Returns:
        测验响应
    """
    if question_type == QuestionType.FILL_BLANK:
        prompt = FILL_BLANK_QUIZ_PROMPT.format(
            lesson_content=lesson_content[:3000],
            progress=50,
            avg_score=70,
            learning_style="综合",
            num=num,
        )
    else:
        prompt = QA_QUIZ_PROMPT.format(
            lesson_content=lesson_content[:3000],
            progress=50,
            avg_score=70,
            learning_style="综合",
            num=num,
        )

    result = await async_generate(prompt=prompt)
    questions, answers = parse_quiz_result(result, question_type)

    return GenerateQuizResponse(
        questions=questions[:num],
        answers=answers[:num],
    )
