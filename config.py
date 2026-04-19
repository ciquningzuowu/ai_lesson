"""应用配置

配置管理：
- 所有 API 密钥和敏感信息预留空白，由开发者后续填入
- 使用环境变量或 .env 文件管理敏感配置
"""

import os
from typing import Optional


# ============= LLM 配置 =============
# 使用 LangChain init_chat_model(model=..., model_provider=...) 注册，与 OpenAI 兼容网关对接

LLM_CONFIG = {
    "model": "astron-code-latest",
    "model_provider": "openai",
    "CHAT_API_KEY": os.getenv("CHAT_API_KEY"),  # API 密钥 - 请填入或依赖环境变量
    "base_url": os.getenv("LLM_BASE_URL", "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"),
    "temperature": 0.7,
    "max_tokens": 2048,
    "top_p": 0.9,
    "top_k": 50,
    "frequency_penalty": 0.1,
    "presence_penalty": 0.1,
    "request_timeout": 90.0,
    "timeout": 45,
    "max_retries": 3,
}


# ============= 向量嵌入配置 =============

EMBEDDING_CONFIG = {
    "model_name": os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),  # 嵌入模型
    "api_key": os.getenv("EMBEDDING_API_KEY"),  # API 密钥
    # 嵌入 API 端点 - 优先使用 EMBEDDING_BASE_URL，否则从 LLM_BASE_URL 推断
    "base_url": os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
    #"dimension": 1536,  # 向量维度（根据实际模型调整）
}


# ============= 数据库配置 =============

def get_db_config():
    """获取数据库配置，支持 SQLite 和 MySQL 切换"""
    use_sqlite = os.getenv("USE_SQLITE", "false").lower() == "true"
    
    if use_sqlite:
        return {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {
                        "file_path": os.getenv("SQLITE_DB_PATH", "ai_lesson.db"),
                    },
                }
            },
            "apps": {
                "main": {
                    "models": ["models.database_models"],
                    "default_connection": "default",
                }
            },
            "use_tz": False,
            "timezone": "Asia/Shanghai",
        }
    
    return {
        "connections": {
            "default": {
                "engine": "tortoise.backends.mysql",
                "credentials": {
                    "host": os.getenv("MYSQL_HOST", "123.57.92.145"),
                    "port": int(os.getenv("MYSQL_PORT", "3306")),
                    "user": os.getenv("MYSQL_USER", "root"),
                    "password": "lylg@2026",# os.getenv("MYSQL_PASSWORD"),
                    "database":"course_elf" #os.getenv("MYSQL_DATABASE", "ai_lesson_system"),
                },
            }
        },
        "apps": {
            "main": {
                "models": ["models.database_models"],
                "default_connection": "default",
            }
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    }


DB_CONFIG = get_db_config()


# ============= Redis 配置 =============

REDIS_CONFIG = {
    # host 与 port 分离；云端 Redis 请在环境变量中配置，勿把端口拼进 host
    "host": os.getenv("REDIS_HOST", "redis-19816.c256.us-east-1-2.ec2.cloud.redislabs.com"),
    "port": int(os.getenv("REDIS_PORT", "19816")),
    "db": int(os.getenv("REDIS_DB", "0")),
    "password": os.getenv("REDIS_PASSWORD") or None,
    "encoding": "utf-8",
}


# ============= RAG 配置 =============

RAG_CONFIG = {
    "chunk_size": 500,  # 文本块大小
    "chunk_overlap": 50,  # 块重叠大小
    "top_k": 5,  # 检索返回数量
    "score_threshold": 0.7,  # 相似度阈值
}


# ============= 应用配置 =============

APP_CONFIG = {
    "app_name": "AI智能交互课件系统",
    "version": "1.0.0",
    "debug": os.getenv("DEBUG", "false").lower() == "true",
    # CORS 允许的域名 - 生产环境应明确指定，不使用通配符
    "cors_origins": os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(","),
}


# ============= 环境变量加载 =============

def load_env():
    """加载环境变量

    支持从 .env 文件加载配置（需要 python-dotenv）
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # 如果没有 python-dotenv，忽略


# 初始化时自动加载环境变量
load_env()
