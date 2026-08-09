# -*- coding: utf-8 -*-
'''编程代理 SDK 演示：让代理写代码、改文件、跑命令。'''
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "..")
from erbaiav_ai.sdk import AIClient

client = AIClient("http://127.0.0.1:8765")

print("=" * 62)
print("1) 让编程代理完整干活")
print("=" * 62)
r = client.agent_run("用 Python 写一个快速排序，保存为 main.py，然后运行验证")
print("后端:", r["backend"], "| 耗时:", r["elapsed_ms"], "ms")
print("计划:", " -> ".join(r["plan"]))
for a in r["actions"]:
    if a["action"] == "write_file":
        print("  [写文件] %s (%s, %d 字节)" % (a["path"], a["op"], a["bytes"]))
    elif a["action"] == "run":
        print("  [运行] %s 返回码=%d" % (a["cmd"], a["returncode"]))
        if a["stdout"]:
            print("    " + a["stdout"].replace("\n", "\n    "))
    elif a["action"] == "finish":
        print("  [总结] " + a["summary"])
print("修改文件:", r["files_changed"])

print()
print("=" * 62)
print("2) 手动文件操作 + 命令")
print("=" * 62)
print("文件列表:", [f["path"] for f in client.fs_list()["files"]])
print("读取 main.py 前 80 字:", client.fs_read("main.py")["content"][:80].replace("\n", "\\n"))
print("执行命令:", client.exec_cmd("python -c \"print('hi from workspace')\"")["stdout"].strip())