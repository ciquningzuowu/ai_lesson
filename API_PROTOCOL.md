# AI智能交互课件系统 - 前后端对接协议

> **版本**: v1.1.0
> **更新日期**: 2026-04-06
> **服务地址**: `http://{host}:{port}`

---

## 一、系统概述

这是一个基于 **FastAPI** 构建的 AI 智能交互课件系统后端服务，提供课件解析、脚本生成、问答交互、学习适应和评估测验等核心功能。

### 1.1 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| Web框架 | FastAPI + Uvicorn | 高性能异步 API 框架 |
| 数据库 | Tortoise ORM | 支持 MySQL/SQLite 的异步 ORM |
| 缓存层 | Redis | 任务进度追踪、会话缓存 |
| AI 模型 | LangChain | 对接讯飞/硅基流动等 LLM 服务 |
| 向量检索 | RAG 服务 | 基于向量相似度的内容检索增强 |

### 1.2 数据模型体系

系统采用 **课程-课件** 两级结构：

```
Teacher (教师)
    └── Course (课程)
            └── Courseware (课件)
                    └── CoursewareVector (课件向量)
```

### 1.3 API 前缀规范

- **业务 API**: 所有接口均以 `/agent/v1` 开头
- **系统 API**: `/health`（健康检查）、`/api/v1/status`（状态查询）

### 1.4 统一响应格式

所有接口均返回以下统一 JSON 格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

---

## 二、API 端点总览

### 2.1 内容处理模块

| 端点 | 方法 | 功能 | 流式支持 |
|------|------|------|----------|
| `/agent/v1/parse-content` | POST | 解析课件文件（上传方式） | ❌ |
| `/agent/v1/parse-content/text` | POST | 解析文本内容（JSON 方式） | ❌ |
| `/agent/v1/generate-script` | POST | 生成讲解脚本 | ❌ |
| `/agent/v1/generate-script/stream` | POST | 流式生成讲解脚本 | ✅ |
| `/agent/v1/update-script` | PUT | 更新讲解脚本 | ❌ |

### 2.2 问答交互模块

| 端点 | 方法 | 功能 | 流式支持 |
|------|------|------|----------|
| `/agent/v1/stream-answer` | POST | 回答学生问题 | ❌ |
| `/agent/v1/stream-answer/stream` | POST | 流式回答学生问题 | ✅ |
| `/agent/v1/conversation-history/{student_id}` | GET | 获取对话历史 | ❌ |

### 2.3 学习适应模块

| 端点 | 方法 | 功能 |
|------|------|------|
| `/agent/v1/adjust-rhythm` | POST | 调整学习节奏 |
| `/agent/v1/student-status/{student_id}` | GET | 获取学生学习状态 |
| `/agent/v1/quiz-history/{student_id}` | GET | 获取答题历史 |
| `/agent/v1/qa-history/{student_id}` | GET | 获取问答历史 |

### 2.4 评估测验模块

| 端点 | 方法 | 功能 |
|------|------|------|
| `/agent/v1/analysis_answers` | GET | 分析学生答案 |
| `/agent/v1/generate-quiz` | POST | 生成测验题目 |
| `/agent/v1/quiz-record/{quiz_id}` | GET | 获取测验记录 |
| `/agent/v1/submit-quiz` | POST | 提交测验答案 |

---

## 三、详细接口规范

### 3.1 内容处理模块

#### 3.1.1 解析课件文件

> 上传课件文件并解析为结构化内容，支持 PDF 图片提取

```
POST /agent/v1/parse-content
Content-Type: multipart/form-data
```

**请求参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file | File | ✅ | - | 课件文件 |
| file_type | string | ✅ | - | 文件类型：`ppt` / `pdf` / `text` |
| task_id | string | ❌ | `default` | 任务ID，用于追踪进度 |
| extract_key_points | boolean | ❌ | `true` | 是否提炼重点 |
| course_id | int | ❌ | null | 关联的课程ID |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "analysis": {
      "title": "课件标题",
      "sections": [...],
      "key_points": [...],
      "images": [
        {"image_index": 1, "page_num": 1, "description": "图表..."}
      ]
    },
    "defeat_describe": null
  }
}
```

> **PDF 图片解析**：当 `file_type=pdf` 时，解析结果中会包含 `images` 字段，列出 PDF 中的所有图片信息。

---

#### 3.1.2 生成讲解脚本

```
POST /agent/v1/generate-script
Content-Type: application/json
```

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| courseware_ids | int[] | ✅ | 课件ID列表 |
| task_id | string | ✅ | 任务ID |
| course_id | int | ❌ | 课程ID |
| start_prompt | string | ❌ | 自定义开场白 |
| style_prompt | string | ❌ | 讲解风格 |

**请求示例**：

```json
{
  "courseware_ids": [1, 2, 3],
  "task_id": "task_001",
  "course_id": 1,
  "start_prompt": "欢迎来到今天的课程",
  "style_prompt": "生动有趣、深入浅出"
}
```

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "explain": [
      {
        "section_id": 1,
        "script": "各位同学好，今天我们来学习..."
      }
    ],
    "courseware_vector": [0.123, -0.456, 0.789, ...]
  }
}
```

