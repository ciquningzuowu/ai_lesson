"""内容处理 API 路由

提供课件解析、脚本生成等接口
"""

from contextlib import asynccontextmanager
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Optional

from models.content_processing import (
    ParseContentRequest,
    ParseContentResponse,
    GenerateScriptRequest,
    GenerateScriptResponse,
    UpdateScriptRequest,
    UpdateScriptResponse,
    ContentType,
)
from core.content_processing.parse_content import parse_file, parse_content_text
from core.content_processing.generate_script import generate_script
from core.content_processing.update_script import update_script
from utils.helpers import ResponseFormatter
from utils.node_monitor import node_state
from utils.database import init_db, close_db, ensure_db, get_redis_cache, Courseware

router = APIRouter(prefix="/agent/v1", tags=["内容处理"])


@router.post("/parse-content", response_model=ParseContentResponse)
async def parse_content(
    file: UploadFile = File(...),
    file_type: ContentType = ContentType.TEXT,
    task_id: str = "default",
    extract_key_points: bool = True,
    course_id: int = None,
):
    """解析课件内容

    接收后端发送的课件原始内容或文本，生成解析结果。

    Args:
        file: 课件文件（最大10MB）
        file_type: 文件类型 (ppt/pdf/text)
        task_id: 任务ID
        extract_key_points: 是否提炼重点
        course_id: 课程ID

    Returns:
        解析结果
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        # 限制文件大小（10MB）
        max_size = 10 * 1024 * 1024
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=413, detail="文件大小超出限制，最大支持10MB")

        node_state(
            "api.content",
            "parse_content",
            phase="enter",
            task_id=task_id,
            extra={"file_type": str(file_type), "filename": file.filename},
        )
        node_state("api.content", "parse_content_upload", phase="checkpoint", extra={"bytes": len(content)})

        if file_type == ContentType.TEXT:
            text_content = content.decode("utf-8", errors="ignore")
            result = await parse_content_text(
                content=text_content,
                task_id=task_id,
                extract_key_points=extract_key_points,
            )
        else:
            import tempfile
            import os
            import logging

            logger = logging.getLogger(__name__)

            # 将 file_type 映射为正确的文件扩展名
            suffix_map = {
                "ppt": ".pptx",   # PPT 类型使用 pptx 扩展名
                "pdf": ".pdf",
                "text": ".txt",
            }
            file_suffix = suffix_map.get(file_type.value, f".{file_type.value}")

            # 创建临时文件
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=file_suffix)
            try:
                # 写入内容
                os.write(tmp_fd, content)
                os.close(tmp_fd)  # 关闭文件句柄

                # 调试日志（隐藏敏感路径信息）
                logger.info(f"[DEBUG] 临时文件已创建, 大小: {len(content)} bytes")

                result = await parse_file(
                    file_path=tmp_path,
                    file_type=file_type,
                    task_id=task_id,
                    extract_key_points=extract_key_points,
                )
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass  # 忽略删除失败

        node_state("api.content", "parse_content", phase="exit", task_id=task_id, message="解析接口返回")
        return result

    except Exception as e:
        node_state("api.content", "parse_content", phase="error", task_id=task_id, message=str(e))
        raise HTTPException(status_code=500, detail="处理文件时发生错误")



@router.post("/parse-content/text")
async def parse_text_content(request: ParseContentRequest):
    """解析文本内容（直接传文本）

    Args:
        request: 解析请求

    Returns:
        解析结果
    """
    await ensure_db()  # 确保数据库已初始化

    from models.content_processing import ParseContentResponse
    from core.content_processing.parse_content import parse_content_text as _parse_content_text

    try:
        node_state(
            "api.content",
            "parse_text_content",
            phase="enter",
            task_id=request.task_id,
            extra={"content_len": len(request.content)},
        )
        result = await _parse_content_text(
            content=request.content,
            task_id=request.task_id,
            extract_key_points=request.extract_key_points,
        )
        node_state("api.content", "parse_text_content", phase="exit", task_id=request.task_id)
        return ResponseFormatter.success_response(result.model_dump())
    except Exception as e:
        node_state("api.content", "parse_text_content", phase="error", message=str(e))
        return ResponseFormatter.error_response(str(e), code="PARSE_ERROR")


@router.post("/generate-script", response_model=GenerateScriptResponse)
async def create_script(request: GenerateScriptRequest):
    """生成讲解脚本

    根据课件内容和指定的风格，生成生动、专业的讲解脚本。

    Args:
        request: 生成脚本请求

    Returns:
        讲解脚本和课件向量
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        node_state("api.content", "generate_script", phase="enter", task_id=request.task_id, extra={"courseware_ids": request.courseware_ids})
        result = await generate_script(request)
        node_state("api.content", "generate_script", phase="exit", task_id=request.task_id)
        return result
    except ValueError as e:
        node_state("api.content", "generate_script", phase="error", task_id=request.task_id, message=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        node_state("api.content", "generate_script", phase="error", task_id=request.task_id, message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-script/stream")
async def create_script_stream(request: GenerateScriptRequest):
    """流式生成讲解脚本

    Args:
        request: 生成脚本请求

    Yields:
        脚本片段
    """
    await ensure_db()  # 确保数据库已初始化

    from fastapi.responses import StreamingResponse

    async def stream_generator():
        from core.content_processing.generate_script import generate_script_stream

        async for chunk in generate_script_stream(request):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )


@router.put("/update-script", response_model=UpdateScriptResponse)
async def modify_script(request: UpdateScriptRequest):
    """更新讲解脚本

    通过新添加的课件内容更新讲解脚本。

    Args:
        request: 更新脚本请求

    Returns:
        更新后的脚本和向量
    """
    await ensure_db()  # 确保数据库已初始化

    try:
        node_state(
            "api.content",
            "update_script",
            phase="enter",
            extra={"courseware_id": request.courseware_id, "new_file_id": request.new_file_id},
        )
        result = await update_script(request)
        node_state("api.content", "update_script", phase="exit")
        return result
    except ValueError as e:
        node_state("api.content", "update_script", phase="error", message=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        node_state("api.content", "update_script", phase="error", message=str(e))
        raise HTTPException(status_code=500, detail=str(e))
