"""内置规则引擎（零依赖，离线可用）。

相当于 BERT 式"理解"能力的轻量实现：
- 关键词/特征规则 -> 威胁分类
- 字符 n-gram 特征向量 -> 语义检索/去重的降级方案
- 熵值/PE 魔数 -> 文件启发式分析
"""
import hashlib
import math
import os
import re

# ---------------- 威胁特征规则 ----------------
THREAT_RULES = [
    {"id": "R001", "type": "勒索软件", "keywords": ["ransom", "lockbit", "wannacry", "blackcat", "加密", "勒索", "bitcoin", "btc", "tor", "赎金"]},
    {"id": "R002", "type": "木马/后门", "keywords": ["trojan", "backdoor", "remote shell", "cmd.exe /c", "powershell -enc", "meterpreter", "cobalt strike", "木马", "后门", "远控"]},
    {"id": "R003", "type": "挖矿病毒", "keywords": ["miner", "xmrig", "monero", "stratum", "nicehash", "挖矿", "矿池", "cpu utilization"]},
    {"id": "R004", "type": "钓鱼/诈骗", "keywords": ["phishing", "password reset", "verify your account", "免费领取", "中奖", "钓鱼", "转账", "退款", "验证码", "假冒", "紧急通知", "冻结"]},
    {"id": "R005", "type": "间谍/窃密", "keywords": ["keylogger", "spyware", "screen capture", "webcam", "键盘记录", "间谍", "窃密", "credential"]},
    {"id": "R006", "type": "广告/流氓软件", "keywords": ["adware", "pup", "browser hijack", "弹窗", "广告插件", "主页劫持", "推广"]},
    {"id": "R007", "type": "注入/漏洞利用", "keywords": ["shellcode", "exploit", "buffer overflow", "code injection", "hook", "注入", "漏洞利用", "payload"]},
]

# Windows 危险 API / 特征串（启发式）
SUSPICIOUS_API = [
    "VirtualAlloc", "VirtualProtect", "WriteProcessMemory", "CreateRemoteThread",
    "SetWindowsHookEx", "NtUnmapViewOfSection", "LoadLibrary", "GetProcAddress",
    "ShellExecute", "RegSetValue", "WinExec", "CreateProcess",
]

PE_MAGIC = b"MZ"
ELF_MAGIC = b"\x7fELF"


def _norm(s):
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]", "", s or "").lower()


def _char_ngrams(text, n=2):
    t = _norm(text)
    if len(t) < n:
        return {t} if t else set()
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    n = len(data)
    e = 0.0
    for c in freq.values():
        p = c / n
        e -= p * math.log2(p)
    return e


def analyze_text(text, context=""):
    """规则版文本威胁分析：返回 {label, confidence, reasons, matched}"""
    text = text or ""
    low = text.lower()
    matched = []
    reasons = []
    for rule in THREAT_RULES:
        hits = [k for k in rule["keywords"] if k.lower() in low]
        if hits:
            matched.append({"rule": rule["id"], "type": rule["type"], "hits": hits[:6]})
            reasons.append("命中 %s 特征: %s" % (rule["type"], ", ".join(hits[:4])))

    api_hits = [a for a in SUSPICIOUS_API if a.lower() in low]
    if api_hits:
        reasons.append("发现危险 API/调用特征: %s" % ", ".join(api_hits[:5]))

    base64_len = len(re.findall(r"[A-Za-z0-9+/]{40,}={0,2}", text))
    if base64_len:
        reasons.append("发现疑似 Base64 载荷（%d 处）" % base64_len)

    enc_pow = len(re.findall(r"powershell\s+-(enc|encodedcommand)", low))
    if enc_pow:
        reasons.append("发现 PowerShell 编码执行特征（免杀常见手法）")

    if not matched and not api_hits and not base64_len and not enc_pow:
        return {"label": "正常", "confidence": 0.92, "reasons": ["未命中任何威胁特征"], "matched": []}

    score = min(0.99, 0.45 + 0.15 * len(matched) + 0.08 * min(len(api_hits), 3)
                + 0.05 * min(base64_len, 2) + 0.10 * enc_pow)
    label = matched[0]["type"] if matched else ("可疑行为" if (api_hits or enc_pow) else "可疑")
    return {"label": label, "confidence": round(score, 3), "reasons": reasons[:8], "matched": matched[:5]}


def analyze_file(path=None, meta=None):
    """规则版文件分析：结合大小/熵/首字节魔数，返回判定结果。"""
    meta = dict(meta or {})
    reasons = []
    matched = []
    if path and os.path.isfile(path):
        with open(path, "rb") as f:
            head = f.read(4096)
        meta.setdefault("size", os.path.getsize(path))
        meta.setdefault("entropy", round(entropy(head), 3))
        meta.setdefault("md5", hashlib.md5(head).hexdigest())
        meta.setdefault("magic", "PE" if head.startswith(PE_MAGIC) else ("ELF" if head.startswith(ELF_MAGIC) else "data"))
    size = meta.get("size") or 0
    ent = meta.get("entropy") or 0.0
    magic = meta.get("magic") or "unknown"

    if ent >= 7.0 and size > 0:
        reasons.append("熵值偏高 %.2f（>7.0，常见于加密/压缩载荷）" % ent)
        matched.append("high-entropy")
    if magic == "PE":
        reasons.append("Windows PE 可执行文件")
    if size == 0:
        reasons.append("空文件，风险低")

    risk = 0.0
    if "high-entropy" in matched:
        risk += 0.5
    if ent >= 7.5:
        risk += 0.3
    if magic == "PE":
        risk += 0.1

    if risk >= 0.7:
        label = "高度可疑"
    elif risk >= 0.4:
        label = "可疑"
    else:
        label = "低风险"
    confidence = round(min(0.97, 0.5 + risk), 3)
    if not reasons:
        reasons.append("未发现明显异常特征")
    return {"label": label, "confidence": confidence, "reasons": reasons, "meta": meta}


def embedding(text, dim=64):
    """把文本映射为固定维度特征向量（字符 n-gram -> 哈希桶计数 -> 归一化）。

    当本地 BERT 模型不可用时，作为 /v1/embed 的降级实现；
    语义相近的文本会产生相近向量。
    """
    ngrams = _char_ngrams(text, 2) | _char_ngrams(text, 3)
    vec = [0.0] * dim
    for g in ngrams:
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return round(dot / (na * nb), 6)


def search(query, corpus, top_k=3):
    """在语料里找最相似的条目（离线语义检索降级方案）。corpus: [{"id","text"}, ...]"""
    qv = embedding(query)
    scored = []
    for item in corpus:
        iv = embedding(item.get("text", ""))
        scored.append((cosine(qv, iv), item))
    scored.sort(key=lambda x: -x[0])
    return [{"score": s, **it} for s, it in scored[:top_k]]