---

#### 3.1.3 流式生成讲解脚本

```
POST /agent/v1/generate-script/stream
Content-Type: application/json
Accept: text/event-stream
```

**响应格式**：SSE (Server-Sent Events)

```
data: {"chunk": "各位同学好，今天我们来学习..."}
data: {"chunk": "首先，让我们回顾一下..."}
data: [DONE]
```

---

#### 3.1.4 更新讲解脚本

```
PUT /agent/v1/update-script
Content-Type: application/json
```

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| courseware_id | int | ✅ | 要更新的课件ID |
| new_file_id | int | ✅ | 新增的课件文件ID |
| start_prompt | string | ❌ | 新的自定义开场白 |

---

### 3.2 问答交互模块

#### 3.2.1 回答学生问题

```
POST /agent/v1/stream-answer
Content-Type: application/json
```

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| student_id | int | ✅ | 学生ID |
| course_id | int | ✅ | 课程ID |
| courseware_id | int | ❌ | 课件ID（可选） |
| question | string | ✅ | 学生的问题 |

**请求示例**：

```json
{
  "student_id": 1001,
  "course_id": 1,
  "courseware_id": 5,
  "question": "这节课的主要内容是什么？"
}
```

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "answer": "这节课主要讲述了三个核心知识点..."
  }
}
```

---

#### 3.2.2 流式回答学生问题

```
POST /agent/v1/stream-answer/stream
Content-Type: application/json
Accept: text/event-stream
```

**响应格式**：SSE 流

```
data: {"content": "这"}
data: {"content": "节"}
data: [DONE]
```

---

#### 3.2.3 获取对话历史

```
GET /agent/v1/conversation-history/{student_id}
```

**路径参数**：`student_id` - 学生ID

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| course_id | int | null | 课程ID（可选） |
| limit | int | 10 | 返回记录数量 |

---

### 3.3 学习适应模块

#### 3.3.1 调整学习节奏

```
POST /agent/v1/adjust-rhythm
Content-Type: application/json
```

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| student_id | int | ✅ | 学生ID |
| course_id | int | ❌ | 课程ID（可选） |

**响应**：

| 字段 | 类型 | 说明 |
|------|------|------|
| rhythm_signal | string | `keep` / `up` / `supplement` |
| supplement_script | string | 补充讲解脚本（仅 signal=supplement 时有值） |

---

#### 3.3.2 获取学生学习状态

```
GET /agent/v1/student-status/{student_id}
```

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "student_id": 1001,
    "progress": 50,
    "lessons_completed": 5,
    "quizzes_completed": 3,
    "avg_score": 85.5,
    "learning_style": "综合"
  }
}
```

---

### 3.4 评估测验模块

#### 3.4.1 分析学生答案

```
GET /agent/v1/analysis_answers
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question_id | int | ✅ | 题目ID |
| course_id | int | ✅ | 课程ID |
| courseware_id | int | ❌ | 课件ID |
| student_id | int | ✅ | 学生ID |
| answer | string | ✅ | 学生的回答 |

---

#### 3.4.2 生成测验题目

```
POST /agent/v1/generate-quiz
Content-Type: application/json
```

**请求体**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| course_id | int | ✅ | - | 课程ID |
| courseware_id | int | ❌ | null | 课件ID |
| student_id | int | ✅ | - | 学生ID |
| num | int | ❌ | 5 | 题目数量（1-20） |
| type | string | ❌ | `qa` | `qa` / `fill_blank` |

**请求示例**：

```json
{
  "course_id": 1,
  "courseware_id": 5,
  "student_id": 1001,
  "num": 5,
  "type": "qa"
}
```

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "questions": ["问题1", "问题2", ...],
    "answers": ["答案1", "答案2", ...]
  }
}
```

---

#### 3.4.3 提交测验答案

```
POST /agent/v1/submit-quiz?quiz_id=1
Content-Type: application/json
```

**请求体**：

