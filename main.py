"""AI 智能交互课件系统

主入口文件
提供 FastAPI 应用初始化和路由注册
"""

import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import APP_CONFIG
from utils.database import init_db, close_db, ensure_db, get_redis_cache
from utils.helpers import ResponseFormatter
from utils.node_monitor import configure_application_logging, node_state

configure_application_logging()

# 路由模块
from api.content_routes import router as content_router
from api.qa_routes import router as qa_router
from api.adaptation_routes import router as adaptation_router
from api.assessment_routes import router as assessment_router


# 创建 FastAPI 应用
app = FastAPI(
    title=APP_CONFIG["app_name"],
    version=APP_CONFIG["version"],
    description="提供课件解析、脚本生成、问答交互、学习适应等核心功能",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=APP_CONFIG["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(content_router)
app.include_router(qa_router)
app.include_router(adaptation_router)
app.include_router(assessment_router)


# ============= 应用生命周期事件 =============

@app.on_event("startup")
async def startup_event():
    """应用启动事件 - 初始化数据库和 Redis"""
    node_state("app.main", "startup", phase="enter", message="应用启动中")

    # 初始化数据库
    node_state("app.main", "db_init", phase="checkpoint", message="初始化数据库")
    try:
        await init_db()
        node_state("app.main", "db_init", phase="exit", message="数据库就绪")
    except Exception as e:
        node_state("app.main", "db_init", phase="error", message=f"数据库初始化失败: {e}")
        raise

    # 初始化 Redis
    redis_cache = get_redis_cache()
    node_state("app.main", "redis_connect", phase="checkpoint", message="连接 Redis")
    try:
        await redis_cache.connect()
        node_state("app.main", "redis_connect", phase="exit", message="Redis 已连接")
    except Exception as e:
        node_state("app.main", "redis_connect", phase="error", message=f"Redis 不可用: {e}")

    node_state(
        "app.main",
        "ready",
        phase="checkpoint",
        message=f"{APP_CONFIG['app_name']} v{APP_CONFIG['version']} 启动完成",
    )


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件 - 释放资源"""
    node_state("app.main", "shutdown", phase="enter", message="应用关闭中")

    # 关闭数据库连接
    try:
        await close_db()
        node_state("app.main", "shutdown", phase="exit", message="资源已释放")
    except Exception as e:
        node_state("app.main", "shutdown", phase="error", message=f"关闭时出错: {e}")


# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    import logging
    logger = logging.getLogger("ai_lesson.api")
    logger.error(f"未处理的异常: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误，请稍后重试",
        },
    )


@app.get("/")
async def root():
    """根路径"""
    return ResponseFormatter.success_response({
        "name": APP_CONFIG["app_name"],
        "version": APP_CONFIG["version"],
        "status": "running",
    })


@app.get("/health")
async def health_check():
    """健康检查"""
    redis_healthy = False
    try:
        cache = get_redis_cache()
        await cache.connect()
        if cache._client:
            await cache._client.ping()
            redis_healthy = True
    except Exception:
        pass

    return ResponseFormatter.success_response({
        "status": "healthy",
        "database": "connected",
        "redis": "connected" if redis_healthy else "disconnected",
    })


@app.get("/api/v1/status")
async def api_status():
    """API 状态"""
    return ResponseFormatter.success_response({
        "api_version": "v1",
        "endpoints": {
            "content": "/agent/v1/parse-content, /agent/v1/generate-script, /agent/v1/update-script",
            "qa": "/agent/v1/stream-answer",
            "adaptation": "/agent/v1/adjust-rhythm",
            "assessment": "/agent/v1/analysis_answers, /agent/v1/generate-quiz",
        },
    })


# 运行入口
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "127.0.0.1")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=APP_CONFIG["debug"],
    )
