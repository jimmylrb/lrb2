"""二伯AI 可插拔服务入口 —— 零依赖，`python server.py` 即可启动。

设计：综合 Qwen(生成/对话/工具) + Llama(本地高效推理) + BERT(双向理解/向量) 的特点，
对外提供统一 REST API，可被 C++ / Python / JS / 任何语言调用。

启动：
  python server.py                    # 默认 http://127.0.0.1:8765
  浏览器打开 http://127.0.0.1:8765/    # 可视化演示页（含"写代码"功能）
  接口说明见 http://127.0.0.1:8765/v1

环境变量：
  AI_HOST / AI_PORT                    # 监听地址和端口
  AI_REMOTE_BASE / AI_REMOTE_KEY / AI_REMOTE_MODEL   # Qwen 等 OpenAI 兼容 API（推荐）
  AI_OLLAMA_URL / AI_OLLAMA_MODEL                    # 本地 Ollama (Llama/Qwen)
  AI_LOCAL_EMBED_MODEL                               # BERT 句向量模型
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from erbaiav_ai import __version__, agent, engine, fsops, guard, local_backend, remote_backend

HOST = os.environ.get("AI_HOST", "127.0.0.1")
PORT = int(os.environ.get("AI_PORT", "8765"))
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_html():
    """读取可视化演示页（web/ai-demo.html），让根路径直接打开网页。"""
    try:
        with open(os.path.join(_BASE_DIR, "web", "ai-demo.html"),
                  "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


HTML_INDEX = _load_html()


def api_info():
    return {
        "name": "ErBaiAI 可插拔 AI 模块",
        "version": __version__,
        "desc": "综合 Qwen(生成/对话) + Llama(本地高效推理) + BERT(双向理解/向量) 的可插拔 AI 服务",
        "web_demo": "浏览器打开 http://%s:%d/ 使用可视化演示页" % (HOST, PORT),
        "endpoints": {
            "GET  /": "可视化演示页(HTML，含写代码)",
            "GET  /v1": "本接口说明(JSON)",
            "GET  /v1/health": "健康检查",
            "POST /v1/analyze/text": "文本威胁分析",
            "POST /v1/analyze/file": "文件分析",
            "POST /v1/chat": "AI 对话助手",
            "POST /v1/code": "写代码（自然语言 -> 代码）",
            "POST /v1/code/explain": "讲解代码",
            "POST /v1/embed": "文本向量(BERT式)",
            "POST /v1/search": "语义检索",
            "POST /v1/report": "扫描报告解读",
            "POST /v1/agent/run": "编程代理: 计划->读写文件->执行命令->总结",
            "POST /v1/agent/plan": "编程代理: 只预览计划(不执行)",
            "POST /v1/fs/list": "列出工作区文件",
            "POST /v1/fs/read": "读取工作区文件",
            "POST /v1/fs/write": "写入工作区文件",
            "POST /v1/fs/search": "在工作区中搜索内容",
            "POST /v1/exec": "在工作区执行命令",
            "POST /v1/guard/status": "数据修改拦截: 保护状态与信任区",
            "POST /v1/guard/enable": "开启数据修改拦截(mode=block/off)",
            "POST /v1/guard/disable": "关闭数据修改拦截",
            "POST /v1/guard/trust": "信任某路径(放行后续修改)",
            "POST /v1/guard/untrust": "取消信任某路径",
            "POST /v1/guard/attempt": "模拟程序尝试修改数据(write/delete/rename)",
            "POST /v1/guard/decide": "处理被拦截事件(allow=信任放行/block=继续拦截/restore=回滚恢复)",
        },
    }


def ok(data):
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False).encode("utf-8")


def err(msg, code=400):
    return json.dumps({"ok": False, "error": msg}, ensure_ascii=False).encode("utf-8"), code


class Handler(BaseHTTPRequestHandler):
    server_version = "ErBaiAI/" + __version__

    def _send(self, body, code=200, ctype="application/json; charset=utf-8"):
        if isinstance(body, tuple):
            body, code = body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(b"", 204)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/demo"):
            if HTML_INDEX is not None:
                self._send(HTML_INDEX.encode("utf-8"),
                           ctype="text/html; charset=utf-8")
            else:
                self._send(ok(api_info()))
        elif path == "/v1":
            self._send(ok(api_info()))
        elif path == "/v1/health":
            self._send(ok({"status": "up",
                           "backends": {"remote": remote_backend.configured(),
                                        **local_backend.status()}}))
        else:
            self._send(err("not found: " + path, 404))

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception as e:
            return self._send(err("invalid json: %s" % e))
        try:
            if path == "/v1/analyze/text":
                self._send(ok(engine.analyze_text(body.get("text", ""), body.get("context", ""))))
            elif path == "/v1/analyze/file":
                self._send(ok(engine.analyze_file(body.get("path"), body.get("meta") or {})))
            elif path == "/v1/chat":
                self._send(ok(engine.chat(body.get("text", ""), body.get("history") or [],
                                          body.get("system"))))
            elif path == "/v1/code":
                self._send(ok(engine.code(body.get("request", ""), body.get("language"))))
            elif path == "/v1/code/explain":
                self._send(ok(engine.explain_code(body.get("code", ""), body.get("language"))))
            elif path == "/v1/embed":
                self._send(ok(engine.embed(body.get("text", ""))))
            elif path == "/v1/search":
                self._send(ok(engine.search(body.get("query", ""), body.get("corpus") or [],
                                            body.get("top_k") or 3)))
            elif path == "/v1/agent/run":
                self._send(ok(agent.run(body.get("task", ""), body.get("workspace"))))
            elif path == "/v1/agent/plan":
                self._send(ok(agent.plan(body.get("task", ""), body.get("workspace"))))
            elif path == "/v1/fs/list":
                self._send(ok({"workspace": fsops.resolve_workspace(body.get("workspace")),
                               "files": fsops.list_files(body.get("workspace"),
                                                         body.get("path") or ".")}))
            elif path == "/v1/fs/read":
                try:
                    self._send(ok(fsops.read_file(body.get("workspace"), body.get("path") or ".")))
                except (ValueError, FileNotFoundError) as e:
                    self._send(err(str(e), 400))
            elif path == "/v1/fs/write":
                try:
                    self._send(ok(fsops.write_file(body.get("workspace"),
                                                   body.get("path") or "untitled.txt",
                                                   body.get("content") or "")))
                except (ValueError, FileNotFoundError) as e:
                    self._send(err(str(e), 400))
            elif path == "/v1/fs/search":
                self._send(ok({"hits": fsops.search_files(body.get("workspace"),
                                                          body.get("pattern") or "")}))
            elif path == "/v1/exec":
                self._send(ok(fsops.run_command(body.get("cmd", ""),
                                                body.get("workspace"),
                                                body.get("timeout") or 30)))
            elif path == "/v1/guard/status":
                g = guard.DataGuard(body.get("workspace"))
                self._send(ok(g.status()))
            elif path == "/v1/guard/enable":
                g = guard.DataGuard(body.get("workspace"))
                self._send(ok(g.enable(body.get("mode") or "block")))
            elif path == "/v1/guard/disable":
                g = guard.DataGuard(body.get("workspace"))
                self._send(ok(g.disable()))
            elif path == "/v1/guard/trust":
                g = guard.DataGuard(body.get("workspace"))
                self._send(ok(g.trust(body.get("path", ""), body.get("reason", ""),
                                      body.get("by", "user"))))
            elif path == "/v1/guard/untrust":
                g = guard.DataGuard(body.get("workspace"))
                self._send(ok(g.untrust(body.get("path", ""))))
            elif path == "/v1/guard/attempt":
                g = guard.DataGuard(body.get("workspace"))
                kind = body.get("kind", "write")
                if kind == "delete":
                    self._send(ok(g.attempt_delete(body.get("path", ""),
                                                   body.get("source", "未知程序"))))
                elif kind == "rename":
                    self._send(ok(g.attempt_rename(body.get("path", ""),
                                                   body.get("new_path", ""),
                                                   body.get("source", "未知程序"))))
                else:
                    self._send(ok(g.attempt_write(body.get("path", ""),
                                                  body.get("content", ""),
                                                  body.get("source", "未知程序"))))
            elif path == "/v1/guard/decide":
                g = guard.DataGuard(body.get("workspace"))
                self._send(ok(g.decide(body.get("event_id", ""), body.get("action", ""),
                                       body.get("by", "user"))))
            elif path == "/v1/report":
                self._send(ok(engine.report(body.get("summary", ""))))
            else:
                self._send(err("not found: " + path, 404))
        except Exception as e:
            self._send(err("internal error: %s" % e, 500))

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print("=" * 62)
    print("  二伯AI 可插拔 AI 模块 v%s" % __version__)
    print("  演示页面   : http://%s:%d/（含写代码）" % (HOST, PORT))
    print("  接口说明   : http://%s:%d/v1" % (HOST, PORT))
    print("  健康检查   : http://%s:%d/v1/health" % (HOST, PORT))
    print("  远程大模型 : %s" % ("已配置" if remote_backend.configured()
                                  else "未配置（设置 AI_REMOTE_KEY 启用 Qwen 等）"))
    print("  本地 Ollama: %s" % ("在线（%s）" % local_backend.OLLAMA_MODEL
                                  if local_backend._ollama_alive() else "未检测到"))
    print("  本地 BERT  : %s" % ("可用" if local_backend._transformers_available() else "未安装"))
    print("  提示: 其他软件可用 HTTP 调用；局域网访问请设置 AI_HOST=0.0.0.0")
    print("=" * 62)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
