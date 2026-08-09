# -*- coding: utf-8 -*-
'''Codex 式编程代理：理解任务 -> 制定计划 -> 读写文件/执行命令 -> 验证 -> 总结。

后端优先级：
  1. 远程大模型（Qwen 等）生成 JSON 行动计划（支持多轮迭代）
  2. 本地 Ollama（若可用）
  3. 内置规则规划器（离线兜底：模板代码 + 文件操作 + 运行验证）

动作类型（JSON）：
  {"action":"write_file","path":"相对路径","content":"文件内容"}
  {"action":"read_file","path":"相对路径"}
  {"action":"list_dir","path":"."}
  {"action":"run","cmd":"命令行","timeout":30}
  {"action":"explain","path":"相对路径"}
  {"action":"finish","summary":"总结"}
'''
import json
import os
import re
import time

from . import codegen, fsops, local_backend, remote_backend

MAX_ACTIONS = 20          # 单次任务最多动作数，防失控
DEFAULT_TIMEOUT = 30      # 每条命令默认超时秒数

PLAN_SYSTEM = (
    '你是一个像 Codex 一样工作的编程代理。你会收到一个编程任务和当前工作区文件列表。'
    '请只输出一个 JSON 数组，每个元素是一个动作，动作类型只能是：\n'
    '- {"action":"write_file","path":"相对路径","content":"文件内容"}\n'
    '- {"action":"read_file","path":"相对路径"}\n'
    '- {"action":"list_dir","path":"."}\n'
    '- {"action":"run","cmd":"要执行的命令行","timeout":30}\n'
    '- {"action":"finish","summary":"一句话总结"}\n'
    '先规划再动手：通常先 write_file 创建或修改代码，再 run 运行验证，最后 finish 总结。'
    '路径必须使用正斜杠相对路径，不要包含中文引号。只输出 JSON，不要输出其他文字。'
)

_MAIN_FILES = {
    "python": "main.py", "javascript": "main.js", "js": "main.js",
    "cpp": "main.cpp", "java": "Main.java", "html": "index.html",
}


def _chat(prompt, system=PLAN_SYSTEM, temperature=0.2, max_tokens=3000):
    '''优先远程大模型，其次本地 Ollama；都不行返回 None。'''
    if remote_backend.configured():
        out = remote_backend.chat([{"role": "user", "content": prompt}],
                                  system=system, temperature=temperature,
                                  max_tokens=max_tokens)
        if out and not out.startswith("["):
            return out
    out = local_backend.chat([{"role": "user", "content": prompt}], system=system)
    if out:
        return out
    return None


def _parse_actions(text):
    '''从模型输出里提取 JSON 动作数组；失败返回 None。'''
    if not text:
        return None
    t = text.strip()
    # 去掉 markdown 代码块围栏
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I | re.S)
    m = re.search(r"\[.*\]", t, re.S)
    if m:
        t = m.group(0)
    try:
        data = json.loads(t)
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    valid = {"write_file", "read_file", "list_dir", "run", "explain", "finish"}
    actions = []
    for a in data:
        if not isinstance(a, dict) or a.get("action") not in valid:
            continue
        if a["action"] == "finish":
            actions.append({"action": "finish", "summary": str(a.get("summary", ""))})
        elif a["action"] in ("read_file", "list_dir", "explain"):
            actions.append({"action": a["action"],
                            "path": str(a.get("path", "."))})
        elif a["action"] == "run":
            actions.append({"action": "run", "cmd": str(a.get("cmd", "")),
                            "timeout": int(a.get("timeout") or DEFAULT_TIMEOUT)})
        elif a["action"] == "write_file":
            actions.append({"action": "write_file",
                            "path": str(a.get("path", "untitled.txt")),
                            "content": str(a.get("content", ""))})
    return actions[:MAX_ACTIONS]


def _plan_llm(task, workspace):
    '''用大模型生成行动计划。'''
    files = [f["path"] for f in fsops.list_files(workspace)]
    prompt = ("编程任务：%s\n\n当前工作区文件：\n%s\n\n请输出 JSON 动作数组。"
              % (task, "\n".join(files) if files else "（空工作区）"))
    return _parse_actions(_chat(prompt))


def _main_filename(lang):
    return _MAIN_FILES.get((lang or "").lower(), "main.py")


def _task_note(task):
    return ("# 任务记录\n\n%s\n\n> 由二伯AI 编程代理创建。\n"
            "> 配置 AI_REMOTE_KEY（Qwen-Coder）后，可让大模型自动编写任意代码并运行验证。\n"
            % (task or ""))


