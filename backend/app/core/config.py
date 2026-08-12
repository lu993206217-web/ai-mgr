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
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_PASSWORD: str = "admin123"
    
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
    DEEPSEEK_VERIFY_SSL: bool = True
    DAILY_REPORT_AI_ENABLED: bool = True
    DAILY_REPORT_AI_AUTO_MATCH_SCORE: float = 0.92
    EMAIL_AI_ENABLED: bool = True
    EMAIL_AI_AUTO_MATCH_SCORE: float = 0.92
    
    # 钉钉集成配置
    DINGTALK_APP_KEY: Optional[str] = None
    DINGTALK_APP_SECRET: Optional[str] = None
    DINGTALK_AGENT_ID: Optional[str] = None

    # 项目活动日报同步配置
    DAILY_REPORT_SYNC_ENABLED: bool = True
    DAILY_REPORT_SYNC_HOUR: int = 9
    DAILY_REPORT_SYNC_MINUTE: int = 45
    DAILY_REPORT_SYNC_LOOKBACK_DAYS: int = 3
    DAILY_REPORT_SYNC_AUTO_MATCH_SCORE: float = 0.86
    DAILY_REPORT_API_BASE_URL: str = "https://192.168.1.180"
    DAILY_REPORT_API_KEY: Optional[str] = None
    DAILY_REPORT_API_KEY_HEADER: str = "X-NB-API-Key"
    DAILY_REPORT_API_VERIFY_SSL: bool = False
    DAILY_REPORT_API_ALLOW_HTTP_FALLBACK: bool = True
    DAILY_REPORT_API_TIMEOUT: int = 30

    # Gmail 邮件情报接入（只使用 OAuth，不保存邮箱密码）
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REDIRECT_URI: str = "http://127.0.0.1:8001/api/v1/email-intelligence/oauth/callback"
    GMAIL_ACCOUNT_EMAIL: Optional[str] = None
    GMAIL_SYNC_ENABLED: bool = False

    # 钉钉企业邮箱（阿里企业邮）IMAP / SMTP 接入
    DINGTALK_MAIL_ENABLED: bool = False
    DINGTALK_MAIL_ACCOUNT_EMAIL: Optional[str] = None
    DINGTALK_MAIL_PASSWORD: Optional[str] = None
    DINGTALK_MAIL_IMAP_HOST: str = "imap.qiye.aliyun.com"
    DINGTALK_MAIL_IMAP_PORT: int = 993
    DINGTALK_MAIL_IMAP_SSL: bool = True
    DINGTALK_MAIL_SMTP_HOST: str = "smtp.qiye.aliyun.com"
    DINGTALK_MAIL_SMTP_PORT: int = 465
    DINGTALK_MAIL_SMTP_SSL: bool = True
    DINGTALK_MAIL_FOLDER: str = "INBOX"
    DINGTALK_MAIL_SENT_FOLDER: Optional[str] = None
    DINGTALK_MAIL_TIMEOUT: int = 30
    DINGTALK_MAIL_SYNC_LIMIT: int = 50
    DINGTALK_MAIL_SYNC_INTERVAL_MINUTES: int = 5
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # 文件上传配置
    UPLOAD_DIR: str = "/opt/ai-control-tower/uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    
    # 预警通知配置
    ENABLE_WARNING_NOTIFICATION: bool = True
    WARNING_CHECK_HOUR: int = 9
    WARNING_CHECK_MINUTE: int = 55
    INTELLIGENCE_SNAPSHOT_HOUR: int = 10
    INTELLIGENCE_SNAPSHOT_MINUTE: int = 0


# 全局配置实例
settings = Settings()
