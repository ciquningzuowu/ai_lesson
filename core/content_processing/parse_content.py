"""课件解析模块

接口：/agent/v1/parse-content (POST)
功能：接收后端发送的课件原始内容或文本，生成解析结果，将解析结果返回后端。

输入：
1. 课件文件 (files)
2. 课件文件的类型 (types: ppt/pdf/text)
3. task_id (用于记录进度信息)
4. extract_key_points: 是否提炼重点 (bool)

输出：
1. analysis: 解析结果 (dict)(当extract_key_points为true时，额外包含key_points)
2. defeat_describe: 无法解析时的描述 (str)


优化：
- 使用异步文件处理
- 集成 LangChain 的结构化输出
- 支持多种文档格式
- 任务进度实时追踪
"""

import asyncio
from typing import Optional
from pydantic import BaseModel, Field

from utils.llm_client import async_generate
from utils.helpers import DocumentParser
from utils.database import TaskProgress, get_redis_cache
from utils.node_monitor import node_state
from models.content_processing import (
    ContentType,
    ParseContentRequest,
    ParseContentResponse,
    KeyPointsData,
)


# ============= 提示词定义 =============

PARSING_PROMPT = """你是一个专业课件解析助手。请仔细分析以下课件内容，提取关键信息和结构。

课件内容：
{content}

请以JSON格式返回解析结果，包含以下字段：
- summary: 课程摘要（100字内）
- main_topics: 主要主题列表
- structure: 内容结构分析
- key_concepts: 核心概念列表
- teaching_objectives: 教学目标

如果启用了重点提炼，还需包含：
- key_points: 重点列表（每个重点一句话）

请确保返回的JSON格式正确，可以被解析。"""


EXTRACT_KEY_POINTS_PROMPT = """基于以下课件内容，提炼出关键知识点列表。

课件内容：
{content}

请以JSON格式返回，格式如下：
{{"key_points": ["重点1", "重点2", ...]}}

请提取5-10个最核心的知识点，每个知识点用一句话概括。"""


# ============= 响应模型 =============

class ParsingResult(BaseModel):
    """解析结果模型"""
    summary: str = Field(..., description="课程摘要")
    main_topics: list[str] = Field(..., description="主要主题")
    structure: str = Field(..., description="内容结构")
    key_concepts: list[str] = Field(..., description="核心概念")
    teaching_objectives: list[str] = Field(..., description="教学目标")


# ============= 核心解析逻辑 =============

async def parse_content_text(
    content: str,
    task_id: str,
    extract_key_points: bool = True,
) -> ParseContentResponse:
    """解析课件文本内容

    Args:
        content: 课件文本内容
        task_id: 任务ID
        extract_key_points: 是否提炼重点

    Returns:
        解析响应
    """
    cache = get_redis_cache()
    progress = TaskProgress(cache)

    try:
        node_state(
            "content.parse",
            "parse_text_01",
            phase="enter",
            task_id=task_id,
            progress=10,
            message="开始解析课件文本",
            extra={"content_len": len(content), "extract_key_points": extract_key_points},
        )
        await progress.set_progress(task_id, 10, "开始解析课件...")
        clean_content = DocumentParser.clean_text(content)
        node_state(
            "content.parse",
            "parse_text_02",
            task_id=task_id,
            progress=10,
            message="文本清理完成",
            extra={"clean_len": len(clean_content)},
        )
        if not clean_content or len(clean_content) < 10:
            node_state(
                "content.parse",
                "parse_text_short",
                phase="error",
                task_id=task_id,
                message="内容过短或为空，终止",
            )
            return ParseContentResponse(
                analysis={"error": "内容过短或为空"},
                defeat_describe="课件内容过短，无法进行有效解析",
            )
        await progress.set_progress(task_id, 30, "正在分析内容结构...")
        node_state(
            "content.parse",
            "parse_text_03",
            task_id=task_id,
            progress=30,
            message="调用 LLM 生成基础解析",
        )
        parsing_result_str = await async_generate(
            prompt=PARSING_PROMPT.format(content=clean_content[:8000]),  # 限制内容长度
            system_prompt="你是一个专业的课件解析助手。",
        )
        await progress.set_progress(task_id, 60, "解析基础内容完成...")
        node_state(
            "content.parse",
            "parse_text_04",
            task_id=task_id,
            progress=60,
            message="LLM 基础解析返回，开始 JSON 解析",
            extra={"raw_len": len(parsing_result_str)},
        )

        # 解析 JSON 结果
        import json
        try:
            analysis_data = json.loads(parsing_result_str)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', parsing_result_str)
            if json_match:
                analysis_data = json.loads(json_match.group())
            else:
                node_state(
                    "content.parse",
                    "parse_text_json_fail",
                    phase="error",
                    task_id=task_id,
                    message="无法从 LLM 输出中提取 JSON",
                )
                return ParseContentResponse(
                    analysis={"raw_result": parsing_result_str},
                    defeat_describe="解析结果格式异常",
                )

        # 如果需要提炼重点
        if extract_key_points:
            await progress.set_progress(task_id, 70, "正在提炼重点...")
            node_state(
                "content.parse",
                "parse_text_05",
                task_id=task_id,
                progress=70,
                message="提炼重点知识点",
            )

            key_points_result = await async_generate(
                prompt=EXTRACT_KEY_POINTS_PROMPT.format(content=clean_content[:6000]),
                system_prompt="你是一个专业的课件解析助手，擅长提炼关键知识点。",
            )

            try:
                key_points_data = json.loads(key_points_result)
                analysis_data["key_points"] = key_points_data.get("key_points", [])
            except json.JSONDecodeError:
                import re
                kp_match = re.search(r'\{[\s\S]*\}', key_points_result)
                if kp_match:
                    kp_data = json.loads(kp_match.group())
                    analysis_data["key_points"] = kp_data.get("key_points", [])

        await progress.set_progress(task_id, 100, "解析完成")
        node_state(
            "content.parse",
            "parse_text_99",
            phase="exit",
            task_id=task_id,
            progress=100,
            message="课件文本解析完成",
        )

        return ParseContentResponse(
            analysis=analysis_data,
            defeat_describe=None,
        )

    except Exception as e:
        node_state(
            "content.parse",
            "parse_text_exception",
            phase="error",
            task_id=task_id,
            message=str(e),
        )
        await progress.set_progress(task_id, 0, f"解析失败: {str(e)}")
        return ParseContentResponse(
            analysis={"error": str(e)},
            defeat_describe=f"解析过程出错: {str(e)}",
        )