```json
{
  "answers": [
    {"question_id": 1, "answer": "学生答案1"},
    {"question_id": 2, "answer": "学生答案2"}
  ]
}
```

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "quiz_id": 1,
    "score": 80.0,
    "correct_count": 4,
    "total_count": 5
  }
}
```

---

## 四、数据模型

### 4.1 数据库表结构

#### teachers（教师表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| name | varchar(100) | 教师姓名 |
| create_time | datetime | 创建时间 |

#### students（学生表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| name | varchar(100) | 学生姓名 |
| create_time | datetime | 创建时间 |

#### courses（课程表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| name | varchar(255) | 课程名称 |
| teacher_id | int | 外键 -> teachers |
| create_time | datetime | 创建时间 |

#### courseware（课件表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| title | varchar(255) | 课件标题 |
| content | text | 课件原始内容 |
| parse_result | json | 课件解析结果 |
| file_type | varchar(20) | 文件类型 |
| course_id | int | 外键 -> courses |
| create_time | datetime | 创建时间 |

#### courseware_vectors（课件向量表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| courseware_id | int | 外键 -> courseware |
| embedding | vector(1536) | 嵌入向量数据（MySQL 原生 VECTOR 类型，1536 维） |
| create_time | datetime | 创建时间 |

#### chat_history（对话历史表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| student_id | int | 外键 -> students |
| course_id | int | 外键 -> courses |
| question | text | 学生问题 |
| answer | text | AI 回答 |
| timestamp | datetime | 对话时间 |

#### learning_progress（学习进度表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| student_id | int | 外键 -> students |
| course_id | int | 外键 -> courses |
| progress | int | 进度百分比（0-100） |
| is_completed | boolean | 是否完成 |
| started_at | datetime | 开始时间 |
| completed_at | datetime | 完成时间 |

#### learning_analytics（学习分析表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| student_id | int | 外键 -> students |
| course_id | int | 外键 -> courses |
| courseware_id | int | 外键 -> courseware（可选） |
| status_data | json | 学习状况快照 |
| update_time | datetime | 更新时间 |

#### quizzes（测验表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| course_id | int | 外键 -> courses |
| student_id | int | 外键 -> students |
| questions | json | 题目列表 |
| answers | json | 答案列表 |
| score | float | 得分 |
| create_time | datetime | 创建时间 |

#### questions（题目表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| quiz_id | int | 外键 -> quizzes |
| content | text | 题目内容 |
| answer | text | 正确答案 |
| student_answer | text | 学生答案 |
| is_correct | boolean | 是否正确 |
| submitted_at | datetime | 提交时间 |

---

## 五、表关系图

```
┌─────────────┐       ┌─────────────┐
│  teachers   │──────<│   courses   │
└─────────────┘       └──────┬──────┘
                             │
                             │
                             │
┌─────────────┐       ┌──────┴──────┐
│  students   │──────<│  courseware  │──────<│ courseware_vectors │
└──────┬──────┘       └─────────────┘       └──────────────────┘
       │
       │                ┌─────────────────┐
       │                │  chat_history   │
       ├───────────────<│                 │
       │                └─────────────────┘
       │
       │                ┌─────────────────────┐
       ├───────────────<│ learning_progress  │
       │                └─────────────────────┘
       │
       │                ┌─────────────────────┐
       ├───────────────<│  learning_analytics│
       │                └─────────────────────┘
       │
       │                ┌─────────────┐       ┌────────────┐
       └───────────────<│   quizzes   │──────<│ questions  │
                        └─────────────┘       └────────────┘
```

---

## 六、典型业务流程

### 6.1 课件学习完整流程

```
┌─────────┐
│ 前端    │
└────┬────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. 上传课件（解析）                                           │
│    POST /agent/v1/parse-content                              │
│    (支持 PDF 图片提取)                                         │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 生成讲解脚本                                                │
│    POST /agent/v1/generate-script                            │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 学生学习 - 问答                                             │
│    POST /agent/v1/stream-answer                              │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 调整学习节奏                                                │
│    POST /agent/v1/adjust-rhythm                              │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. 生成测验 & 提交                                             │
│    POST /agent/v1/generate-quiz                              │
│    POST /agent/v1/submit-quiz                                │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. 答案分析                                                   │
│    GET /agent/v1/analysis_answers                            │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 RAG 问答流程

```
用户问题
    │
    ▼
┌──────────────┐
│ 文本嵌入     │  (使用 Embedding 模型)
└──────────────┘
    │
    ▼
┌──────────────┐
│ 向量相似度   │  (在 VectorStore 中检索)
│ 搜索 Top-K   │
└──────────────┘
    │
    ▼
┌──────────────┐
│ 构建 RAG     │  (将检索结果注入 Prompt)
│ Prompt      │
└──────────────┘
    │
    ▼
┌──────────────┐
│ LLM 生成     │  (基于上下文生成回答)
│ 回答        │
└──────────────┘
    │
    ▼
返回回答给用户
```

