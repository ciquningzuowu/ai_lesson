"""数据库模型模块

集中管理所有数据库实体模型，使用 Tortoise ORM。
与新课程体系对齐：课程(Course) + 课件(Courseware)

数据模型：
- Teacher: 教师表
- Student: 学生表
- Course: 课程表
- Courseware: 课件表
- CoursewareVector: 课件向量表
- ChatHistory: 对话历史表
- LearningProgress: 学习进度表
- Quiz: 测验表
- Question: 题目表
- LearningAnalytics: 学习分析表
"""

from tortoise import fields
from tortoise.models import Model


class Teacher(Model):
    """教师模型"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "teachers"


class Student(Model):
    """学生模型"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "students"


class Course(Model):
    """课程模型"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    teacher = fields.ForeignKeyField("main.Teacher", related_name="courses")
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "courses"


class Courseware(Model):
    """课件模型"""
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    content = fields.BinaryField(null=True)  # 存储文件二进制（pptx/pdf）
    parse_result = fields.JSONField(null=True)
    file_type = fields.CharField(max_length=20, null=True)
    script = fields.TextField(null=True)
    course = fields.ForeignKeyField("main.Course", related_name="coursewares")
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "courseware"


class CoursewareVector(Model):
    """课件向量模型

    MySQL 原生 VECTOR 类型存储，维度由 EMBEDDING_CONFIG.dimension 配置。
    ORM 层以字符串形式存储，格式为 "[-0.123, 0.456, ...]"
    """
    id = fields.IntField(pk=True)
    courseware = fields.OneToOneField("main.Courseware", related_name="vector")
    embedding = fields.TextField(null=True)  # MySQL VECTOR 以字符串存储
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "courseware_vectors"


class ChatHistory(Model):
    """对话历史模型"""
    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField("main.Student", related_name="chat_histories")
    course = fields.ForeignKeyField("main.Course", related_name="chat_histories")
    question = fields.TextField()
    answer = fields.TextField(null=True)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_history"


class LearningProgress(Model):
    """学习进度模型"""
    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField("main.Student", related_name="learning_progresses")
    course = fields.ForeignKeyField("main.Course", related_name="learning_progresses")
    progress = fields.IntField(default=0)
    is_completed = fields.BooleanField(default=False)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "learning_progress"


class LearningAnalytics(Model):
    """学习分析模型"""
    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField("main.Student", related_name="learning_analytics")
    course = fields.ForeignKeyField("main.Course", related_name="learning_analytics")
    courseware = fields.ForeignKeyField("main.Courseware", related_name="learning_analytics", null=True)
    status_data = fields.JSONField(null=True)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "learning_analytics"


class Quiz(Model):
    """测验模型"""
    id = fields.IntField(pk=True)
    course = fields.ForeignKeyField("main.Course", related_name="quizzes")
    student = fields.ForeignKeyField("main.Student", related_name="quizzes")
    questions = fields.JSONField()
    answers = fields.JSONField()
    score = fields.FloatField(null=True)
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "quizzes"


class Question(Model):
    """题目模型"""
    id = fields.IntField(pk=True)
    quiz = fields.ForeignKeyField("main.Quiz", related_name="question_items")
    content = fields.TextField()
    answer = fields.TextField()
    student_answer = fields.TextField(null=True)
    is_correct = fields.BooleanField(null=True)
    submitted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "questions"


__all__ = [
    "Teacher",
    "Student",
    "Course",
    "Courseware",
    "CoursewareVector",
    "ChatHistory",
    "LearningProgress",
    "LearningAnalytics",
    "Quiz",
    "Question",
]