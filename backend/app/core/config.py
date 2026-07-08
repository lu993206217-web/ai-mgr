"""
配置管理模块

使用 pydantic-settings 从环境变量和 .env 文件加载配置。
"""
from typing import Any, Dict, List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, model_validator


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    # 应用配置
    APP_NAME: str = "AI项目推进控制塔"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"
    
    # 安全配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 数据库配置
    DB_TYPE: str = "sqlite"  # sqlite 或 postgres
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ai_control_tower"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "your_password"

    @property
    def DATABASE_URL(self) -> str:
        """构建数据库连接 URL"""
        if self.DB_TYPE == "postgres":
            return (
                f"postgresql+psycopg2://"
                f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}"
                f"/{self.POSTGRES_DB}"
            )
        # SQLite 本地开发
        import os
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        os.makedirs(db_dir, exist_ok=True)
        return f"sqlite:///{os.path.join(db_dir, 'app.db')}"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """构建异步数据库连接 URL（本地开发使用同步引擎）"""
        return self.DATABASE_URL

    # CORS 配置
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    def get_cors_origins(self) -> List[str]:
        """获取 CORS 允许的源列表"""
        return self.ALLOWED_ORIGINS
    
    # DeepSeek 配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_MAX_TOKENS: int = 4096
    DEEPSEEK_TEMPERATURE: float = 0.1
    DEEPSEEK_TIMEOUT: int = 30
    
    # 钉钉集成配置
    DINGTALK_APP_KEY: Optional[str] = None
    DINGTALK_APP_SECRET: Optional[str] = None
    DINGTALK_AGENT_ID: Optional[str] = None
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # 文件上传配置
    UPLOAD_DIR: str = "/opt/ai-control-tower/uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    
    # 预警通知配置
    ENABLE_WARNING_NOTIFICATION: bool = True
    WARNING_CHECK_HOUR: int = 9


# 全局配置实例
settings = Settings()