async def parse_file(
    file_path: str,
    file_type: ContentType,
    task_id: str,
    extract_key_points: bool = True,
) -> ParseContentResponse:
    """解析课件文件

    Args:
        file_path: 文件路径
        file_type: 文件类型
        task_id: 任务ID
        extract_key_points: 是否提炼重点

    Returns:
        解析响应
    """
    cache = get_redis_cache()
    progress = TaskProgress(cache)
    try:
        node_state(
            "content.parse",
            "parse_file_01",
            phase="enter",
            task_id=task_id,
            progress=5,
            message="准备读取并解析文件",
            extra={"file_path": file_path, "file_type": str(file_type)},
        )
        await progress.set_progress(task_id, 5, "正在读取文件...")

        content = await DocumentParser.parse_file(file_path, file_type)
        node_state(
            "content.parse",
            "parse_file_02",
            task_id=task_id,
            progress=5,
            message="DocumentParser 返回",
            extra={"extracted_len": len(content) if content else 0},
        )
        if not content:
            node_state(
                "content.parse",
                "parse_file_empty",
                phase="error",
                task_id=task_id,
                message="无法提取文件内容",
                extra={"file_type": str(file_type)},
            )
            return ParseContentResponse(
                analysis={"error": "无法提取文件内容"},
                defeat_describe=f"不支持的文件格式或无法解析 {file_type} 文件",
            )

        node_state(
            "content.parse",
            "parse_file_03",
            task_id=task_id,
            message="转入 parse_content_text",
        )
        return await parse_content_text(content, task_id, extract_key_points)

    except Exception as e:
        node_state(
            "content.parse",
            "parse_file_exception",
            phase="error",
            task_id=task_id,
            message=str(e),
            extra={"file_path": file_path},
        )
        await progress.set_progress(task_id, 0, f"解析失败: {str(e)}")
        return ParseContentResponse(
            analysis={"error": str(e)},
            defeat_describe=f"文件解析失败: {str(e)}",
        )


# ============= 多文件并发处理 =============

async def parse_multiple_files(
    file_infos: list[dict],
    task_id: str,
    extract_key_points: bool = True,
) -> dict:
    """并发解析多个课件文件

    Args:
        file_infos: 文件信息列表，每个元素包含 path, type
        task_id: 任务ID
        extract_key_points: 是否提炼重点

    Returns:
        解析结果字典
    """
    cache = get_redis_cache()
    progress = TaskProgress(cache)

    await progress.set_progress(task_id, 0, "开始批量解析...")
    node_state(
        "content.parse",
        "parse_batch_01",
        task_id=task_id,
        progress=0,
        message="开始批量解析",
        extra={"file_count": len(file_infos)},
    )

    # 创建并发任务
    tasks = []
    for info in file_infos:
        task = parse_file(
            file_path=info["path"],
            file_type=ContentType(info["type"]),
            task_id=f"{task_id}_{info['path']}",
            extract_key_points=extract_key_points,
        )
        tasks.append(task)

    # 并发执行
    results = await asyncio.gather(*tasks, return_exceptions=True)

    await progress.set_progress(task_id, 100, "批量解析完成")
    ok = sum(1 for r in results if not isinstance(r, Exception))
    node_state(
        "content.parse",
        "parse_batch_99",
        phase="exit",
        task_id=task_id,
        progress=100,
        message="批量解析完成",
        extra={"success": ok, "total": len(results)},
    )

    # 整理结果
    parsed_results = {}
    for i, info in enumerate(file_infos):
        file_path = info["path"]
        if isinstance(results[i], Exception):
            parsed_results[file_path] = {
                "status": "failed",
                "error": str(results[i]),
            }
        else:
            parsed_results[file_path] = {
                "status": "success",
                "result": results[i].model_dump(),
            }

    return parsed_results


# ============= 快捷函数 =============

async def quick_parse(content: str, extract_key_points: bool = True) -> dict:
    """快速解析（不追踪任务进度）

    Args:
        content: 课件内容
        extract_key_points: 是否提炼重点

    Returns:
        解析结果字典
    """
    result = await parse_content_text(
        content=content,
        task_id="quick_parse",
        extract_key_points=extract_key_points,
    )
    return result.model_dump()
