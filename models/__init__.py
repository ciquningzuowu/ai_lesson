"""models 模块

统一管理所有数据模型：
- 数据库模型 (Tortoise ORM)：使用 models.database_models
- Pydantic 模型 (API Schema)：用于请求/响应数据结构
"""

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

from models.assessment import (
    QuestionType,
    StudentAnswer,
    AnalysisRequest,
    AnalysisResponse,
    GenerateQuizRequest,
    GenerateQuizResponse,
    QuizRecord,
    AnswerItem,
    SubmitQuizRequest,
    SubmitQuizResponse,
    QuizHistoryItem,
    QuestionRecord,
)

from models.content_processing import (
    ContentType,
    TaskStatus,
    ParseContentRequest,
    ParseContentResponse,
    KeyPointsData,
    SectionScript,
    GenerateScriptRequest,
    GenerateScriptResponse,
    UpdateScriptRequest,
    UpdateScriptResponse,
    TaskProgress as ModelTaskProgress,
    CoursewareContent,
    ParseTextContentRequest,
    AnalysisImage,
    ParseTextContentResponse,
)

from models.learning_adaptation import (
    RhythmSignal,
    AdjustRhythmRequest,
    AdjustRhythmResponse,
    StudentProfile,
    CourseProgress,
    InteractionHistory,
    LearningAnalyticsData,
    StudentStatusResponse,
    QuizHistoryResponse,
    QAHistoryResponse,
)

from models.qa_interaction import (
    StreamAnswerRequest,
    StreamAnswerResponse,
    ConversationTurn,
    QAContext,
    ConversationHistoryItem,
    QAHistoryItem,
    StreamChunk,
)

from models.rag import (
    TextChunk,
    TextSplitter,
    VectorStore,
    RAGService,
    get_rag_service,
)

__all__ = [
    # ========== 数据库模型 (Database Models) ==========
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
    # ========== 评估测验模型 (Assessment Models) ==========
    "QuestionType",
    "StudentAnswer",
    "AnalysisRequest",
    "AnalysisResponse",
    "GenerateQuizRequest",
    "GenerateQuizResponse",
    "QuizRecord",
    "AnswerItem",
    "SubmitQuizRequest",
    "SubmitQuizResponse",
    "QuizHistoryItem",
    "QuestionRecord",
    # ========== 内容处理模型 (Content Processing Models) ==========
    "ContentType",
    "TaskStatus",
    "ParseContentRequest",
    "ParseContentResponse",
    "KeyPointsData",
    "SectionScript",
    "GenerateScriptRequest",
    "GenerateScriptResponse",
    "UpdateScriptRequest",
    "UpdateScriptResponse",
    "ModelTaskProgress",
    "CoursewareContent",
    "ParseTextContentRequest",
    "AnalysisImage",
    "ParseTextContentResponse",
    # ========== 学习适应模型 (Learning Adaptation Models) ==========
    "RhythmSignal",
    "AdjustRhythmRequest",
    "AdjustRhythmResponse",
    "StudentProfile",
    "CourseProgress",
    "InteractionHistory",
    "LearningAnalyticsData",
    "StudentStatusResponse",
    "QuizHistoryResponse",
    "QAHistoryResponse",
    # ========== 问答交互模型 (QA Interaction Models) ==========
    "StreamAnswerRequest",
    "StreamAnswerResponse",
    "ConversationTurn",
    "QAContext",
    "ConversationHistoryItem",
    "QAHistoryItem",
    "StreamChunk",
    # ========== RAG 模型 ==========
    "TextChunk",
    "TextSplitter",
    "VectorStore",
    "RAGService",
    "get_rag_service",
]
