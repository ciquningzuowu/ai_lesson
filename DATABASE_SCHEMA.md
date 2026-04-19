# AI智能交互课件系统 - 数据库结构说明

> **版本**: v1.3.0
> **更新日期**: 2026-04-18
> **ORM框架**: Tortoise ORM
> **支持数据库**: MySQL / SQLite

---

## 一、数据库概述

### 1.1 设计理念

系统采用 **课程-课件两级结构**：

```
Teacher (教师)
    └── Course (课程)
            └── Courseware (课件)
                    └── CoursewareVector (课件向量)
```

### 1.2 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| ORM框架 | Tortoise ORM | 异步ORM，支持MySQL/SQLite |
| 向量存储 | MySQL VECTOR | 文本嵌入向量存储 |
| 缓存层 | Redis | 任务进度追踪、会话缓存 |

### 1.3 命名规范

- **表名**: 蛇形命名 (snake_case)，使用单数形式
- **字段名**: 蛇形命名 (snake_case)
- **外键**: `{表名}_id` 格式

---

## 二、数据表结构

### 2.1 教师表 (teachers)

存储系统中的教师信息。

```sql
CREATE TABLE teachers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '教师姓名',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| name | VARCHAR(100) | NOT NULL | 教师姓名 |
| create_time | DATETIME | DEFAULT NOW() | 创建时间 |

**Python模型**:
```python
class Teacher(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    create_time = fields.DatetimeField(auto_now_add=True)
```

---

### 2.2 学生表 (students)

存储系统中的学生信息。

```sql
CREATE TABLE students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '学生姓名',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| name | VARCHAR(100) | NOT NULL | 学生姓名 |
| create_time | DATETIME | DEFAULT NOW() | 创建时间 |

**Python模型**:
```python
class Student(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    create_time = fields.DatetimeField(auto_now_add=True)
```

---

### 2.3 课程表 (courses)

存储课程基本信息。

```sql
CREATE TABLE courses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL COMMENT '课程名称',
    teacher_id INT NOT NULL COMMENT '授课教师ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课程表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| name | VARCHAR(255) | NOT NULL | 课程名称 |
| teacher_id | INT | FK -> teachers | 授课教师ID |
| create_time | DATETIME | DEFAULT NOW() | 创建时间 |

**Python模型**:
```python
class Course(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    teacher = fields.ForeignKeyField("main.Teacher", related_name="courses")
    create_time = fields.DatetimeField(auto_now_add=True)
```

**关系**:
- Teacher 1:N Course (一个教师可以创建多个课程)

---

### 2.4 课件表 (courseware)

存储课件文件和相关解析结果。

```sql
CREATE TABLE courseware (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL COMMENT '课件标题',
    content LONGBLOB NULL COMMENT '原始文件二进制',
    parse_result JSON NULL COMMENT '解析结果',
    file_type VARCHAR(20) NULL COMMENT '文件类型(ppt/pdf/text)',
    script TEXT NULL COMMENT '讲解脚本',
    course_id INT NOT NULL COMMENT '所属课程ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课件表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| title | VARCHAR(255) | NOT NULL | 课件标题 |
| content | LONGBLOB | NULL | 原始文件二进制(pptx/pdf) |
| parse_result | JSON | NULL | 解析结果(摘要/关键点等) |
| file_type | VARCHAR(20) | NULL | 文件类型(ppt/pdf/text) |
| script | TEXT | NULL | AI生成的讲解脚本 |
| course_id | INT | FK -> courses | 所属课程ID |
| create_time | DATETIME | DEFAULT NOW() | 创建时间 |

**Python模型**:
```python
class Courseware(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    content = fields.BinaryField(null=True)
    parse_result = fields.JSONField(null=True)
    file_type = fields.CharField(max_length=20, null=True)
    script = fields.TextField(null=True)
    course = fields.ForeignKeyField("main.Course", related_name="coursewares")
    create_time = fields.DatetimeField(auto_now_add=True)
```

**关系**:
- Course 1:N Courseware (一个课程包含多个课件)

**parse_result 字段示例**:
```json
{
    "summary": "本节课介绍人工智能的基本概念...",
    "main_topics": ["AI定义", "发展历史", "应用领域"],
    "key_points": ["人工智能是研究、开发用于模拟..."],
    "key_concepts": ["机器学习", "深度学习", "神经网络"]
}
```

---

### 2.5 课件向量表 (courseware_vectors)

存储课件内容的向量嵌入，用于RAG检索。

```sql
CREATE TABLE courseware_vectors (
    id INT PRIMARY KEY AUTO_INCREMENT,
    courseware_id INT NOT NULL UNIQUE COMMENT '课件ID',
    embedding TEXT NULL COMMENT '嵌入向量(JSON字符串)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (courseware_id) REFERENCES courseware(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课件向量表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| courseware_id | INT | FK -> courseware, UNIQUE | 课件ID |
| embedding | TEXT | NULL | 嵌入向量(JSON字符串格式) |
| create_time | DATETIME | DEFAULT NOW() | 创建时间 |

**Python模型**:
```python
class CoursewareVector(Model):
    id = fields.IntField(pk=True)
    courseware = fields.OneToOneField("main.Courseware", related_name="vector")
    embedding = fields.TextField(null=True)
    create_time = fields.DatetimeField(auto_now_add=True)
```

**关系**:
- Courseware 1:1 CoursewareVector (一对一)

**embedding 字段示例**:
```json
"[-0.0123, 0.0456, -0.0789, ...]"  // 向量数组转为字符串
```

---

### 2.6 对话历史表 (chat_history)

存储学生与AI助手的问答对话记录。

```sql
CREATE TABLE chat_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL COMMENT '学生ID',
    course_id INT NOT NULL COMMENT '课程ID',
    question TEXT NOT NULL COMMENT '学生问题',
    answer TEXT NULL COMMENT 'AI回答',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '对话时间',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话历史表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| student_id | INT | FK -> students | 学生ID |
| course_id | INT | FK -> courses | 课程ID |
| question | TEXT | NOT NULL | 学生问题 |
| answer | TEXT | NULL | AI回答 |
| timestamp | DATETIME | DEFAULT NOW() | 对话时间 |

**Python模型**:
```python
class ChatHistory(Model):
    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField("main.Student", related_name="chat_histories")
    course = fields.ForeignKeyField("main.Course", related_name="chat_histories")
    question = fields.TextField()
    answer = fields.TextField(null=True)
    timestamp = fields.DatetimeField(auto_now_add=True)
```

**关系**:
- Student 1:N ChatHistory (一个学生有多条对话)
- Course 1:N ChatHistory (一个课程有多条对话)

---

### 2.7 学习进度表 (learning_progress)

跟踪学生在各课程中的学习进度。

```sql
CREATE TABLE learning_progress (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL COMMENT '学生ID',
    course_id INT NOT NULL COMMENT '课程ID',
    progress INT DEFAULT 0 COMMENT '进度百分比(0-100)',
    is_completed BOOLEAN DEFAULT FALSE COMMENT '是否完成',
    started_at DATETIME NULL COMMENT '开始学习时间',
    completed_at DATETIME NULL COMMENT '完成时间',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE KEY uk_student_course (student_id, course_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学习进度表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| student_id | INT | FK -> students | 学生ID |
| course_id | INT | FK -> courses | 课程ID |
| progress | INT | DEFAULT 0 | 进度百分比(0-100) |
| is_completed | BOOLEAN | DEFAULT FALSE | 是否完成 |
| started_at | DATETIME | NULL | 开始学习时间 |
| completed_at | DATETIME | NULL | 完成时间 |

**Python模型**:
```python
class LearningProgress(Model):
    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField("main.Student", related_name="learning_progresses")
    course = fields.ForeignKeyField("main.Course", related_name="learning_progresses")
    progress = fields.IntField(default=0)
    is_completed = fields.BooleanField(default=False)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)
```

**关系**:
- Student 1:N LearningProgress (一个学生有多条进度记录)
- Course 1:N LearningProgress (一个课程有多条进度记录)

**约束**: 同一学生同一课程唯一 (UNIQUE student_id + course_id)

---

### 2.8 学习分析表 (learning_analytics)

存储学生的学习状况快照和综合分析数据。

```sql
CREATE TABLE learning_analytics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL COMMENT '学生ID',
    course_id INT NOT NULL COMMENT '课程ID',
    courseware_id INT NULL COMMENT '课件ID(可选)',
    status_data JSON NULL COMMENT '学习状况快照',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (courseware_id) REFERENCES courseware(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学习分析表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| student_id | INT | FK -> students | 学生ID |
| course_id | INT | FK -> courses | 课程ID |
| courseware_id | INT | FK -> courseware, NULL | 课件ID(可选) |
| status_data | JSON | NULL | 学习状况快照 |
| update_time | DATETIME | AUTO UPDATE | 更新时间 |

**Python模型**:
```python
class LearningAnalytics(Model):
    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField("main.Student", related_name="learning_analytics")
    course = fields.ForeignKeyField("main.Course", related_name="learning_analytics")
    courseware = fields.ForeignKeyField("main.Courseware", related_name="learning_analytics", null=True)
    status_data = fields.JSONField(null=True)
    update_time = fields.DatetimeField(auto_now=True)
```

**关系**:
- Student 1:N LearningAnalytics
- Course 1:N LearningAnalytics
- Courseware 1:N LearningAnalytics (可选关联)

**status_data 字段示例**:
```json
{
    "avg_score": 85.5,
    "quiz_count": 10,
    "correct_rate": 0.85,
    "learning_style": "综合",
    "weak_points": ["算法分析", "数据结构"],
    "strong_points": ["基础概念", "编程实践"]
}
```

---

### 2.9 测验表 (quizzes)

存储每次测验的基本信息。

```sql
CREATE TABLE quizzes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    course_id INT NOT NULL COMMENT '课程ID',
    student_id INT NOT NULL COMMENT '学生ID',
    questions JSON NOT NULL COMMENT '题目列表',
    answers JSON NULL COMMENT '答案列表',
    score FLOAT NULL COMMENT '得分',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测验表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| course_id | INT | FK -> courses | 课程ID |
| student_id | INT | FK -> students | 学生ID |
| questions | JSON | NOT NULL | 题目列表 |
| answers | JSON | NULL | 答案列表 |
| score | FLOAT | NULL | 得分(0-100) |
| create_time | DATETIME | DEFAULT NOW() | 创建时间 |

**Python模型**:
```python
class Quiz(Model):
    id = fields.IntField(pk=True)
    course = fields.ForeignKeyField("main.Course", related_name="quizzes")
    student = fields.ForeignKeyField("main.Student", related_name="quizzes")
    questions = fields.JSONField()
    answers = fields.JSONField()
    score = fields.FloatField(null=True)
    create_time = fields.DatetimeField(auto_now_add=True)
```

**关系**:
- Course 1:N Quiz
- Student 1:N Quiz
- Quiz 1:N Question (一个测验包含多道题目)

**questions 字段示例**:
```json
[
    {"id": 1, "content": "什么是人工智能？", "type": "qa"},
    {"id": 2, "content": "机器学习是_____的子领域", "type": "fill_blank"}
]
```

---

### 2.10 题目表 (questions)

存储测验中的每道题目及其答案信息。

```sql
CREATE TABLE questions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    quiz_id INT NOT NULL COMMENT '所属测验ID',
    content TEXT NOT NULL COMMENT '题目内容',
    answer TEXT NOT NULL COMMENT '正确答案',
    student_answer TEXT NULL COMMENT '学生答案',
    is_correct BOOLEAN NULL COMMENT '是否正确',
    submitted_at DATETIME NULL COMMENT '提交时间',
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='题目表';
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 主键 |
| quiz_id | INT | FK -> quizzes | 所属测验ID |
| content | TEXT | NOT NULL | 题目内容 |
| answer | TEXT | NOT NULL | 正确答案 |
| student_answer | TEXT | NULL | 学生答案 |
| is_correct | BOOLEAN | NULL | 是否正确 |
| submitted_at | DATETIME | NULL | 提交时间 |

**Python模型**:
```python
class Question(Model):
    id = fields.IntField(pk=True)
    quiz = fields.ForeignKeyField("main.Quiz", related_name="question_items")
    content = fields.TextField()
    answer = fields.TextField()
    student_answer = fields.TextField(null=True)
    is_correct = fields.BooleanField(null=True)
    submitted_at = fields.DatetimeField(null=True)
```

**关系**:
- Quiz 1:N Question (一个测验包含多道题目)

---

## 三、表关系图

### 3.1 实体关系图 (ER Diagram)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           核心业务实体                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐                                                     │
│   │   teachers   │                                                     │
│   └──────┬───────┘                                                     │
│          │ 1:N                                                        │
│          ▼                                                             │
│   ┌──────────────┐                                                     │
│   │   courses    │                                                     │
│   └──────┬───────┘                                                     │
│          │ 1:N                                                        │
│          ▼                                                             │
│   ┌──────────────┐       ┌─────────────────────┐                      │
│   │  courseware  │──────<│ courseware_vectors   │                      │
│   └──────┬───────┘  1:1 └─────────────────────┘                      │
│          │                                                             │
│          │                                                             │
├──────────┼─────────────────────────────────────────────────────────────┤
│          │                                                             │
│          ▼                                                             │
│   ┌──────────────┐                                                     │
│   │   students   │                                                     │
│   └──────┬───────┘                                                     │
│          │ 1:N                                                         │
│          ├──────────────────────────────────────┐                     │
│          │                                      │                     │
│          ▼                                      ▼                     │
│   ┌──────────────┐                     ┌──────────────┐               │
│   │ chat_history │                     │learning_     │               │
│   └──────────────┘                     │ progress     │               │
│          │                             └──────────────┘               │
│          │                                      │                     │
│          │                             ┌──────────────┐               │
│          │                             │learning_     │               │
│          │                             │ analytics    │               │
│          │                             └──────────────┘               │
│          │                                      │                     │
│          └──────────────────────────────────────▼                     │
│                                                      │                 │
│   ┌──────────────┐                                   │                 │
│   │   quizzes    │───────────────────────────────────┘                 │
│   └──────┬───────┘                                                       │
│          │ 1:N                                                            │
│          ▼                                                                │
│   ┌──────────────┐                                                        │
│   │  questions   │                                                        │
│   └──────────────┘                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 关系说明表

| 父表 | 关系 | 子表 | 说明 |
|------|------|------|------|
| Teacher | 1:N | Course | 一个教师可创建多门课程 |
| Course | 1:N | Courseware | 一个课程包含多个课件 |
| Course | 1:N | ChatHistory | 一个课程的对话历史 |
| Course | 1:N | LearningProgress | 一个课程的学习进度 |
| Course | 1:N | LearningAnalytics | 一个课程的学习分析 |
| Course | 1:N | Quiz | 一个课程的测验记录 |
| Course | 1:N | LearningProgress | 一个课程的学习进度 |
| Courseware | 1:1 | CoursewareVector | 一个课件对应一个向量 |
| Student | 1:N | ChatHistory | 一个学生的对话历史 |
| Student | 1:N | LearningProgress | 一个学生的学习进度 |
| Student | 1:N | LearningAnalytics | 一个学生的学习分析 |
| Student | 1:N | Quiz | 一个学生的测验记录 |
| Quiz | 1:N | Question | 一个测验包含多道题目 |

---

## 四、索引设计

### 4.1 主键索引

所有表的主键 `id` 自动创建唯一索引。

### 4.2 外键索引

| 表名 | 外键字段 | 索引类型 | 说明 |
|------|----------|----------|------|
| courses | teacher_id | INDEX | 加速教师查询 |
| courseware | course_id | INDEX | 加速课程课件查询 |
| courseware_vectors | courseware_id | UNIQUE | 一对一关系 |
| chat_history | student_id | INDEX | 加速学生对话查询 |
| chat_history | course_id | INDEX | 加速课程对话查询 |
| learning_progress | student_id | INDEX | 加速学生进度查询 |
| learning_progress | course_id | INDEX | 加速课程进度查询 |
| learning_analytics | student_id | INDEX | 加速学生分析查询 |
| learning_analytics | course_id | INDEX | 加速课程分析查询 |
| quizzes | course_id | INDEX | 加速课程测验查询 |
| quizzes | student_id | INDEX | 加速学生测验查询 |
| questions | quiz_id | INDEX | 加速测验题目查询 |

### 4.3 复合索引

| 表名 | 复合字段 | 类型 | 说明 |
|------|----------|------|------|
| learning_progress | (student_id, course_id) | UNIQUE | 防止重复进度记录 |
| chat_history | (student_id, course_id) | INDEX | 加速学生课程对话查询 |

---

## 五、使用示例

### 5.1 模型导入

```python
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
```

### 5.2 创建教师和课程

```python
# 创建教师
teacher = await Teacher.create(name="张三")

# 创建课程
course = await Course.create(
    name="人工智能导论",
    teacher=teacher
)

# 创建课件
courseware = await Courseware.create(
    title="第一章：AI基础",
    file_type="pdf",
    course=course
)
```

### 5.3 创建学生和学习进度

```python
# 创建学生
student = await Student.create(name="李四")

# 创建学习进度
progress = await LearningProgress.create(
    student=student,
    course=course,
    progress=50,
    is_completed=False,
    started_at=datetime.now()
)
```

### 5.4 问答对话记录

```python
# 记录对话
chat = await ChatHistory.create(
    student=student,
    course=course,
    question="什么是机器学习？",
    answer="机器学习是人工智能的一个分支..."
)

# 查询学生对话历史
history = await ChatHistory.filter(student=student).order_by("-timestamp")
```

### 5.5 测验和题目

```python
# 创建测验
quiz = await Quiz.create(
    course=course,
    student=student,
    questions=[{"id": 1, "content": "问题1"}, {"id": 2, "content": "问题2"}],
    answers=[{"id": 1, "answer": "答案1"}, {"id": 2, "answer": "答案2"}]
)

# 添加题目
question1 = await Question.create(
    quiz=quiz,
    content="什么是深度学习？",
    answer="深度学习是机器学习的子领域..."
)

# 提交答案
await question1.update_from_dict({
    "student_answer": "深度学习是...",
    "is_correct": True,
    "submitted_at": datetime.now()
})
```

### 5.6 学习分析

```python
# 创建学习分析
analytics = await LearningAnalytics.create(
    student=student,
    course=course,
    status_data={
        "avg_score": 85.5,
        "quiz_count": 10,
        "learning_style": "综合",
        "weak_points": ["算法优化"]
    }
)
```

### 5.7 课件向量

```python
# 创建课件向量
vector = await CoursewareVector.create(
    courseware=courseware,
    embedding="[-0.123, 0.456, -0.789, ...]"
)

# 查询课件及其向量
result = await CoursewareVector.filter(id=vector.id).prefetch_related("courseware")
```

---

## 六、注意事项

### 6.1 字段约束

| 表名 | 字段 | 最大长度 | 说明 |
|------|------|----------|------|
| teachers | name | 100 | 教师姓名 |
| students | name | 100 | 学生姓名 |
| courses | name | 255 | 课程名称 |
| courseware | title | 255 | 课件标题 |
| courseware | file_type | 20 | 文件类型 |
| courseware_vectors | embedding | TEXT | 向量数据 |

### 6.2 级联删除

| 父表 | 删除行为 | 说明 |
|------|----------|------|
| teachers | CASCADE | 删除教师时级联删除其课程 |
| courses | CASCADE | 删除课程时级联删除课件、对话等 |
| quizzes | CASCADE | 删除测验时级联删除题目 |

### 6.3 JSON字段使用

以下字段存储为JSON格式：

- `courseware.parse_result` - 课件解析结果
- `courseware_vectors.embedding` - 向量数据(JSON字符串)
- `learning_analytics.status_data` - 学习状况快照
- `quizzes.questions` - 题目列表
- `quizzes.answers` - 答案列表

---

## 七、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0.0 | 2026-04-06 | 初始版本 |
| v1.1.0 | 2026-04-06 | 数据结构重构，采用 Course-Courseware 两级结构 |
| v1.3.0 | 2026-04-18 | 完善文档说明 |

---

*文档生成时间: 2026-04-18*
