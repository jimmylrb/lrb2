"""本地模型后端（Llama/BERT 风格）：轻量、离线、高效。

优先顺序：
  1. sentence_transformers / transformers（BERT 式句向量）
  2. Ollama（本地 Llama/Qwen，GGUF 量化，低资源推理）
都没有时返回 None / False，由引擎自动降级到内置规则引擎。
"""
import json
import os
import time
import urllib.request

OLLAMA_URL = os.environ.get("AI_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("AI_OLLAMA_MODEL", "qwen2.5:3b")  # 或 llama3.2:3b

_ollama_cache = {"t": 0.0, "ok": False}
_embed_model = None


def _transformers_available():
    try:
        import importlib.util
        return (importlib.util.find_spec("sentence_transformers") is not None
                or importlib.util.find_spec("transformers") is not None)
    except Exception:
        return False


def _ollama_alive(timeout=1.0):
    now = time.monotonic()
    if now - _ollama_cache["t"] < 5:
        return _ollama_cache["ok"]
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=timeout) as r:
            _ollama_cache["ok"] = r.status == 200
    except Exception:
        _ollama_cache["ok"] = False
    _ollama_cache["t"] = now
    return _ollama_cache["ok"]


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        name = os.environ.get("AI_LOCAL_EMBED_MODEL", "BAAI/bge-small-zh-v1.5")
        _embed_model = SentenceTransformer(name)
    return _embed_model


def embed(text):
    """BERT 式句向量；无本地模型时返回 None。"""
    if _transformers_available():
        try:
            m = _get_embed_model()
            return [round(float(x), 6) for x in m.encode([text])[0]]
        except Exception:
            return None
    return None


def chat(messages, system=None):
    """Ollama 本地对话（Llama/Qwen）；不可用返回 None。"""
    if not _ollama_alive():
        return None
    if system:
        messages = [{"role": "system", "content": system}] + messages
    payload = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
    try:
        req = urllib.request.Request(
            OLLAMA_URL + "/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data.get("message", {}).get("content")
    except Exception:
        return None


def status():
    return {
        "bert_models": _transformers_available(),
        "ollama_alive": _ollama_alive(),
        "ollama_url": OLLAMA_URL,
        "ollama_model": OLLAMA_MODEL,
    }
