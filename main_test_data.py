"""测试数据初始化脚本

运行方式：python main_test_data.py

此脚本会：
1. 初始化数据库连接
2. 创建所有测试数据表（如不存在）
3. 插入测试用例数据
4. 验证插入结果
"""

import asyncio
import logging
from datetime import datetime

from models.database_models import (
    Teacher,
    Student,
    Course,
    Courseware,
    CoursewareVector,
    ChatHistory,
    LearningProgress,
    LearningAnalytics,
    Quiz,
    Question,
)
from utils.database import init_db, close_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def clear_existing_data():
    """清空现有数据（按外键依赖顺序）"""
    logger.info("清空现有数据...")
    await Question.all().delete()
    await Quiz.all().delete()
    await LearningAnalytics.all().delete()
    await LearningProgress.all().delete()
    await ChatHistory.all().delete()
    await CoursewareVector.all().delete()
    await Courseware.all().delete()
    await Course.all().delete()
    await Student.all().delete()
    await Teacher.all().delete()
    logger.info("清空完成")


async def create_teachers():
    """创建教师数据"""
    logger.info("创建教师数据...")
    teachers = [
        Teacher(id=1, name="张教授"),
        Teacher(id=2, name="李老师"),
        Teacher(id=3, name="王讲师"),
    ]
    await Teacher.bulk_create(teachers)
    logger.info(f"已创建 {len(teachers)} 名教师")
    return teachers


async def create_students():
    """创建学生数据"""
    logger.info("创建学生数据...")
    students = [
        Student(id=1, name="小明"),
        Student(id=2, name="小红"),
        Student(id=3, name="小刚"),
    ]
    await Student.bulk_create(students)
    logger.info(f"已创建 {len(students)} 名学生")
    return students


async def create_courses():
    """创建课程数据"""
    logger.info("创建课程数据...")
    courses = [
        Course(id=1, name="Python编程基础", teacher_id=1),
        Course(id=2, name="数据结构与算法", teacher_id=2),
        Course(id=3, name="人工智能导论", teacher_id=3),
    ]
    await Course.bulk_create(courses)
    logger.info(f"已创建 {len(courses)} 门课程")
    return courses


async def create_coursewares():
    """创建课件数据"""
    logger.info("创建课件数据...")
    coursewares = [
        Courseware(
            id=1,
            title="第一章概述",
            content="Python是一种高级编程语言，由Guido van Rossum于1991年创建。\nPython具有以下特点：\n1. 简单易学的语法\n2. 丰富的标准库\n3. 跨平台支持\n4. 动态类型",
            parse_result={
                "summary": "Python语言概述与特点",
                "key_points": ["高级语言", "简单易学", "标准库丰富", "跨平台"],
            },
            file_type="pptx",
            script="本章节介绍Python语言的基本概念和特点。Python由Guido创建，是一种高级编程语言，具有简单易学、库丰富、跨平台等特点。",
            course_id=1,
        ),
        Courseware(
            id=2,
            title="变量与数据类型",
            content="变量是存储数据的容器。\nPython支持多种数据类型：\n- 整数(int)：如 1, 100, -5\n- 浮点数(float)：如 3.14, -0.5\n- 字符串(str)：如 'hello'\n- 布尔值(bool)：True, False\n\n变量命名规则：\n1. 必须以字母或下划线开头\n2. 区分大小写\n3. 不能使用关键字",
            parse_result={
                "summary": "Python变量与数据类型详解",
                "key_points": ["变量定义", "整数", "浮点数", "字符串", "布尔值"],
            },
            file_type="pdf",
            script="本章节讲解Python中的变量定义和基本数据类型，包括整数、浮点数、字符串和布尔值。",
            course_id=1,
        ),
        Courseware(
            id=3,
            title="链表介绍",
            content="链表是一种线性数据结构。\n\n特点：\n1. 元素之间通过指针连接\n2. 不需要连续的内存空间\n3. 插入和删除操作效率高\n\n类型：\n- 单向链表：每个节点包含数据和下一个节点的指针\n- 双向链表：每个节点包含数据、指向前后节点的指针\n\n时间复杂度：\n- 访问：O(n)\n- 插入/删除：O(1)",
            parse_result={
                "summary": "链表数据结构详解",
                "key_points": ["单向链表", "双向链表", "指针", "时间复杂度"],
            },
            file_type="pptx",
            script="本章介绍链表这种重要的数据结构，包括单向链表和双向链表的原理与特点。",
            course_id=2,
        ),
    ]
    await Courseware.bulk_create(coursewares)
    logger.info(f"已创建 {len(coursewares)} 个课件")
    return coursewares


