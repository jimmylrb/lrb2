# -*- coding: utf-8 -*-
"""Python 软件接入二伯AI 服务的示例（使用官方 SDK）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from erbaiav_ai.sdk import AIClient

client = AIClient("http://127.0.0.1:8765")

print("== 0. 健康检查 ==")
print(client.health())

print("\n== 1. 文本威胁分析 ==")
r = client.analyze_text(
    "检测到疑似勒索软件：文件尝试连接 tor 节点并加密磁盘，要求支付 bitcoin 赎金")
print("判定:", r["label"], "| 置信度:", r["confidence"])
for x in r["reasons"]:
    print("  -", x)

print("\n== 2. 文件分析 ==")
r = client.analyze_file(meta={"name": "invoice.pdf.exe", "size": 204800,
                              "entropy": 7.82, "magic": "PE"})
print("判定:", r["label"], "| 置信度:", r["confidence"], "| 原因:", r["reasons"])

print("\n== 3. 语义检索 ==")
corpus = [
    {"id": 1, "text": "勒索软件加密用户文件并要求比特币赎金"},
    {"id": 2, "text": "挖矿木马占用 CPU 挖门罗币"},
    {"id": 3, "text": "钓鱼邮件诱导用户输入银行卡密码"},
]
r = client.search("文件被加密了，要我付钱才能解锁", corpus)
for item in r:
    print("  ", item["score"], "-", item["text"])

print("\n== 4. AI 对话 ==")
r = client.chat("什么是勒索软件？")
print("后端:", r["backend"])
print(r["content"])
