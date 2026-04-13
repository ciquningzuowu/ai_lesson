"""生成讲解脚本模块

接口：/agent/v1/generate-script (POST)

功能：根据课件内容和指定的风格，生成生动、专业的讲解脚本，
使用embedding模型生成课件的信息向量，
最终返回讲解脚本和课件向量给后端。

输入：
1. courseware_ids: 课件ID列表 (list[int])
2. task_id: 任务 ID (用于记录进度信息)
3. course_id: 课程ID (可选)

可选输入：
1. start_prompt: 教师自定义开场白 (str)
2. style_prompt: 讲解风格 (str，默认课件所属领域的老师)

输出：
1. explain: 完整的讲解脚本 (list[dict])，每项包含 section_id 和 script
2. courseware_vector: 课件信息向量 (list[float])

内部逻辑：
调用大语言模型（LLM），依据 courseware_id 从数据库获取课件解析，
结合 style_prompt 生成符合教学逻辑的讲授脚本，并注意与 start_prompt 进行衔接。
使用embedding模型生成课件的信息向量，将讲解脚本与课件向量返回后端。
"""

import asyncio
from typing import Optional
from pydantic import BaseModel, Field

from utils.llm_client import async_generate, async_stream_generate
from utils.embeddings import embed_lesson_content
from utils.database import TaskProgress, get_redis_cache, Courseware
from utils.node_monitor import node_state
from models.content_processing import (
    GenerateScriptRequest,
    GenerateScriptResponse,
    SectionScript,
)


SCRIPT_GENERATION_PROMPT = """你是一位专业的{style}，擅长用生动、易懂的方式讲解课程内容。

开场白：{start_prompt}

课件内容：
{lesson_content}

请生成一段专业的讲解脚本，要求：
1. 自然衔接开场白
2. 内容结构清晰，分点讲解
3. 语言生动，便于学生理解
4. 适当加入比喻和实例
5. 控制长度在合适范围内（约500-1000字）

请直接输出脚本内容，不需要其他格式。"""


MULTI_LESSON_SCRIPT_PROMPT = """你是一位专业的{style}，擅长用生动、易懂的方式讲解课程内容。

开场白：{start_prompt}

以下是多个课件的内容：

{lessons_content}

请生成连贯的讲解脚本，要求：
1. 自然衔接开场白
2. 按课件顺序组织内容，逻辑连贯
3. 内容结构清晰，适当分点讲解
4. 在课件之间添加过渡语
5. 语言生动，便于学生理解
6. 整体控制在1500-2000字

请直接输出脚本内容，不需要其他格式。"""


DEFAULT_STYLES = {
    "default": "经验丰富的教师",
    "math": "数学教学专家",
    "science": "自然科学教师",
    "history": "历史教学专家",
    "language": "语文教师",
    "programming": "编程教学专家",
}


async def generate_single_script(
    courseware: Courseware,
    style_prompt: Optional[str] = None,
    start_prompt: Optional[str] = None,
    task_id: Optional[str] = None,
) -> tuple[str, list[float]]:
    """为单个课件生成讲解脚本

    Args:
        courseware: 课件对象
        style_prompt: 讲解风格
        start_prompt: 自定义开场白
        task_id: 任务ID

    Returns:
        (讲解脚本, 课件向量)
    """
    cache = get_redis_cache()
    progress = TaskProgress(cache) if task_id else None

    if progress:
        await progress.set_progress(task_id, 10, f"正在生成《{courseware.title}》的讲解脚本...")
    node_state(
        "content.script",
        "single_01",
        task_id=task_id,
        progress=10 if task_id else None,
        message="单课件脚本：准备内容与风格",
        extra={"courseware_id": courseware.id, "title": courseware.title[:80] if courseware.title else ""},
    )

    style = style_prompt or DEFAULT_STYLES.get("default", DEFAULT_STYLES["default"])
    start = start_prompt or "各位同学，大家好，今天我们来学习这门课程。"

    from utils.courseware_reader import get_courseware_text

    lesson_content = courseware.parse_result.get("summary", "") if courseware.parse_result else ""
    if not lesson_content and courseware.content:
        lesson_content = await get_courseware_text(courseware, max_chars=2000)

    prompt = SCRIPT_GENERATION_PROMPT.format(
        style=style,
        start_prompt=start,
        lesson_content=lesson_content,
    )

    if progress:
        await progress.set_progress(task_id, 40, "正在调用语言模型生成脚本...")
    node_state("content.script", "single_02", task_id=task_id, progress=40 if task_id else None, message="调用 LLM 生成脚本")

    script = await async_generate(prompt=prompt)

    if progress:
        await progress.set_progress(task_id, 70, "正在生成课件向量...")
    node_state("content.script", "single_03", task_id=task_id, progress=70 if task_id else None, message="生成嵌入向量")

    vector = await embed_lesson_content(
        content=lesson_content,
        title=courseware.title,
    )

    if progress:
        await progress.set_progress(task_id, 100, "脚本生成完成")
    node_state("content.script", "single_99", phase="exit", task_id=task_id, progress=100 if task_id else None, message="单课件脚本完成")

    return script, vector