async def create_courseware_vectors():
    """创建课件向量数据"""
    logger.info("创建课件向量数据...")
    vectors = [
        CoursewareVector(
            id=1,
            courseware_id=1,
            embedding=[0.123, 0.456, 0.789, 0.012, 0.345],
        ),
        CoursewareVector(
            id=2,
            courseware_id=2,
            embedding=[0.789, 0.012, 0.345, 0.678, 0.901],
        ),
        CoursewareVector(
            id=3,
            courseware_id=3,
            embedding=[0.345, 0.678, 0.901, 0.234, 0.567],
        ),
    ]
    await CoursewareVector.bulk_create(vectors)
    logger.info(f"已创建 {len(vectors)} 条向量数据")
    return vectors


async def create_chat_histories():
    """创建对话历史数据"""
    logger.info("创建对话历史数据...")
    histories = [
        ChatHistory(
            id=1,
            student_id=1,
            course_id=1,
            question="Python怎么定义变量？",
            answer="Python定义变量非常简单，直接使用等号赋值即可。例如：x = 10，name = 'Alice'。不需要声明变量类型，Python会自动推断。",
        ),
        ChatHistory(
            id=2,
            student_id=2,
            course_id=1,
            question="什么是循环？",
            answer="循环用于重复执行一段代码。Python中有两种循环：for循环用于遍历序列，while循环在条件为真时重复执行。",
        ),
        ChatHistory(
            id=3,
            student_id=1,
            course_id=2,
            question="链表和数组有什么区别？",
            answer="主要区别：1）数组需要连续内存空间，链表不需要；2）数组访问快O(1)，链表访问慢O(n)；3）链表插入删除快O(1)，数组需要移动元素。",
        ),
    ]
    await ChatHistory.bulk_create(histories)
    logger.info(f"已创建 {len(histories)} 条对话历史")
    return histories


async def create_learning_progress():
    """创建学习进度数据"""
    logger.info("创建学习进度数据...")
    progress_list = [
        LearningProgress(
            id=1,
            student_id=1,
            course_id=1,
            progress=80,
            is_completed=False,
            started_at=datetime(2026, 4, 1, 9, 0, 0),
        ),
        LearningProgress(
            id=2,
            student_id=2,
            course_id=1,
            progress=100,
            is_completed=True,
            started_at=datetime(2026, 4, 1, 10, 0, 0),
            completed_at=datetime(2026, 4, 5, 16, 30, 0),
        ),
        LearningProgress(
            id=3,
            student_id=1,
            course_id=2,
            progress=30,
            is_completed=False,
            started_at=datetime(2026, 4, 6, 14, 0, 0),
        ),
    ]
    await LearningProgress.bulk_create(progress_list)
    logger.info(f"已创建 {len(progress_list)} 条学习进度")
    return progress_list


async def create_learning_analytics():
    """创建学习分析数据"""
    logger.info("创建学习分析数据...")
    analytics = [
        LearningAnalytics(
            id=1,
            student_id=1,
            course_id=1,
            courseware_id=1,
            status_data={
                "focus_level": 0.8,
                "confusion": False,
                "time_spent": 1200,
                "interaction_count": 5,
            },
        ),
        LearningAnalytics(
            id=2,
            student_id=2,
            course_id=1,
            courseware_id=2,
            status_data={
                "focus_level": 0.6,
                "confusion": True,
                "time_spent": 800,
                "interaction_count": 8,
            },
        ),
        LearningAnalytics(
            id=3,
            student_id=1,
            course_id=2,
            courseware_id=3,
            status_data={
                "focus_level": 0.9,
                "confusion": False,
                "time_spent": 1500,
                "interaction_count": 3,
            },
        ),
    ]
    await LearningAnalytics.bulk_create(analytics)
    logger.info(f"已创建 {len(analytics)} 条学习分析数据")
    return analytics


