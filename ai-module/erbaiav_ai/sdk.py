"""Python SDK：其他 Python 软件插入二伯AI 服务的客户端。"""
import json

try:
    import requests as _requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False
    import urllib.error as _urlerr
    import urllib.request as _urlreq


class AIClient:
    """二伯AI 客户端。用法：
        client = AIClient("http://127.0.0.1:8765")
        client.analyze_text("可疑文本")
        client.code("用 Python 写一个冒泡排序")
    """

    def __init__(self, base_url="http://127.0.0.1:8765", timeout=30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path, payload):
        if _HAS_REQUESTS:
            r = _requests.post(self.base_url + path, json=payload, timeout=self.timeout)
            r.raise_for_status()
            return r.json()["data"]
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = _urlreq.Request(self.base_url + path, data=data,
                              headers={"Content-Type": "application/json"}, method="POST")
        with _urlreq.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))["data"]

    def _get(self, path):
        if _HAS_REQUESTS:
            r = _requests.get(self.base_url + path, timeout=self.timeout)
            r.raise_for_status()
            return r.json()["data"]
        with _urlreq.urlopen(self.base_url + path, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))["data"]

    def health(self):
        return self._get("/v1/health")

    def analyze_text(self, text, context=""):
        return self._post("/v1/analyze/text", {"text": text, "context": context})

    def analyze_file(self, path=None, meta=None):
        return self._post("/v1/analyze/file", {"path": path, "meta": meta or {}})

    def chat(self, text, history=None, system=None):
        return self._post("/v1/chat", {"text": text, "history": history or [], "system": system})

    def embed(self, text):
        return self._post("/v1/embed", {"text": text})

    def search(self, query, corpus, top_k=3):
        return self._post("/v1/search", {"query": query, "corpus": corpus, "top_k": top_k})

    def report(self, summary):
        return self._post("/v1/report", {"summary": summary})

    def agent_run(self, task, workspace=None):
        """让编程代理完整执行一个任务（计划->读写文件->运行验证->总结）。"""
        return self._post("/v1/agent/run", {"task": task, "workspace": workspace})

    def agent_plan(self, task, workspace=None):
        """只看编程代理的计划（不执行）。"""
        return self._post("/v1/agent/plan", {"task": task, "workspace": workspace})

    def fs_list(self, path=".", workspace=None):
        """列出工作区文件。"""
        return self._post("/v1/fs/list", {"path": path, "workspace": workspace})

    def fs_read(self, path, workspace=None):
        """读取工作区文件内容。"""
        return self._post("/v1/fs/read", {"path": path, "workspace": workspace})

    def fs_write(self, path, content, workspace=None):
        """写入/覆盖工作区文件。"""
        return self._post("/v1/fs/write", {"path": path, "content": content,
                                           "workspace": workspace})

    def fs_search(self, pattern, workspace=None):
        """在工作区中按正则搜索内容。"""
        return self._post("/v1/fs/search", {"pattern": pattern, "workspace": workspace})

    def exec_cmd(self, cmd, workspace=None, timeout=30):
        """在工作区目录内执行命令并返回输出。"""
        return self._post("/v1/exec", {"cmd": cmd, "workspace": workspace,
                                       "timeout": timeout})


    # ---------- 数据修改拦截（二伯杀毒：发现修改电脑数据 → 直接拦截 → 可选信任） ----------
    def guard_status(self, workspace=None):
        """查看数据修改拦截状态与信任区。"""
        return self._post("/v1/guard/status", {"workspace": workspace})

    def guard_enable(self, workspace=None, mode="block"):
        """开启数据修改拦截（mode=block 直接拦截 / off 关闭）。"""
        return self._post("/v1/guard/enable", {"workspace": workspace, "mode": mode})

    def guard_disable(self, workspace=None):
        """关闭数据修改拦截。"""
        return self._post("/v1/guard/disable", {"workspace": workspace})

    def guard_trust(self, path, workspace=None, reason="", by="user"):
        """信任某路径：拦截后选择信任，放行后续修改。"""
        return self._post("/v1/guard/trust",
                          {"path": path, "workspace": workspace, "reason": reason, "by": by})

    def guard_untrust(self, path, workspace=None):
        """取消信任某路径。"""
        return self._post("/v1/guard/untrust", {"path": path, "workspace": workspace})

    def guard_attempt(self, kind, path, workspace=None, content="", new_path="", source="未知程序"):
        """模拟程序尝试修改数据（kind=write/delete/rename），未信任会被直接拦截。"""
        return self._post("/v1/guard/attempt",
                          {"kind": kind, "path": path, "workspace": workspace,
                           "content": content, "new_path": new_path, "source": source})

    def guard_decide(self, event_id, action, workspace=None, by="user"):
        """处理被拦截事件：action=allow(信任放行)/block(继续拦截)/restore(回滚恢复)。"""
        return self._post("/v1/guard/decide",
                          {"event_id": event_id, "action": action,
                           "workspace": workspace, "by": by})

    def code(self, request, language=None):
        """让 AI 写代码。request 为自然语言需求，如：用 Python 写一个冒泡排序。"""
        return self._post("/v1/code", {"request": request, "language": language})

    def explain_code(self, code, language=None):
        """让 AI 讲解一段代码。"""
        return self._post("/v1/code/explain", {"code": code, "language": language})
