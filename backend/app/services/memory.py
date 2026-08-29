"""Redis 记忆服务：QA 会话历史 + 会话索引 + 面试事件流（7 天 TTL）

图内状态由 SqliteSaver（面试图，同步）/ AsyncSqliteSaver（问答图，异步）
持久化到 SQLite 文件；Redis 只存会话历史与面试事件，
解决切页面/重启丢对话的问题。
"""

import json
import time

import redis

from app.config import config

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            decode_responses=True,
        )
    return _redis


def _key(prefix: str, session_id: str) -> str:
    return f"agent_job_coach:{prefix}:{session_id}"


def save_history(session_id: str, messages: list[dict]) -> None:
    """QA 会话历史（覆盖写 + TTL + 会话索引 touch）"""
    key = _key("history", session_id)
    r = get_redis()
    r.delete(key)
    if messages:
        r.rpush(key, *[json.dumps(m, ensure_ascii=False) for m in messages])
        r.expire(key, config.history_ttl_seconds)
    touch_session(session_id)


def get_history(session_id: str) -> list[dict]:
    try:
        items = get_redis().lrange(_key("history", session_id), 0, -1)
        return [json.loads(i) for i in items]
    except Exception:
        return []


def touch_session(session_id: str) -> None:
    """会话索引（Redis sorted set）：member=session_id，score=最后活动时间戳"""
    try:
        r = get_redis()
        r.zadd("agent_job_coach:sessions", {session_id: time.time()})
        r.expire("agent_job_coach:sessions", config.history_ttl_seconds)
    except Exception:
        pass


def list_sessions(limit: int = 50) -> list[dict]:
    """会话列表（按最后活动倒序）：session_id + 消息数 + 首条摘要 + 最后活动时间"""
    try:
        r = get_redis()
        pairs = r.zrevrange("agent_job_coach:sessions", 0, limit - 1, withscores=True)
    except Exception:
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
    r = get_redis()
    r.delete(_key("history", session_id))
    r.delete(_key("interview", session_id))
    r.zrem("agent_job_coach:sessions", session_id)


def append_interview_event(session_id: str, event: dict) -> None:
    """面试事件流：每题 {round, question, answer, score, feedback}"""
    key = _key("interview", session_id)
    r = get_redis()
    r.rpush(key, json.dumps(event, ensure_ascii=False))
    r.expire(key, config.history_ttl_seconds)


def get_interview_events(session_id: str) -> list[dict]:
    try:
        items = get_redis().lrange(_key("interview", session_id), 0, -1)
        return [json.loads(i) for i in items]
    except Exception:
        return []


def clear_session(session_id: str) -> None:
    r = get_redis()
    r.delete(_key("history", session_id))
    r.delete(_key("interview", session_id))
