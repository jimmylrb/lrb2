# -*- coding: utf-8 -*-
'''安全的工作区文件操作：把 AI 的读写限制在指定工作区内（防路径穿越）。

所有文件路径都相对于工作区（默认 ai-module/workspace，可用 AI_WORKSPACE 覆盖），
命令在指定工作目录内执行并带超时，避免代理失控。
'''
import os
import re
import subprocess

DEFAULT_WORKSPACE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workspace")


def resolve_workspace(workspace=None):
    '''解析并确保工作区目录存在。'''
    if not workspace:
        workspace = os.environ.get("AI_WORKSPACE", DEFAULT_WORKSPACE)
    workspace = os.path.abspath(os.path.expanduser(str(workspace)))
    os.makedirs(workspace, exist_ok=True)
    return workspace


def safe_join(workspace, rel):
    '''把相对路径安全地拼到工作区内；越界（..）直接报错。'''
    workspace = os.path.abspath(workspace)
    rel = (rel or ".").replace("\\", "/")
    target = os.path.abspath(os.path.join(workspace, rel))
    if not (target == workspace or target.startswith(workspace + os.sep)):
        raise ValueError("路径越界: %s（工作区: %s）" % (rel, workspace))
    return target


def list_files(workspace=None, rel="."):
    '''递归列出工作区文件，返回 [{path, size}, ...]。'''
    ws = resolve_workspace(workspace)
    root = safe_join(ws, rel)
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            relpath = os.path.relpath(full, ws).replace("\\", "/")
            files.append({"path": relpath, "size": size})
    files.sort(key=lambda x: x["path"])
    return files


def read_file(workspace=None, rel="."):
    '''读取工作区文件（UTF-8，容错替换），返回 {path, size, content}。'''
    ws = resolve_workspace(workspace)
    target = safe_join(ws, rel)
    if not os.path.isfile(target):
        raise FileNotFoundError("文件不存在: %s" % rel)
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return {"path": os.path.relpath(target, ws).replace("\\", "/"),
            "size": len(content.encode("utf-8")),
            "content": content}


def write_file(workspace=None, rel="untitled.txt", content=""):
    '''写入/覆盖工作区文件，自动建目录。返回 {path, action: created|updated, bytes}。'''
    ws = resolve_workspace(workspace)
    target = safe_join(ws, rel)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    existed = os.path.exists(target)
    content = content or ""
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    return {"path": os.path.relpath(target, ws).replace("\\", "/"),
            "action": "updated" if existed else "created",
            "bytes": len(content.encode("utf-8"))}


def search_files(workspace=None, pattern=""):
    '''按正则搜索工作区文件内容，返回 "路径:行号:行内容" 命中列表。'''
    ws = resolve_workspace(workspace)
    try:
        rx = re.compile(pattern, re.I)
    except Exception:
        return []
    hits = []
    for f in list_files(ws):
        if not pattern:
            hits.append(f["path"])
            continue
        try:
            info = read_file(ws, f["path"])
        except Exception:
            continue
        for i, line in enumerate(info["content"].splitlines(), 1):
            if rx.search(line):
                hits.append("%s:%d:%s" % (f["path"], i, line.strip()[:120]))
                if len(hits) >= 200:
                    return hits
    return hits


def run_command(cmd, workspace=None, timeout=30):
    '''在工作区目录内执行命令，返回 {cmd, cwd, returncode, stdout, stderr, timed_out}。'''
    ws = resolve_workspace(workspace)
    cmdline = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.run(cmdline, cwd=ws, shell=True,
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=int(timeout or 30), **kwargs)
        return {"cmd": cmdline, "cwd": ws, "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[-4000:],
                "stderr": (proc.stderr or "")[-4000:],
                "timed_out": False}
    except subprocess.TimeoutExpired:
        return {"cmd": cmdline, "cwd": ws, "returncode": -1,
                "stdout": "", "stderr": "命令超时（%s 秒）" % timeout,
                "timed_out": True}
    except Exception as e:
        return {"cmd": cmdline, "cwd": ws, "returncode": -1,
                "stdout": "", "stderr": "执行失败: %s" % e,
                "timed_out": False}