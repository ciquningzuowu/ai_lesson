"""内容处理相关的数据模型

定义内容处理模块的请求和响应数据结构。
与新课程体系对齐：课程(Course) + 课件(Courseware)
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ContentType(str, Enum):
    """课件文件类型"""
    PPT = "ppt"
    PDF = "pdf"
    TEXT = "text"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ParseContentRequest(BaseModel):
    """课件解析请求"""
    task_id: str = Field(..., max_length=128, description="任务ID，用于记录进度")
    file_type: ContentType = Field(..., description="文件类型")
    extract_key_points: bool = Field(default=True, description="是否提炼重点")


class ParseContentResponse(BaseModel):
    """课件解析响应"""
    analysis: dict = Field(..., description="解析结果")
    defeat_describe: Optional[str] = Field(default=None, description="无法解析时的描述")


class KeyPointsData(BaseModel):
    """重点数据"""
    key_points: list[str] = Field(..., description="提炼的重点列表")


class SectionScript(BaseModel):
    """章节脚本"""
    section_id: int = Field(..., description="章节ID")
    script: str = Field(..., description="讲解脚本内容")


class GenerateScriptRequest(BaseModel):
    """生成讲解脚本请求"""
    courseware_ids: list[int] = Field(..., max_length=50, description="课件ID列表（替代原lesson_ids）")
    task_id: str = Field(..., max_length=128, description="任务ID")
    course_id: Optional[int] = Field(default=None, description="课程ID")
    start_prompt: Optional[str] = Field(default=None, max_length=500, description="自定义开场白")
    style_prompt: Optional[str] = Field(default=None, max_length=200, description="讲解风格")


class GenerateScriptResponse(BaseModel):
    """生成讲解脚本响应"""
    explain: list[SectionScript] = Field(..., description="讲解脚本列表")
    courseware_vector: list[float] = Field(..., description="课件信息向量")


class UpdateScriptRequest(BaseModel):
    """更新脚本请求"""
    courseware_id: int = Field(..., description="要更新的课件ID（替代原lesson_id）")
    new_file_id: int = Field(..., description="新的课件文件ID")
    start_prompt: Optional[str] = Field(default=None, description="新的自定义开场白")


class UpdateScriptResponse(BaseModel):
    """更新脚本响应"""
    script: str = Field(..., description="新的讲解脚本")
    courseware_vector: list[float] = Field(..., description="新的课件信息向量")


class TaskProgress(BaseModel):
    """任务进度"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: float = Field(ge=0.0, le=100.0, default=0.0, description="进度百分比")
    message: Optional[str] = Field(default=None, description="状态消息")
    updated_at: datetime = Field(default_factory=datetime.now)


class CoursewareContent(BaseModel):
    """课件内容"""
    courseware_id: int = Field(..., description="课件ID")
    course_id: int = Field(..., description="课程ID")
    title: str = Field(..., description="课件标题")
    content: str = Field(..., description="课件原始内容")
    parse_result: Optional[dict] = Field(default=None, description="课件解析结果")
    file_type: Optional[str] = Field(default=None, description="文件类型")
    vector: Optional[list[float]] = Field(default=None, description="课件向量")
    create_time: datetime = Field(default_factory=datetime.now)


class ParseTextContentRequest(BaseModel):
    """解析文本内容请求

    POST /agent/v1/parse-content/text 接口使用
    """
    content: str = Field(..., max_length=500000, description="文本内容（最大500KB）")
    task_id: str = Field(..., max_length=128, description="任务ID")
    extract_key_points: bool = Field(default=True, description="是否提炼重点")


class AnalysisImage(BaseModel):
    """PDF图片分析结果"""
    image_index: int = Field(..., description="图片索引")
    page_num: int = Field(..., description="所在页码")
    description: Optional[str] = Field(default=None, description="图片描述")


class ParseTextContentResponse(BaseModel):
    """解析文本内容响应"""
    analysis: dict = Field(..., description="解析结果")
    defeat_describe: Optional[str] = Field(default=None, description="无法解析时的描述")