def _plan_rules(task):
    '''离线规则规划器：把常见任务转成动作序列。'''
    low = (task or "").lower()
    actions = []

    # 1) 列目录
    if any(k in low for k in ["列目录", "列出文件", "查看目录", "list files", "ls"]):
        actions.append({"action": "list_dir", "path": "."})
        actions.append({"action": "finish", "summary": "已列出工作区文件。"})
        return actions

    # 2) 读文件
    m = re.search(r"(?:读|读取|查看|open|read)\s+([\w\-./\\]+\.\w+)", task)
    if m:
        actions.append({"action": "read_file", "path": m.group(1)})
        actions.append({"action": "finish", "summary": "已读取文件 %s。" % m.group(1)})
        return actions

    # 3) 讲解代码
    if any(k in task for k in ["讲解", "解释", "explain", "什么意思", "说明"]):
        m2 = re.search(r"([\w\-./\\]+\.\w+)", task)
        if m2:
            actions.append({"action": "read_file", "path": m2.group(1)})
            actions.append({"action": "explain", "path": m2.group(1)})
            actions.append({"action": "finish", "summary": "已讲解 %s。" % m2.group(1)})
            return actions

    # 4) 写代码 + 运行验证（内置模板匹配）
    gen = codegen.generate(task)
    if gen.get("name") and gen["name"] != "未匹配":
        fname = _main_filename(gen["language"])
        actions.append({"action": "write_file", "path": fname, "content": gen["code"]})
        if gen["language"] in ("python", "javascript"):
            runner = "python" if gen["language"] == "python" else "node"
            actions.append({"action": "run",
                            "cmd": "%s %s" % (runner, fname), "timeout": 20})
        actions.append({"action": "finish",
                        "summary": "已按模板生成「%s」并写入 %s。"
                                   % (gen["name"], fname)})
        return actions

    # 5) 通用兜底：列目录 + 写任务记录 + 提示配置大模型
    actions.append({"action": "list_dir", "path": "."})
    actions.append({"action": "write_file", "path": "TASK.md",
                    "content": _task_note(task)})
    actions.append({"action": "finish",
                    "summary": "未匹配内置模板，已把任务写入 TASK.md。"
                               "配置 AI_REMOTE_KEY（Qwen-Coder）后即可自动编写任意代码。"})
    return actions


def _describe(action):
    k = action.get("action")
    if k == "write_file":
        return "写入文件 %s" % action.get("path")
    if k == "read_file":
        return "读取文件 %s" % action.get("path")
    if k == "list_dir":
        return "列出目录 %s" % action.get("path")
    if k == "run":
        return "运行命令: %s" % action.get("cmd")
    if k == "explain":
        return "讲解代码 %s" % action.get("path")
    if k == "finish":
        return "总结"
    return k


def _exec_action(action, workspace):
    '''执行单个动作，返回结构化结果。'''
    kind = action.get("action")
    try:
        if kind == "write_file":
            r = fsops.write_file(workspace, action.get("path"), action.get("content"))
            return {"action": kind, "ok": True,
                    "path": r["path"], "op": r["action"], "bytes": r["bytes"],
                    "preview": (action.get("content") or "")[:200]}
        if kind == "read_file":
            info = fsops.read_file(workspace, action.get("path"))
            return {"action": kind, "ok": True, "path": info["path"],
                    "size": info["size"], "content": info["content"]}
        if kind == "list_dir":
            files = fsops.list_files(workspace, action.get("path", "."))
            return {"action": kind, "ok": True,
                    "files": [f["path"] for f in files], "count": len(files)}
        if kind == "run":
            r = fsops.run_command(action.get("cmd"), workspace,
                                  action.get("timeout") or DEFAULT_TIMEOUT)
            return {"action": kind, "ok": r["returncode"] == 0,
                    "cmd": r["cmd"], "returncode": r["returncode"],
                    "stdout": r["stdout"], "stderr": r["stderr"],
                    "timed_out": r["timed_out"]}
        if kind == "explain":
            info = fsops.read_file(workspace, action.get("path"))
            exp = codegen.explain(info["content"])
            return {"action": kind, "ok": True, "path": info["path"],
                    "explanation": exp["explanation"], "stats": exp.get("stats")}
        if kind == "finish":
            return {"action": kind, "ok": True, "summary": action.get("summary", "")}
        return {"action": kind, "ok": False, "error": "未知动作: %s" % kind}
    except (ValueError, FileNotFoundError) as e:
        return {"action": kind, "ok": False, "error": str(e)}
    except Exception as e:
        return {"action": kind, "ok": False, "error": "执行异常: %s" % e}


def plan(task, workspace=None):
    '''只制定计划（不执行），返回 {backend, plan, actions}。'''
    task = (task or "").strip()
    workspace = fsops.resolve_workspace(workspace)
    backend, actions = _choose_plan(task, workspace)
    return {
        "task": task,
        "backend": backend,
        "workspace": workspace,
        "plan": [_describe(a) for a in actions if a.get("action") != "finish"],
        "actions": actions,
    }


def _choose_plan(task, workspace):
    '''按后端优先级选计划：remote -> local -> rules。'''
    if remote_backend.configured():
        actions = _plan_llm(task, workspace)
        if actions:
            return "remote", actions
    if local_backend._ollama_alive():
        actions = _plan_llm(task, workspace)  # 内部会优先 remote；此处只走 local 分支
        if actions:
            return "local", actions
    return "rules", _plan_rules(task)


def run(task, workspace=None, max_actions=MAX_ACTIONS):
    '''完整跑一个编程任务：计划 -> 执行 -> 验证 -> 总结。'''
    task = (task or "").strip()
    workspace = fsops.resolve_workspace(workspace)
    if not task:
        return {"task": "", "backend": "rules", "status": "error",
                "workspace": workspace, "error": "请输入任务描述"}

    start = time.time()
    backend, actions = _choose_plan(task, workspace)
    actions = actions[:max_actions]

    executed = []
    files_changed = []
    summary = ""
    for a in actions:
        r = _exec_action(a, workspace)
        executed.append(r)
        if r["action"] == "write_file" and r.get("ok"):
            files_changed.append(r.get("path"))
        if r["action"] == "finish":
            summary = r.get("summary", "")
        if r["action"] == "finish":
            break

    if not summary:
        summary = ("任务执行完成：%d 个动作，修改文件 %d 个。"
                   % (len(executed), len(files_changed)))
    files = [f["path"] for f in fsops.list_files(workspace)]
    return {
        "task": task,
        "backend": backend,
        "status": "done",
        "workspace": workspace,
        "plan": [_describe(a) for a in actions if a.get("action") != "finish"],
        "actions": executed,
        "files_changed": files_changed,
        "files": files,
        "summary": summary,
        "elapsed_ms": int((time.time() - start) * 1000),
    }