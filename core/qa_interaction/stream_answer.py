"""流式回答模块

接口：/agent/v1/stream-answer (POST)

功能：接收学生问题，结合课程上下文与学生学习状况生成回答。

输入：
1. student_id: 学生 id
2. course_id: 课程 id
3. courseware_id: 课件 id (可选)
4. question: 学生的问题

输出：
1. answer: 完整的 answer 文本(str)

内部逻辑：
使用学生id获取学生学习状况、课程进度和对话历史，使用course_id获取课程解析，
基于该学生的学习状况、课程进度、对话历史和该课程的课件解析生成答案。
必要时可通过course_id获取课程信息向量，使用RAG技术进行信息查询 。
"""

from typing import Optional, AsyncIterator
from pydantic import BaseModel, Field

from utils.llm_client import async_generate, async_stream_generate
from utils.database import (
    Student,
    Course,
    Courseware,
    CoursewareVector,
    ChatHistory,
    LearningProgress,
    LearningAnalytics,
)
from utils.rag import get_rag_service, RAGService
from utils.node_monitor import node_state


ANSWER_PROMPT = """你是一位专业的AI助教，请根据课件内容和学生学习状况回答学生的问题。

=== 课件解析 ===
{lesson_analysis}

=== 学生学习状况 ===
学习进度：{progress}%
历史平均分：{avg_score}
学习风格：{learning_style}

=== 对话历史 ===
{conversation_history}

=== 学生问题 ===
{question}

请用专业、生动的方式回答学生的问题，要求：
1. 基于课件内容给出准确答案
2. 适当引用课件中的关键概念
3. 语言简洁易懂
4. 如有必要，可以举例说明
5. 如果问题超出课件范围，请诚实说明

安全约束：
1. 回答内容控制在100-300字以内
2. 禁止生成任何涉及政治敏感、个人隐私或不当内容
3. 保持客观专业的教育态度
4. 不输出任何额外解释或后续内容
5. 回答结束后，用 <END> 标记结束

请直接输出回答内容。"""


RAG_ANSWER_PROMPT = """你是一位专业的AI助教，请根据检索到的相关内容回答学生的问题。

=== 检索到的相关内容 ===
{retrieved_content}

=== 学生学习状况 ===
学习进度：{progress}%
历史平均分：{avg_score}

=== 学生问题 ===
{question}

请基于检索到的内容回答学生的问题，要求：
1. 准确、清晰地回答
2. 适当引用检索内容中的要点
3. 如有需要可补充额外知识
4. 如果检索内容不足以回答，请诚实说明

安全约束：
1. 回答内容控制在100-300字以内
2. 禁止生成任何涉及政治敏感、个人隐私或不当内容
3. 保持客观专业的教育态度
4. 不输出任何额外解释或后续内容
5. 回答结束后，用 <END> 标记结束

请直接输出回答内容。"""


CONVERSATION_CONTEXT_PROMPT = """基于以下对话历史，保持回答的一致性和连贯性。

对话历史：
{history}

请在回答中保持上下文连贯，如：
- 延续之前的话题
- 回应之前提到的概念
- 记住学生之前的问题或困惑

当前问题：{question}

安全约束：
1. 禁止生成任何涉及政治敏感、个人隐私或不当内容
2. 保持客观专业的教育态度
3. 回答内容控制在100字以内"""


class StreamAnswerResponse(BaseModel):
    """流式回答响应"""
    answer: str = Field(..., description="完整的回答文本")


async def get_conversation_history(
    student_id: int,
    course_id: Optional[int] = None,
    limit: int = 10,
) -> str:
    """获取对话历史

    Args:
        student_id: 学生ID
        course_id: 课程ID（可选）
        limit: 返回数量

    Returns:
        格式化的对话历史字符串
    """
    query = ChatHistory.filter(student_id=student_id)
    if course_id:
        query = query.filter(course_id=course_id)

    conversations = await query.order_by("-timestamp").limit(limit)

    history_parts = []
    for conv in conversations:
        history_parts.append(f"学生: {conv.question}")
        if conv.answer:
            history_parts.append(f"助教: {conv.answer}")

    return "\n".join(history_parts) if history_parts else "（首次对话）"


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


async def get_courseware_content(course_id: int, courseware_id: Optional[int] = None) -> str:
    """获取课件内容

    Args:
        course_id: 课程ID
        courseware_id: 课件ID（可选）

    Returns:
        课件内容字符串
    """
    from utils.courseware_reader import get_courseware_summary

    if courseware_id:
        courseware = await Courseware.get_or_none(id=courseware_id)
        if courseware:
            # 优先使用已解析的结果
            if courseware.parse_result:
                content = courseware.parse_result.get("summary", "")
                if content:
                    return content
                key_points = courseware.parse_result.get("key_points", [])
                if key_points:
                    return "关键知识点：\n" + "\n".join(f"- {kp}" for kp in key_points)
            # 使用 courseware_reader 读取二进制文件
            return await get_courseware_summary(courseware)

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

        # 使用 courseware_reader 读取第一个课件
        return await get_courseware_summary(coursewares[0])

    return ""