async def generate_multi_lesson_script(
    courseware_ids: list[int],
    task_id: str,
    style_prompt: Optional[str] = None,
    start_prompt: Optional[str] = None,
) -> tuple[list[SectionScript], list[float]]:
    """为多个课件生成讲解脚本

    Args:
        courseware_ids: 课件ID列表
        task_id: 任务ID
        style_prompt: 讲解风格
        start_prompt: 自定义开场白

    Returns:
        (讲解脚本列表, 课件向量)
    """
    cache = get_redis_cache()
    progress = TaskProgress(cache)

    await progress.set_progress(task_id, 5, "正在获取课件内容...")
    node_state(
        "content.script",
        "multi_01",
        task_id=task_id,
        progress=5,
        message="多课件：拉取 Courseware",
        extra={"courseware_ids": courseware_ids},
    )

    coursewares = []
    for cid in courseware_ids:
        courseware = await Courseware.get_or_none(id=cid)
        if courseware:
            coursewares.append(courseware)

    if not coursewares:
        node_state("content.script", "multi_fail", phase="error", task_id=task_id, message="未找到课件", extra={"courseware_ids": courseware_ids})
        raise ValueError(f"未找到指定的课件，IDs: {courseware_ids}")

    await progress.set_progress(task_id, 20, f"已加载 {len(coursewares)} 个课件")
    node_state("content.script", "multi_02", task_id=task_id, progress=20, message="课件已加载", extra={"count": len(coursewares)})

    style = style_prompt or DEFAULT_STYLES.get("default", DEFAULT_STYLES["default"])
    start = start_prompt or "各位同学，大家好，今天我们来学习这门课程。"

    from utils.courseware_reader import get_courseware_text

    lessons_content = []
    for i, courseware in enumerate(coursewares, 1):
        content = courseware.parse_result.get("summary", "") if courseware.parse_result else ""
        if not content and courseware.content:
            content = await get_courseware_text(courseware, max_chars=1000)
        lessons_content.append(f"=== 课件 {i}: {courseware.title} ===\n{content}")

    combined_content = "\n\n".join(lessons_content)

    await progress.set_progress(task_id, 40, "正在调用语言模型生成脚本...")
    node_state("content.script", "multi_03", task_id=task_id, progress=40, message="LLM 生成多课件脚本")

    if len(coursewares) == 1:
        prompt = SCRIPT_GENERATION_PROMPT.format(
            style=style,
            start_prompt=start,
            lesson_content=combined_content,
        )
    else:
        prompt = MULTI_LESSON_SCRIPT_PROMPT.format(
            style=style,
            start_prompt=start,
            lessons_content=combined_content,
        )

    script = await async_generate(prompt=prompt)

    await progress.set_progress(task_id, 70, "正在生成课件向量...")
    node_state("content.script", "multi_04", task_id=task_id, progress=70, message="合并内容嵌入")

    vector = await embed_lesson_content(
        content=combined_content,
        title=" | ".join([c.title for c in coursewares]),
    )

    await progress.set_progress(task_id, 100, "脚本生成完成")
    node_state("content.script", "multi_99", phase="exit", task_id=task_id, progress=100, message="多课件脚本完成")

    sections = [
        SectionScript(section_id=0, script=script),
    ]

    return sections, vector