---

## 七、错误处理

### 7.1 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

### 7.2 常见错误响应

```json
{
  "code": 404,
  "message": "测验不存在",
  "data": null
}
```

---

## 八、接口调用示例

### 8.1 Python 调用示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 生成讲解脚本
def generate_script(courseware_ids: list[int], course_id: int):
    response = requests.post(
        f"{BASE_URL}/agent/v1/generate-script",
        json={
            "courseware_ids": courseware_ids,
            "task_id": "task_001",
            "course_id": course_id,
            "style_prompt": "生动有趣"
        }
    )
    return response.json()

# 2. 提问
def ask_question(student_id: int, course_id: int, question: str, courseware_id: int = None):
    payload = {
        "student_id": student_id,
        "course_id": course_id,
        "question": question
    }
    if courseware_id:
        payload["courseware_id"] = courseware_id
    response = requests.post(f"{BASE_URL}/agent/v1/stream-answer", json=payload)
    return response.json()

# 3. 生成测验
def generate_quiz(course_id: int, student_id: int, courseware_id: int = None):
    payload = {
        "course_id": course_id,
        "student_id": student_id,
        "num": 5,
        "type": "qa"
    }
    if courseware_id:
        payload["courseware_id"] = courseware_id
    response = requests.post(f"{BASE_URL}/agent/v1/generate-quiz", json=payload)
    return response.json()

# 4. 提交测验
def submit_quiz(quiz_id: int, answers: list[dict]):
    response = requests.post(
        f"{BASE_URL}/agent/v1/submit-quiz?quiz_id={quiz_id}",
        json={"answers": answers}
    )
    return response.json()
```

### 8.2 JavaScript 调用示例

```javascript
const BASE_URL = 'http://localhost:8000';

// 生成讲解脚本
async function generateScript(coursewareIds, courseId) {
  const response = await fetch(`${BASE_URL}/agent/v1/generate-script`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      courseware_ids: coursewareIds,
      task_id: 'task_001',
      course_id: courseId,
      style_prompt: '生动有趣'
    })
  });
  return await response.json();
}

// 流式回答问题
async function* streamAnswer(studentId, courseId, question, coursewareId = null) {
  const payload = { student_id: studentId, course_id: courseId, question };
  if (coursewareId) payload.courseware_id = coursewareId;

  const response = await fetch(`${BASE_URL}/agent/v1/stream-answer/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    const data = chunk.replace('data: ', '').trim();
    if (data === '[DONE]') break;
    yield JSON.parse(data);
  }
}
```

---

## 九、API 安全与限制

### 9.1 输入参数校验

| 参数类型 | 校验规则 | 错误响应 |
|---------|---------|---------|
| student_id | 正整数 (>0) | code=400, "参数校验失败" |
| course_id | 正整数 (>0) | code=400, "参数校验失败" |
| courseware_id | 正整数 (>0) | code=400, "参数校验失败" |
| question | 最大 2000 字符 | code=400, "问题长度超限" |
| limit | 最大 100 | code=400, "limit 参数超限" |
| num | 1-20 范围 | code=400, "题目数量需在1-20之间" |

### 9.2 当前 API 限制

> ⚠️ **安全提示**：以下功能在当前版本中尚未实现权限验证，生产环境部署时请务必添加认证机制。

| 限制项 | 说明 | 建议 |
|--------|------|------|
| 权限验证 | 所有 API 端点暂无身份认证 | 部署前实现 JWT Token 认证 |
| 请求限流 | 暂无频率限制 | 使用 Redis 实现限流中间件 |
| CORS | 默认允许 localhost | 生产环境明确配置允许的域名 |

### 9.3 健康检查

```
GET /health
```

**响应**（成功）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "healthy",
    "database": "connected",
    "redis": "connected"
  }
}
```

**响应**（部分故障）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "degraded",
    "database": "connected",
    "redis": "disconnected"
  }
}
```

---

## 十、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0.0 | 2026-04-06 | 初始版本 |
| v1.1.0 | 2026-04-06 | 数据结构重构：新增 Teacher/Course/Courseware 两级结构，新增 courseware_vectors 表，新增 learning_analytics 表，lesson 相关字段改为 courseware，新增 PDF 图片解析功能 |
| v1.2.0 | 2026-04-07 | 新增 API 安全与限制说明章节，补充输入参数校验规则和 CORS 配置说明 |

---

*文档生成时间: 2026-04-07*