async def should_use_rag(question: str) -> bool:
    """判断是否需要使用 RAG

    Args:
        question: 学生问题

    Returns:
        是否使用 RAG
    """
    rag_keywords = ["详细", "具体", "例子", "如何", "为什么", "什么原理", "说明"]
    return len(question) > 20 or any(kw in question for kw in rag_keywords)


async def answer_question(
    student_id: int,
    course_id: int,
    question: str,
    courseware_id: Optional[int] = None,
) -> StreamAnswerResponse:
    """回答学生问题

    Args:
        student_id: 学生ID
        course_id: 课程ID
        question: 学生问题
        courseware_id: 课件ID（可选）

    Returns:
        回答响应
    """
    node_state(
        "qa.answer",
        "entry",
        phase="enter",
        extra={"student_id": student_id, "course_id": course_id, "q_len": len(question)},
        message="问答：聚合上下文",
    )
    student_profile = await get_student_profile(student_id)
    courseware_content = await get_courseware_content(course_id, courseware_id)
    conversation_history = await get_conversation_history(student_id, course_id)
    node_state(
        "qa.answer",
        "context_ready",
        phase="checkpoint",
        extra={
            "content_chars": len(courseware_content),
            "history_chars": len(conversation_history),
        },
    )

    use_rag = await should_use_rag(question)
    node_state("qa.answer", "rag_decision", phase="checkpoint", extra={"use_rag": use_rag})

    if use_rag and courseware_content:
        rag_service = get_rag_service()

        if not rag_service.vector_store.chunks:
            node_state("qa.answer", "rag_index", message="建立临时索引")
            await rag_service.aindex_content(courseware_content, source=f"course_{course_id}")

        retrieved_chunks = await rag_service.retrieve(question)
        node_state("qa.answer", "rag_retrieve", extra={"chunks": len(retrieved_chunks)})
        if retrieved_chunks:
            retrieved_content = "\n".join(chunk.content for chunk in retrieved_chunks)

            prompt = RAG_ANSWER_PROMPT.format(
                retrieved_content=retrieved_content,
                progress=student_profile["progress"],
                avg_score=student_profile["avg_score"],
                question=question,
            )
        else:
            prompt = ANSWER_PROMPT.format(
                lesson_analysis=courseware_content or "无课件解析",
                progress=student_profile["progress"],
                avg_score=student_profile["avg_score"],
                learning_style=student_profile["learning_style"],
                conversation_history=conversation_history,
                question=question,
            )
    else:
        prompt = ANSWER_PROMPT.format(
            lesson_analysis=courseware_content or "无课件解析",
            progress=student_profile["progress"],
            avg_score=student_profile["avg_score"],
            learning_style=student_profile["learning_style"],
            conversation_history=conversation_history,
            question=question,
        )

    node_state("qa.answer", "llm_invoke", message="生成回答")
    answer = await async_generate(prompt=prompt)

    node_state("qa.answer", "exit", phase="exit", extra={"answer_chars": len(answer) if answer else 0})
    return StreamAnswerResponse(answer=answer)


async def stream_answer(
    student_id: int,
    course_id: int,
    question: str,
    courseware_id: Optional[int] = None,
) -> AsyncIterator[str]:
    """流式回答学生问题

    Args:
        student_id: 学生ID
        course_id: 课程ID
        question: 学生问题
        courseware_id: 课件ID（可选）

    Yields:
        回答文本片段
    """
    node_state(
        "qa.stream",
        "entry",
        phase="enter",
        extra={"student_id": student_id, "course_id": course_id},
    )
    student_profile = await get_student_profile(student_id)
    courseware_content = await get_courseware_content(course_id, courseware_id)
    conversation_history = await get_conversation_history(student_id, course_id)

    prompt = ANSWER_PROMPT.format(
        lesson_analysis=courseware_content or "无课件解析",
        progress=student_profile["progress"],
        avg_score=student_profile["avg_score"],
        learning_style=student_profile["learning_style"],
        conversation_history=conversation_history,
        question=question,
    )

    full_answer = ""
    node_state("qa.stream", "llm_stream_start", phase="checkpoint")
    async for chunk in async_stream_generate(prompt=prompt):
        full_answer += chunk
        yield chunk

    node_state("qa.stream", "exit", phase="exit", extra={"answer_chars": len(full_answer)})


async def quick_answer(
    question: str,
    context: Optional[str] = None,
) -> StreamAnswerResponse:
    """快速回答（不查询数据库）

    Args:
        question: 学生问题
        context: 上下文内容

    Returns:
        回答响应
    """
    if context:
        prompt = f"""基于以下内容回答学生的问题：

{context}

学生问题：{question}

请给出准确、简洁的回答。"""
    else:
        prompt = question

    answer = await async_generate(prompt=prompt)

    return StreamAnswerResponse(answer=answer)
