"""Redis 记忆服务：QA 会话历史 + 会话索引 + 面试事件流（7 天 TTL）

图内状态由 SqliteSaver（面试图，同步）/ AsyncSqliteSaver（问答图，异步）
持久化到 SQLite 文件；Redis 只存会话历史与面试事件，
解决切页面/重启丢对话的问题。

降级策略：Redis 仅作缓存/事件流，全部操作 best-effort——
读写失败只记日志、不抛异常，主流程（图状态 / MySQL 持久化）不受影响。
"""

import json
import logging
import time

import redis

from app.config import config

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,  # Redis 挂掉时快速失败，不吊死请求
        )
    return _redis


def _key(prefix: str, session_id: str) -> str:
    return f"agent_job_coach:{prefix}:{session_id}"


def save_history(session_id: str, messages: list[dict]) -> None:
    """QA 会话历史（覆盖写 + TTL + 会话索引 touch）"""
    try:
        key = _key("history", session_id)
        r = get_redis()
        r.delete(key)
        if messages:
            r.rpush(key, *[json.dumps(m, ensure_ascii=False) for m in messages])
            r.expire(key, config.history_ttl_seconds)
        touch_session(session_id)
    except Exception:
        logger.warning("save_history 失败（Redis 不可用？），session=%s", session_id, exc_info=True)


def get_history(session_id: str) -> list[dict]:
    try:
        items = get_redis().lrange(_key("history", session_id), 0, -1)
        return [json.loads(i) for i in items]
    except Exception:
        logger.warning("get_history 失败，session=%s", session_id, exc_info=True)
        return []


def touch_session(session_id: str) -> None:
    """会话索引（Redis sorted set）：member=session_id，score=最后活动时间戳"""
    try:
        r = get_redis()
        r.zadd("agent_job_coach:sessions", {session_id: time.time()})
        r.expire("agent_job_coach:sessions", config.history_ttl_seconds)
    except Exception:
        logger.warning("touch_session 失败，session=%s", session_id, exc_info=True)


def list_sessions(limit: int = 50) -> list[dict]:
    """会话列表（按最后活动倒序）：session_id + 消息数 + 首条摘要 + 最后活动时间"""
    try:
        r = get_redis()
        pairs = r.zrevrange("agent_job_coach:sessions", 0, limit - 1, withscores=True)
    except Exception:
        logger.warning("list_sessions 失败", exc_info=True)
        return []
    items: list[dict] = []
    for sid, score in pairs:
        msgs = get_history(sid)
        if not msgs:
            continue
        first_content = ""
        for m in msgs:
            if m.get("role") == "user" and m.get("content"):
                first_content = str(m["content"])[:40]
                break
        items.append({
            "session_id": sid,
            "message_count": len(msgs),
            "preview": first_content or "（空会话）",
            "updated_at": int(score),
        })
    return items


def remove_session(session_id: str) -> None:
    """删除会话：Redis 历史/事件 + 会话索引（SQLite checkpoint 由调用方清理）"""
    try:
        r = get_redis()
        r.delete(_key("history", session_id))
        r.delete(_key("interview", session_id))
        r.zrem("agent_job_coach:sessions", session_id)
    except Exception:
        logger.warning("remove_session 失败，session=%s", session_id, exc_info=True)


def append_interview_event(session_id: str, event: dict) -> None:
    """面试事件流：每题 {round, question, answer, score, feedback}"""
    try:
        key = _key("interview", session_id)
        r = get_redis()
        r.rpush(key, json.dumps(event, ensure_ascii=False))
        r.expire(key, config.history_ttl_seconds)
    except Exception:
        logger.warning("append_interview_event 失败，session=%s", session_id, exc_info=True)


def get_interview_events(session_id: str) -> list[dict]:
    try:
        items = get_redis().lrange(_key("interview", session_id), 0, -1)
        return [json.loads(i) for i in items]
    except Exception:
        logger.warning("get_interview_events 失败，session=%s", session_id, exc_info=True)
        return []


def clear_session(session_id: str) -> None:
    try:
        r = get_redis()
        r.delete(_key("history", session_id))
        r.delete(_key("interview", session_id))
    except Exception:
        logger.warning("clear_session 失败，session=%s", session_id, exc_info=True)
