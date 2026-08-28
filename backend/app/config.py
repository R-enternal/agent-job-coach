"""全局配置：从 .env 读取，API Key 兜底读环境变量（参考仓维云 config.py）"""

import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用
    app_name: str = "Agent Job Coach（Agent 求职助手）"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 9902

    # 智谱 GLM 对话模型（OpenAI 兼容；实测带推理链，max_tokens 需调大）
    llm_api_key: str = os.environ.get("ZHIPU_API_KEY", "")
    llm_base_url: str = os.environ.get("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
    llm_model: str = os.environ.get("GLM_MODEL", "glm-5.1")
    llm_max_tokens: int = 4096

    # 智谱 embedding（OpenAI 兼容）
    embedding_api_key: str = os.environ.get("ZHIPU_API_KEY", "")
    embedding_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    embedding_model: str = "embedding-2"

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = os.environ.get("MYSQL_PASSWORD", "060311")
    mysql_db: str = "agent_job_coach"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    history_ttl_seconds: int = 7 * 24 * 3600

    # 知识库
    kb_data_dir: str = "../data"          # 知识库源文件目录（项目根 data/）
    kb_vector_dir: str = "./vector_db"    # Chroma 持久化目录
    kb_top_k: int = 4
    kb_chunk_size: int = 500
    kb_chunk_overlap: int = 50

    # Agent
    agent_max_steps: int = 6
    interview_max_rounds: int = 5

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )

    @property
    def kb_data_path(self) -> Path:
        return Path(self.kb_data_dir).resolve()

    @field_validator("llm_api_key", "embedding_api_key", mode="before")
    @classmethod
    def _fallback_env(cls, v: str, info) -> str:
        """.env 中留空时回退读系统环境变量（ZHIPU_API_KEY）"""
        if v:
            return v
        env_name = "ZHIPU_API_KEY"
        return os.environ.get(env_name, "")


config = Settings()
