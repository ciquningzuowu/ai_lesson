"""问答交互相关的数据模型

定义问答交互模块的请求和响应数据结构。
与新课程体系对齐：课程(Course) + 课件(Courseware)
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class StreamAnswerRequest(BaseModel):
    """流式回答请求"""
    student_id: int = Field(..., description="学生ID")
    course_id: int = Field(..., description="课程ID（替代原lesson_id）")
    courseware_id: Optional[int] = Field(default=None, description="课件ID（可选）")
    question: str = Field(..., description="学生的问题")


class StreamAnswerResponse(BaseModel):
    """流式回答响应"""
    answer: str = Field(..., description="完整的回答文本")


class ConversationTurn(BaseModel):
    """对话回合"""
    turn_id: int = Field(..., description="回合ID")
    student_id: int = Field(..., description="学生ID")
    course_id: int = Field(..., description="课程ID")
    question: str = Field(..., description="学生问题")
    answer: Optional[str] = Field(default=None, description="系统回答")
    timestamp: datetime = Field(default_factory=datetime.now)


class QAContext(BaseModel):
    """问答上下文"""
    student_profile: dict = Field(..., description="学生档案")
    course_progress: float = Field(..., description="课程进度")
    conversation_history: list[dict] = Field(description="对话历史")
    courseware_analysis: Optional[dict] = Field(default=None, description="课件解析")


class ConversationHistoryItem(BaseModel):
    """对话历史项"""
    id: int = Field(..., description="历史记录ID")
    course_id: int = Field(..., description="课程ID")
    question: str = Field(..., description="学生问题")
    answer: Optional[str] = Field(default=None, description="系统回答")
    timestamp: datetime = Field(default_factory=datetime.now)


class QAHistoryItem(BaseModel):
    """问答历史项"""
    id: int = Field(..., description="历史记录ID")
    course_id: int = Field(..., description="课程ID")
    courseware_id: Optional[int] = Field(default=None, description="课件ID")
    question: str = Field(..., description="学生问题")
    answer: Optional[str] = Field(default=None, description="系统回答")
    timestamp: datetime = Field(default_factory=datetime.now)


class StreamChunk(BaseModel):
    """流式响应块"""
    content: str = Field(..., description="文本内容块")
