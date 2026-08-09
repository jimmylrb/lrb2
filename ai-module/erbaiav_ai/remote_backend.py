"""远程大模型后端（Qwen 风格）：OpenAI 兼容 API，用 urllib 实现，零依赖。

设置环境变量启用：
  AI_REMOTE_BASE    例如 https://dashscope.aliyuncs.com/compatible-mode/v1
  AI_REMOTE_KEY     你的 API Key
  AI_REMOTE_MODEL   例如 qwen-plus / qwen-coder-plus / deepseek-chat / gpt-4o-mini
"""
import json
import os
import urllib.error
import urllib.request


def configured():
    return bool(os.environ.get("AI_REMOTE_KEY") or os.environ.get("AI_REMOTE_BASE"))


def model_name():
    return os.environ.get("AI_REMOTE_MODEL", "qwen-plus")


def chat(messages, system=None, temperature=0.7, max_tokens=1024):
    base = os.environ.get("AI_REMOTE_BASE",
                          "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
    key = os.environ.get("AI_REMOTE_KEY", "")
    model = model_name()
    if system:
        messages = [{"role": "system", "content": system}] + messages
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return "[远程模型调用失败 HTTP %d] %s" % (e.code, e.read().decode("utf-8", "ignore")[:300])
    except Exception as e:
        return "[远程模型调用失败] %s" % e
