"""API 模块

统一导出各路由模块
"""

from api import content_routes
from api import qa_routes
from api import adaptation_routes
from api import assessment_routes

__all__ = ["content_routes", "qa_routes", "adaptation_routes", "assessment_routes"]
