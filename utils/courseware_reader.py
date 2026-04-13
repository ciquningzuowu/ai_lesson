"""课件内容读取模块

从数据库读取二进制课件文件并解析为文本内容
"""

import tempfile
import os
from typing import Optional


async def get_courseware_text(courseware, max_chars: int = 3000) -> str:
    """从课件获取文本内容
    
    优先使用已解析的结果，如果不存在则解析二进制文件
    
    Args:
        courseware: Courseware 模型实例
        max_chars: 最大返回字符数
    
    Returns:
        课件文本内容
    """
    # 优先使用已解析的结果
    if courseware.parse_result:
        summary = courseware.parse_result.get("summary", "")
        if summary:
            return summary[:max_chars]
    
    # 如果有原始文件二进制，需要解析
    if courseware.content:
        try:
            from models.content_processing import ContentType
            
            suffix = ".pptx" if courseware.file_type == "ppt" else ".pdf"
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            try:
                os.write(tmp_fd, courseware.content)
                os.close(tmp_fd)
                
                from core.content_processing.parse_content import parse_file
                
                result = await parse_file(
                    file_path=tmp_path,
                    file_type=ContentType(courseware.file_type or "ppt"),
                    task_id=f"read_{courseware.id}",
                    extract_key_points=True,
                )
                return result.analysis.get("summary", "")[:max_chars]
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        except Exception:
            pass
    
    return ""


async def get_courseware_summary(courseware, max_chars: int = 2000) -> str:
    """获取课件摘要
    
    Args:
        courseware: Courseware 模型实例
        max_chars: 最大返回字符数（默认2000）
    
    Returns:
        课件摘要文本
    """
    return await get_courseware_text(courseware, max_chars=max_chars)


__all__ = [
    "get_courseware_text",
    "get_courseware_summary",
]
