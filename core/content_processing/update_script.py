"""更新脚本模块

接口：/agent/v1/update-script (PUT)

功能：通过数据库获取要添加的课件的解析，根据解析与要更新的课件的课件的信息，生成新的讲解脚本。
使用embedding模型结合原课件内容与新添加课件的内容生成新的课件信息向量，将新的讲解脚本与新的课件向量返回后端。

输入：
1. courseware_id: 要更新的课件 id
2. new_file_id: 新的课件文件 id（用于获取解析路由生成的解析）

可选输入：
1. start_prompt: 新的教师自定义开场白

输出：
1. script: 新的讲解脚本 (str)
2. courseware_vector: 新的课件信息向量 (list[float])

内部逻辑：逻辑同 generate-script，但使用新的内容和提示词。
"""

from typing import Optional
from pydantic import BaseModel, Field

from utils.llm_client import async_generate
from utils.embeddings import embed_lesson_content
from utils.database import TaskProgress, get_redis_cache, Courseware
from utils.node_monitor import node_state
from models.content_processing import (
    UpdateScriptRequest,
    UpdateScriptResponse,
)
from core.content_processing.generate_script import (
    DEFAULT_STYLES,
    SCRIPT_GENERATION_PROMPT,
)


UPDATE_SCRIPT_PROMPT = """你是一位专业的{style}，擅长用生动、易懂的方式讲解课程内容。

原有课件的讲解脚本已经完成，现在需要添加新的课件内容并更新讲解。

原有课件摘要：
{original_summary}

新增课件内容：
{new_content}

请生成更新后的完整讲解脚本，要求：
1. 自然衔接原有内容
2. 逻辑连贯，结构完整
3. 适当加入过渡语连接新旧内容
4. 保持风格一致
5. 整体控制在1500-2000字

安全约束：
1. 禁止生成任何涉及政治敏感、个人隐私或不当内容
2. 保持客观专业的教育态度
3. 输出内容仅限教育相关

请直接输出脚本内容，不需要其他格式。"""


MERGE_PROMPT = """你是一位专业的{style}，擅长整合和讲解课程内容。

请将以下两个课件的内容整合成一个连贯的讲解脚本：

课件1（原有）：
{original_content}

课件2（新增）：
{new_content}

开场白：{start_prompt}

要求：
1. 逻辑清晰，衔接自然
2. 内容完整，覆盖两个课件
3. 适当过渡
4. 长度约1500字

安全约束：
1. 禁止生成任何涉及政治敏感、个人隐私或不当内容
2. 保持客观专业的教育态度
3. 输出内容仅限教育相关

请直接输出脚本内容。"""


async def update_script(
    request: UpdateScriptRequest,
) -> UpdateScriptResponse:
    """更新讲解脚本

    Args:
        request: 更新脚本请��

    Returns:
        更新后的响应
    """
    cache = get_redis_cache()
    progress = TaskProgress(cache)

    task_id = f"update_script_{request.courseware_id}"
    node_state(
        "content.update",
        "entry",
        phase="enter",
        task_id=task_id,
        message="更新脚本开始",
        extra={"courseware_id": request.courseware_id, "new_file_id": request.new_file_id},
    )

    await progress.set_progress(task_id, 10, "正在获取原课件...")

    original_courseware = await Courseware.get_or_none(id=request.courseware_id)
    if not original_courseware:
        node_state("content.update", "fail_original", phase="error", task_id=task_id, extra={"courseware_id": request.courseware_id})
        raise ValueError(f"未找到原课件: {request.courseware_id}")

    await progress.set_progress(task_id, 20, "正在获取新增课件...")
    node_state("content.update", "loaded_original", task_id=task_id, progress=20, extra={"title": original_courseware.title[:60] if original_courseware.title else ""})

    new_courseware = await Courseware.get_or_none(id=request.new_file_id)
    if not new_courseware:
        node_state("content.update", "fail_new", phase="error", task_id=task_id, extra={"new_file_id": request.new_file_id})
        raise ValueError(f"未找到新增课件: {request.new_file_id}")

    await progress.set_progress(task_id, 40, "正在生成更新后的脚本...")
    node_state("content.update", "llm_prompt_ready", task_id=task_id, progress=40, message="构建提示词并调用 LLM")

    style = DEFAULT_STYLES["default"]
    start = request.start_prompt or "各位同学，大家好，我们继续学习。"

    from utils.courseware_reader import get_courseware_text

    original_content = ""
    if original_courseware.parse_result:
        original_content = original_courseware.parse_result.get("summary", "")
    if not original_content:
        original_content = await get_courseware_text(original_courseware, max_chars=2000)

    new_content = ""
    if new_courseware.parse_result:
        new_content = new_courseware.parse_result.get("summary", "")
    if not new_content:
        new_content = await get_courseware_text(new_courseware, max_chars=2000)

    existing_script = getattr(original_courseware, "script", None)

    if existing_script:
        prompt = UPDATE_SCRIPT_PROMPT.format(
            style=style,
            original_summary=original_content,
            new_content=new_content,
        )
    else:
        prompt = MERGE_PROMPT.format(
            style=style,
            original_content=original_content,
            new_content=new_content,
            start_prompt=start,
        )

    script = await async_generate(prompt=prompt)
    node_state("content.update", "llm_done", task_id=task_id, progress=60, extra={"script_chars": len(script) if script else 0})

    await progress.set_progress(task_id, 70, "正在生成课件向量...")

    combined_content = f"{original_content}\n\n{new_content}"
    vector = await embed_lesson_content(
        content=combined_content,
        title=f"{original_courseware.title} + {new_courseware.title}",
    )

    await progress.set_progress(task_id, 100, "脚本更新完成")
    node_state("content.update", "exit", phase="exit", task_id=task_id, progress=100, message="脚本与向量已生成")

    return UpdateScriptResponse(
        script=script,
        courseware_vector=vector,
    )


async def quick_update(
    courseware_id: int,
    new_content: str,
    start_prompt: Optional[str] = None,
) -> UpdateScriptResponse:
    """快速更新脚本（不查询新课件）

    Args:
        courseware_id: 原课件ID
        new_content: 新内容
        start_prompt: 开场白

    Returns:
        更新后的响应
    """
    cache = get_redis_cache()
    progress = TaskProgress(cache)

    task_id = f"quick_update_{courseware_id}"

    original_courseware = await Courseware.get_or_none(id=courseware_id)
    if not original_courseware:
        raise ValueError(f"未找到原课件: {courseware_id}")

    from utils.courseware_reader import get_courseware_text

    original_content = ""
    if original_courseware.parse_result:
        original_content = original_courseware.parse_result.get("summary", "")
    if not original_content:
        original_content = await get_courseware_text(original_courseware, max_chars=2000)

    await progress.set_progress(task_id, 30, "正在生成更新后的脚本...")

    style = DEFAULT_STYLES["default"]
    start = start_prompt or "各位同学，大家好，我们继续学习。"

    existing_script = getattr(original_courseware, "script", None)

    if existing_script:
        prompt = UPDATE_SCRIPT_PROMPT.format(
            style=style,
            original_summary=original_content,
            new_content=new_content,
        )
    else:
        prompt = MERGE_PROMPT.format(
            style=style,
            original_content=original_content,
            new_content=new_content,
            start_prompt=start,
        )

    script = await async_generate(prompt=prompt)

    combined_content = f"{original_content}\n\n{new_content}"
    vector = await embed_lesson_content(
        content=combined_content,
        title=original_courseware.title,
    )

    return UpdateScriptResponse(
        script=script,
        courseware_vector=vector,
    )
