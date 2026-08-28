"""SQLAlchemy 数据库（MySQL），启动时自动建库建表"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import config


class Base(DeclarativeBase):
    pass


def _ensure_database() -> None:
    """连接 MySQL 服务器，若目标库不存在则创建"""
    server_url = config.mysql_url.rsplit("/", 1)[0]
    engine = create_engine(server_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(
            text(f"CREATE DATABASE IF NOT EXISTS `{config.mysql_db}` "
                 "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        )
        conn.commit()
    engine.dispose()


_ensure_database()
engine = create_engine(config.mysql_url, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """建表（幂等）"""
    from app import models  # noqa: F401  确保模型注册
    Base.metadata.create_all(bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
