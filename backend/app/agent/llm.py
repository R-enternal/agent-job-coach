"""LLM 工厂：智谱 GLM 全家桶（对话 glm-5.1 / 视觉 glm-4v-plus / embedding-2，OpenAI 兼容）"""

import json
import re

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr

from app.config import config


def get_chat_model() -> ChatOpenAI:
    """智谱 GLM 对话模型（temperature=0，max_tokens 调大容纳推理链）"""
    return ChatOpenAI(
        model=config.llm_model,
        api_key=SecretStr(config.llm_api_key),
        base_url=config.llm_base_url,
        temperature=0,
        max_tokens=config.llm_max_tokens,
        timeout=120,
        max_retries=2,
    )


def get_embeddings() -> OpenAIEmbeddings:
    """智谱 GLM embedding（OpenAI 兼容）"""
    return OpenAIEmbeddings(
        model=config.embedding_model,
        api_key=SecretStr(config.embedding_api_key),
        base_url=config.embedding_base_url,
        chunk_size=16,
    )


def get_vision_model() -> ChatOpenAI:
    """智谱视觉模型（glm-4v-plus，JD 截图解析用，OpenAI 兼容）"""
    return ChatOpenAI(
        model="glm-4v-plus",
        api_key=SecretStr(config.embedding_api_key),
        base_url=config.embedding_base_url,
        temperature=0,
        timeout=120,
        max_retries=2,
    )


def call_llm_json(prompt, llm=None, attempts: int = 2) -> dict:
    """公共 JSON 输出调用：response_format 硬约束 + 正则提取兜底 + 失败重试。

    glm-5.1 带推理链、4v 的 json_object 支持不稳，统一走这里保证解析鲁棒。
    """
    llm = llm or get_chat_model()
    # OpenAI 兼容的 response_format 硬约束；不支持时降级普通调用
    try:
        llm = llm.bind(response_format={"type": "json_object"})
    except Exception:
        pass
    last_raw = ""
    for _ in range(attempts):
        try:
            raw = llm.invoke(prompt).content or ""
        except Exception as exc:
            last_raw = f"LLM 调用失败: {exc}"
            continue
        last_raw = raw
        # 优先尝试整段解析，失败则正则提取 {...}
        try:
            return json.loads(raw)
        except Exception:
            m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    continue
    raise ValueError(f"LLM JSON 解析失败（{attempts} 次尝试）: {last_raw[:300]}")
