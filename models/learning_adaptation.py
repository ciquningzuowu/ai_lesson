"""学习适应相关的数据模型

定义学习适应模块的请求和响应数据结构。
与新课程体系对齐：课程(Course) + 课件(Courseware)
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class RhythmSignal(str, Enum):
    """节奏信号"""
    KEEP = "keep"  # 保持当前节奏
    UP = "up"  # 加速
    SUPPLEMENT = "supplement"  # 需要补充讲解


class AdjustRhythmRequest(BaseModel):
    """调整学习节奏请求"""
    student_id: int = Field(..., description="学生ID")
    course_id: Optional[int] = Field(default=None, description="课程ID（可选）")


class AdjustRhythmResponse(BaseModel):
    """调整学习节奏响应"""
    rhythm_signal: RhythmSignal = Field(..., description="节奏信号")
    supplement_script: Optional[str] = Field(default=None, description="补充讲解脚本")


class StudentProfile(BaseModel):
    """学生学习档案"""
    student_id: int = Field(..., description="学生ID")
    name: str = Field(..., description="学生姓名")
    total_courses: int = Field(default=0, description="已完成课程数")
    total_quizzes: int = Field(default=0, description="完成测验数")
    average_score: float = Field(default=0.0, description="平均得分")
    learning_style: Optional[str] = Field(default=None, description="学习风格偏好")
    create_time: datetime = Field(default_factory=datetime.now)


class CourseProgress(BaseModel):
    """课程进度"""
    course_id: int = Field(..., description="课程ID")
    student_id: int = Field(..., description="学生ID")
    progress: int = Field(ge=0, le=100, default=0, description="完成进度")
    is_completed: bool = Field(default=False, description="是否已完成")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")


class InteractionHistory(BaseModel):
    """交互历史"""
    student_id: int = Field(..., description="学生ID")
    course_id: int = Field(..., description="课程ID")
    interaction_type: str = Field(..., description="交互类型(qa/quiz)")
    content: str = Field(..., description="交互内容")
    response: Optional[str] = Field(default=None, description="系统响应")
    timestamp: datetime = Field(default_factory=datetime.now)


class LearningAnalyticsData(BaseModel):
    """学习分析数据"""
    student_id: int = Field(..., description="学生ID")
    course_id: int = Field(..., description="课程ID")
    courseware_id: Optional[int] = Field(default=None, description="课件ID")
    status_data: dict = Field(..., description="学习状况快照")
    update_time: datetime = Field(default_factory=datetime.now)


class StudentStatusResponse(BaseModel):
    """学生学习状态响应"""
    student_id: int = Field(..., description="学生ID")
    progress: int = Field(ge=0, le=100, description="学习进度百分比")
    lessons_completed: int = Field(..., description="已完成课件数")
    quizzes_completed: int = Field(..., description="已完成测验数")
    avg_score: float = Field(..., description="平均得分")
    learning_style: Optional[str] = Field(default=None, description="学习风格")


class QuizHistoryResponse(BaseModel):
    """答题历史响应"""
    quiz_id: int = Field(..., description="测验ID")
    course_id: int = Field(..., description="课程ID")
    score: float = Field(..., description="得分")
    correct_count: int = Field(..., description="正确题数")
    total_count: int = Field(..., description="总题数")
    create_time: datetime = Field(default_factory=datetime.now)


class QAHistoryResponse(BaseModel):
    """问答历史响应"""
    id: int = Field(..., description="历史记录ID")
    course_id: int = Field(..., description="课程ID")
    courseware_id: Optional[int] = Field(default=None, description="课件ID")
    question: str = Field(..., description="学生问题")
    answer: Optional[str] = Field(default=None, description="系统回答")
    timestamp: datetime = Field(default_factory=datetime.now)
