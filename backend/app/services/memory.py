"""Redis 记忆服务：QA 会话历史 + 面试事件流（7 天 TTL）

参考仓维云：MemorySaver 存图内状态，Redis 持久化会话历史，
解决切页面/重启丢对话的问题。
"""

import json

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
    """QA 会话历史（覆盖写 + TTL）"""
    key = _key("history", session_id)
    r = get_redis()
    r.delete(key)
    if messages:
        r.rpush(key, *[json.dumps(m, ensure_ascii=False) for m in messages])
        r.expire(key, config.history_ttl_seconds)


def get_history(session_id: str) -> list[dict]:
    try:
        items = get_redis().lrange(_key("history", session_id), 0, -1)
        return [json.loads(i) for i in items]
    except Exception:
        return []


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