async def generate_script(
    request: GenerateScriptRequest,
) -> GenerateScriptResponse:
    """生成讲解脚本主函数

    Args:
        request: 生成脚本请求

    Returns:
        脚本响应
    """
    task_id = request.task_id
    node_state(
        "content.script",
        "generate_script_entry",
        phase="enter",
        task_id=task_id,
        message="generate_script 入口",
        extra={"courseware_ids": request.courseware_ids},
    )

    if len(request.courseware_ids) == 1:
        courseware_id = request.courseware_ids[0]
        courseware = await Courseware.get_or_none(id=courseware_id)

        if not courseware:
            node_state("content.script", "generate_script_fail", phase="error", task_id=task_id, extra={"courseware_id": courseware_id})
            raise ValueError(f"未找到课件: {courseware_id}")

        script, vector = await generate_single_script(
            courseware=courseware,
            style_prompt=request.style_prompt,
            start_prompt=request.start_prompt,
            task_id=task_id,
        )

        courseware.script = script
        await courseware.save()
        node_state("content.script", "script_saved", phase="checkpoint", extra={"courseware_id": courseware_id})

        node_state("content.script", "generate_script_exit", phase="exit", task_id=task_id, message="单课件响应已构造")
        return GenerateScriptResponse(
            explain=[SectionScript(section_id=0, script=script)],
            courseware_vector=vector,
        )

    sections, vector = await generate_multi_lesson_script(
        courseware_ids=request.courseware_ids,
        task_id=task_id,
        style_prompt=request.style_prompt,
        start_prompt=request.start_prompt,
    )

    for i, cid in enumerate(request.courseware_ids):
        courseware = await Courseware.get_or_none(id=cid)
        if courseware and i < len(sections):
            courseware.script = sections[i].script
            await courseware.save()

    node_state("content.script", "generate_script_exit", phase="exit", task_id=task_id, message="多课件响应已构造")
    return GenerateScriptResponse(
        explain=sections,
        courseware_vector=vector,
    )


async def generate_script_stream(
    request: GenerateScriptRequest,
):
    """流式生成讲解脚本

    Args:
        request: 生成脚本请求

    Yields:
        脚本片段
    """
    task_id = request.task_id
    cache = get_redis_cache()
    progress = TaskProgress(cache)

    await progress.set_progress(task_id, 10, "开始生成脚本...")
    node_state("content.script", "stream_01", phase="enter", task_id=task_id, progress=10, message="流式生成脚本开始")

    coursewares = []
    for cid in request.courseware_ids:
        courseware = await Courseware.get_or_none(id=cid)
        if courseware:
            coursewares.append(courseware)

    if not coursewares:
        node_state("content.script", "stream_fail", phase="error", task_id=task_id, message="流式：无课件")
        raise ValueError(f"未找到指定的课件")

    style = request.style_prompt or DEFAULT_STYLES["default"]
    start = request.start_prompt or "各位同学，大家好。"

    from utils.courseware_reader import get_courseware_text

    lessons_content = []
    for i, courseware in enumerate(coursewares, 1):
        content = courseware.parse_result.get("summary", "") if courseware.parse_result else ""
        if not content:
            content = await get_courseware_text(courseware, max_chars=1000)
        lessons_content.append(f"=== 课件 {i}: {courseware.title} ===\n{content}")

    combined_content = "\n\n".join(lessons_content)

    await progress.set_progress(task_id, 30, "正在生成脚本...")
    node_state("content.script", "stream_02", task_id=task_id, progress=30, message="流式 LLM 输出")

    prompt = MULTI_LESSON_SCRIPT_PROMPT.format(
        style=style,
        start_prompt=start,
        lessons_content=combined_content,
    )

    async for chunk in async_stream_generate(prompt=prompt):
        yield chunk

    await progress.set_progress(task_id, 100, "生成完成")
    node_state("content.script", "stream_99", phase="exit", task_id=task_id, progress=100, message="流式生成结束")
