# -*- coding: utf-8 -*-
"""可选增强：安装本地 BERT 句向量模型依赖（需要网络）。

用法:
  python scripts/download_models.py

安装后重启服务，/v1/embed 与 /v1/search 将自动使用 BERT 语义向量。
"""
import subprocess
import sys


def main():
    print("正在安装 sentence-transformers（自动附带 CPU 版 torch，约 1~2 GB）...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"])
    print("完成。重启服务后 /v1/embed 将自动使用 BERT 句向量。")
    print("如需 Ollama 本地大模型（Llama/Qwen），请到 https://ollama.com 安装后执行：")
    print("  ollama pull qwen2.5:3b")


if __name__ == "__main__":
    main()
