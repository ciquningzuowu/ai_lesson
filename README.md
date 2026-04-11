# AI 智能交互课件系统

智能化的交互式课件学习系统，提供课件解析、讲解脚本生成、问答交互、学习适应等功能。

## 功能特性

- **课件解析** (`/agent/v1/parse-content`)
  - 支持 PDF、PPT、TXT 等格式
  - 自动提炼重点内容
  - 任务进度追踪

- **讲解脚本生成** (`/agent/v1/generate-script`)
  - 基于课件内容生成专业讲解脚本
  - 支持自定义开场白和讲解风格
  - 自动生成课件向量

- **脚本更新** (`/agent/v1/update-script`)
  - 增量更新讲解内容
  - 自动衔接原有脚本

- **问答交互** (`/agent/v1/stream-answer`)
  - 结合课程上下文生成回答
  - 支持流式输出
  - RAG 检索增强

- **学习适应** (`/agent/v1/adjust-rhythm`)
  - 智能分析学习状态
  - 调整讲解节奏
  - 生成补充脚本

- **评估测验** (`/agent/v1/generate-quiz`, `/agent/v1/analysis_answers`)
  - 自动生成测验题目
  - 答案智能分析

## 技术栈

- **框架**: FastAPI + Uvicorn
- **数据库**: Tortoise ORM + SQLite
- **缓存**: Redis
- **LLM**: LangChain + OpenAI 兼容 API
- **向量**: 自定义嵌入服务

## 项目结构

```
.
├── api/                      # API 路由
│   ├── adaptation_routes.py  # 学习适应路由
│   ├── assessment_routes.py  # 评估测验路由
│   ├── content_routes.py     # 内容处理路由
│   └── qa_routes.py          # 问答交互路由
├── core/                     # 核心业务逻辑
│   ├── assessment/          # 评估模块
│   │   ├── analysis_response.py  # 答案分析
│   │   └── generate-quiz.py      # 测验生成
│   ├── content_processing/  # 内容处理模块
│   │   ├── generate-script.py     # 脚本生成
│   │   ├── parse-content.py       # 课件解析
│   │   └── update-script.py       # 脚本更新
│   ├── learning_adaptation/ # 学习适应模块
│   │   └── adjust-rhythm.py       # 节奏调整
│   └── qa_interaction/       # 问答模块
│       └── stream-answer.py  # 流式回答
├── models/                   # 数据模型
│   ├── assessment.py
│   ├── content_processing.py
│   ├── learning_adaptation.py
│   └── qa_interaction.py
├── utils/                    # 工具模块
│   ├── database.py          # 数据库工具
│   ├── embeddings.py        # 嵌入服务
│   ├── helpers.py           # 辅助工具
│   ├── llm_client.py        # LLM 客户端
│   └── rag.py               # RAG 服务
├── config.py                # 配置文件
├── main.py                  # 主入口
└── requirements.txt         # 依赖列表
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# LLM 配置
OPENAI_API_KEY=your_api_key_here
LLM_BASE_URL=https://your-llm-api-url/v2

# Redis 配置（可选）
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3. 运行服务

```bash
python main.py
```

或使用 Uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问 API 文档

打开浏览器访问: http://localhost:8000/docs

## API 文档

### 内容处理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/agent/v1/parse-content` | POST | 解析课件内容 |
| `/agent/v1/generate-script` | POST | 生成讲解脚本 |
| `/agent/v1/update-script` | PUT | 更新讲解脚本 |

### 问答交互

| 接口 | 方法 | 描述 |
|------|------|------|
| `/agent/v1/stream-answer` | POST | 回答问题 |
| `/agent/v1/conversation-history/{student_id}` | GET | 获取对话历史 |

### 学习适应

| 接口 | 方法 | 描述 |
|------|------|------|
| `/agent/v1/adjust-rhythm` | POST | 调整学习节奏 |
| `/agent/v1/student-status/{student_id}` | GET | 获取学生状态 |

### 评估测验

| 接口 | 方法 | 描述 |
|------|------|------|
| `/agent/v1/analysis_answers` | GET | 分析答案 |
| `/agent/v1/generate-quiz` | POST | 生成测验 |
| `/agent/v1/submit-quiz` | POST | 提交测验 |

## 开发说明

### 配置修改

所有敏感配置（API 密钥等）通过 `config.py` 统一管理，预留空白由开发者填入。

### 提示词管理

各模块的提示词定义在对应的 `core/*/` 文件中，采用过渡版本，后续可由开发者进一步优化。

### 异步实现

系统全面采用异步架构（`async/await`），所有 I/O 操作均为异步实现。

## License

MIT
