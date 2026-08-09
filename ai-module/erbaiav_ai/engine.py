"""AI 分析引擎：把 Qwen + Llama + BERT 的特点合而为一。

调用链：
  分析/向量 -> 本地模型(若有) + 内置规则引擎(兜底)
  对话/生成 -> 远程大模型(优先) -> Ollama 本地模型 -> 规则引擎兜底
  代码生成 -> 远程代码模型 -> Ollama 代码模型 -> 内置模板兜底
"""
from . import codegen
from . import local_backend
from . import remote_backend
from . import rules


def analyze_text(text, context=""):
    """文本威胁分析：规则判定 + 可选大模型解读。"""
    base = rules.analyze_text(text, context)
    if remote_backend.configured() or local_backend._ollama_alive():
        msgs = [{"role": "user", "content": (
            "你是一名资深安全分析专家。请判断以下文本是否包含恶意内容"
            "（勒索/木马/钓鱼/挖矿/间谍等），用中文给出结论和简要理由。\n\n文本内容：\n"
            + (text or ""))}]
        if remote_backend.configured():
            explanation = remote_backend.chat(msgs, temperature=0.3, max_tokens=300)
        else:
            explanation = local_backend.chat(msgs)
        if explanation and not explanation.startswith("["):
            base["ai_explanation"] = explanation
    return base


def analyze_file(path=None, meta=None):
    """文件分析：规则判定 + 可选大模型解读。"""
    base = rules.analyze_file(path, meta)
    if remote_backend.configured():
        m = base.get("meta") or {}
        summary = ("文件名: %s; 大小: %s 字节; 熵: %s; 类型: %s; 判定: %s (置信度 %s)"
                   % (m.get("name", path or "?"), m.get("size", 0), m.get("entropy", 0),
                      m.get("magic", "?"), base["label"], base["confidence"]))
        msgs = [{"role": "user",
                 "content": "请用中文解读这份文件分析结果，给出风险判断与建议。\n" + summary}]
        explanation = remote_backend.chat(msgs, temperature=0.3, max_tokens=300)
        if explanation and not explanation.startswith("["):
            base["ai_explanation"] = explanation
    return base


def chat(user_text, history=None, system=None):
    """对话助手（Qwen 风格）：远程 -> 本地 -> 规则兜底。"""
    history = history or []
    messages = history[-10:] + [{"role": "user", "content": user_text}]
    if remote_backend.configured():
        out = remote_backend.chat(messages, system=system or "你是二伯AI安全助手，请用中文简洁回答。")
        if out and not out.startswith("["):
            return {"backend": "remote", "content": out}
    out = local_backend.chat(messages, system=system)
    if out:
        return {"backend": "local", "content": out}
    return {"backend": "rules", "content": rules_fallback_chat(user_text)}


def rules_fallback_chat(text):
    """无模型时的兜底回复（基于规则引擎）。"""
    low = (text or "").lower()
    if any(k in low for k in ["你好", "hi", "hello", "在吗"]):
        return "你好！我是二伯AI安全助手。可以问我：这是什么文件？这段话安全吗？"
    if any(k in text for k in ["威胁", "病毒", "安全", "分析"]):
        r = rules.analyze_text(text)
        return "内置规则引擎分析结果：%s（置信度 %s）。原因：%s" % (
            r["label"], r["confidence"], "；".join(r["reasons"][:3]))
    return ("当前未配置任何大模型后端（远程 API Key 或本地 Ollama）。"
            "设置 AI_REMOTE_KEY 即可启用 Qwen 等大模型对话；"
            "或安装 Ollama 并拉取 qwen2.5:3b 启用本地模型。")


def embed(text):
    """文本向量：优先本地 BERT 模型，降级到规则 n-gram 向量。"""
    vec = local_backend.embed(text)
    if vec:
        return {"backend": "local-bert", "vector": vec}
    return {"backend": "rules-ngram", "vector": rules.embedding(text)}


def search(query, corpus, top_k=3):
    """语义检索：本地向量优先，规则向量兜底。"""
    qv = local_backend.embed(query)
    if qv:
        scored = []
        for item in corpus:
            iv = local_backend.embed(item.get("text", ""))
            if iv:
                scored.append((rules.cosine(qv, iv), item))
        if scored:
            scored.sort(key=lambda x: -x[0])
            return [{"score": s, **it} for s, it in scored[:top_k]]
    return rules.search(query, corpus, top_k)


def report(summary_text):
    """生成扫描报告解读（Qwen 风格生成）。"""
    if remote_backend.configured():
        msgs = [{"role": "user",
                 "content": "请用中文把这份杀毒扫描报告总结成通俗易懂的几句话，并给出建议。\n"
                            + (summary_text or "")}]
        out = remote_backend.chat(msgs, temperature=0.4, max_tokens=400)
        if out and not out.startswith("["):
            return {"backend": "remote", "content": out}
    return {"backend": "rules",
            "content": "（规则模式）请配置 AI_REMOTE_KEY 以启用大模型报告解读。"}


def code(request, language=None):
    """代码生成（写代码）：远程代码模型 -> 本地 Ollama -> 内置模板兜底。"""
    return codegen.generate(request, language)


def explain_code(code_text, language=None):
    """代码讲解：远程 -> 本地 -> 规则兜底。"""
    return codegen.explain(code_text, language)
