"""评估测验相关的数据模型

定义评估测验模块的请求和响应数据结构。
与新课程体系对齐：课程(Course) + 课件(Courseware)
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class QuestionType(str, Enum):
    """题目类型枚举"""
    FILL_BLANK = "fill_blank"  # 填空题
    QA = "qa"  # 问答题


class StudentAnswer(BaseModel):
    """学生答案模型"""
    question_id: int = Field(..., description="题目ID")
    answer: str = Field(..., description="学生回答")
    submitted_at: Optional[datetime] = Field(default_factory=datetime.now, description="提交时间")


class AnalysisRequest(BaseModel):
    """答案分析请求"""
    question_id: int = Field(..., description="题目ID")
    course_id: int = Field(..., description="课程ID（替代原lesson_id）")
    courseware_id: Optional[int] = Field(default=None, description="课件ID")
    student_id: int = Field(..., description="学生ID")
    answer: str = Field(..., description="学生的回答")


class AnalysisResponse(BaseModel):
    """答案分析响应"""
    analysis: str = Field(..., description="答案分析")
    answer_condition: str = Field(..., description="学生学习情况分析")


class GenerateQuizRequest(BaseModel):
    """生成测验请求"""
    course_id: int = Field(..., description="课程ID（替代原lesson_id）")
    courseware_id: Optional[int] = Field(default=None, description="课件ID")
    student_id: int = Field(..., description="学生ID")
    num: int = Field(default=5, ge=1, le=20, description="题目数量")
    type: QuestionType = Field(default=QuestionType.QA, description="题目类型")


class GenerateQuizResponse(BaseModel):
    """生成测验响应"""
    questions: list[str] = Field(..., description="题目列表")
    answers: list[str] = Field(..., description="答案列表")


class QuizRecord(BaseModel):
    """测验记录"""
    quiz_id: int = Field(..., description="测验ID")
    course_id: int = Field(..., description="课程ID")
    student_id: int = Field(..., description="学生ID")
    questions: list[str] = Field(..., description="题目列表")
    answers: list[str] = Field(..., description="答案列表")
    score: Optional[float] = Field(default=None, description="得分")
    create_time: datetime = Field(default_factory=datetime.now)


class AnswerItem(BaseModel):
    """答案项"""
    question_id: int = Field(..., description="题目ID")
    answer: str = Field(..., description="学生回答")


class SubmitQuizRequest(BaseModel):
    """提交测验请求"""
    answers: list[AnswerItem] = Field(..., description="答案列表")


class SubmitQuizResponse(BaseModel):
    """提交测验响应"""
    quiz_id: int = Field(..., description="测验ID")
    score: float = Field(..., description="得分")
    correct_count: int = Field(..., description="正确题数")
    total_count: int = Field(..., description="总题数")


class QuizHistoryItem(BaseModel):
    """答题历史项"""
    quiz_id: int = Field(..., description="测验ID")
    course_id: int = Field(..., description="课程ID")
    score: float = Field(..., description="得分")
    correct_count: int = Field(..., description="正确题数")
    total_count: int = Field(..., description="总题数")
    create_time: datetime = Field(default_factory=datetime.now)


class QuestionRecord(BaseModel):
    """题目记录"""
    question_id: int = Field(..., description="题目ID")
    content: str = Field(..., description="题目内容")
    answer: Optional[str] = Field(default=None, description="正确答案")
    student_answer: Optional[str] = Field(default=None, description="学生答案")
    is_correct: Optional[bool] = Field(default=None, description="是否正确")
    submitted_at: Optional[datetime] = Field(default=None, description="提交时间")