async def create_quizzes():
    """创建测验数据"""
    logger.info("创建测验数据...")
    quizzes = [
        Quiz(
            id=1,
            course_id=1,
            student_id=1,
            questions=[
                {"q1": "Python中如何定义列表？", "options": ["list()", "[]", "dict()", "{}"]},
                {"q2": "什么是字典？", "options": ["键值对容器", "列表", "元组", "集合"]},
                {"q3": "for循环用于什么？", "options": ["遍历序列", "条件判断", "异常处理", "函数定义"]},
            ],
            answers=[1, 0, 0],
            score=85.5,
        ),
        Quiz(
            id=2,
            course_id=1,
            student_id=2,
            questions=[
                {"q1": "Python中如何定义列表？", "options": ["list()", "[]", "dict()", "{}"]},
            ],
            answers=[1],
            score=100.0,
        ),
        Quiz(
            id=3,
            course_id=2,
            student_id=1,
            questions=[
                {"q1": "链表的插入时间复杂度是？", "options": ["O(1)", "O(n)", "O(log n)", "O(n^2)"]},
                {"q2": "单向链表每个节点有几个指针？", "options": ["1个", "2个", "3个", "0个"]},
                {"q3": "数组的优势是什么？", "options": ["随机访问快", "插入快", "不需要内存", "灵活性高"]},
            ],
            answers=[0, 0, 0],
            score=66.7,
        ),
    ]
    await Quiz.bulk_create(quizzes)
    logger.info(f"已创建 {len(quizzes)} 个测验")
    return quizzes


async def create_questions():
    """创建题目数据"""
    logger.info("创建题目数据...")
    questions = [
        # Quiz 1 的题目
        Question(
            id=1,
            quiz_id=1,
            content="Python中如何定义列表？",
            answer="[] 或 list()",
            student_answer="[]",
            is_correct=True,
            submitted_at=datetime(2026, 4, 7, 10, 30, 0),
        ),
        Question(
            id=2,
            quiz_id=1,
            content="什么是字典？",
            answer="键值对容器",
            student_answer="键值对容器",
            is_correct=True,
            submitted_at=datetime(2026, 4, 7, 10, 35, 0),
        ),
        Question(
            id=3,
            quiz_id=1,
            content="for循环用于什么？",
            answer="遍历序列",
            student_answer="条件判断",
            is_correct=False,
            submitted_at=datetime(2026, 4, 7, 10, 40, 0),
        ),
        # Quiz 2 的题目
        Question(
            id=4,
            quiz_id=2,
            content="Python中如何定义列表？",
            answer="[] 或 list()",
            student_answer="[]",
            is_correct=True,
            submitted_at=datetime(2026, 4, 7, 11, 0, 0),
        ),
        # Quiz 3 的题目
        Question(
            id=5,
            quiz_id=3,
            content="链表的插入时间复杂度是？",
            answer="O(1)",
            student_answer="O(1)",
            is_correct=True,
            submitted_at=datetime(2026, 4, 7, 14, 0, 0),
        ),
        Question(
            id=6,
            quiz_id=3,
            content="单向链表每个节点有几个指针？",
            answer="1个",
            student_answer="1个",
            is_correct=True,
            submitted_at=datetime(2026, 4, 7, 14, 5, 0),
        ),
        Question(
            id=7,
            quiz_id=3,
            content="数组的优势是什么？",
            answer="随机访问快",
            student_answer="插入快",
            is_correct=False,
            submitted_at=datetime(2026, 4, 7, 14, 10, 0),
        ),
    ]
    await Question.bulk_create(questions)
    logger.info(f"已创建 {len(questions)} 道题目")
    return questions


async def verify_data():
    """验证数据插入结果"""
    logger.info("\n========== 数据验证 ==========")
    logger.info(f"教师数量: {await Teacher.all().count()}")
    logger.info(f"学生数量: {await Student.all().count()}")
    logger.info(f"课程数量: {await Course.all().count()}")
    logger.info(f"课件数量: {await Courseware.all().count()}")
    logger.info(f"向量数量: {await CoursewareVector.all().count()}")
    logger.info(f"对话历史: {await ChatHistory.all().count()}")
    logger.info(f"学习进度: {await LearningProgress.all().count()}")
    logger.info(f"学习分析: {await LearningAnalytics.all().count()}")
    logger.info(f"测验数量: {await Quiz.all().count()}")
    logger.info(f"题目数量: {await Question.all().count()}")
    logger.info("========== 验证完成 ==========\n")


async def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始初始化测试数据...")
    logger.info("=" * 50)

    # 初始化数据库
    await init_db()
    logger.info("数据库初始化完成")

    try:
        # 清空现有数据
        await clear_existing_data()

        # 按依赖顺序创建数据
        await create_teachers()
        await create_students()
        await create_courses()
        await create_coursewares()
        await create_courseware_vectors()
        await create_chat_histories()
        await create_learning_progress()
        await create_learning_analytics()
        await create_quizzes()
        await create_questions()

        # 验证结果
        await verify_data()

        logger.info("=" * 50)
        logger.info("测试数据初始化完成！")
        logger.info("=" * 50)

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
