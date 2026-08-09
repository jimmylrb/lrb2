# 🛡️ 二伯AI —— 可插拔 AI 能力模块

一个把 **Qwen + Llama + BERT** 三大模型特点合而为一、可以**插入任何软件**的 AI 服务模块。
零依赖（仅 Python 标准库），`python server.py` 一条命令启动，C++ / Python / JS / 网页都能直接调用。

| 模型特点 | 在本模块中的体现 |
|---------|----------------|
| **Qwen**（生成/对话/多语言/工具） | `/v1/chat` 对话助手、`/v1/code` 写代码、`/v1/report` 报告解读；可接任意 OpenAI 兼容 API（Qwen-Coder 等） |
| **Llama**（本地高效推理/量化/轻量） | 支持本地 [Ollama](https://ollama.com)（`qwen2.5:3b` / `llama3.2:3b`），低资源离线运行 |
| **BERT**（双向理解/句向量/语义） | `/v1/embed` 句向量、`/v1/search` 语义检索；可接本地 sentence-transformers |

---

## 🚀 快速开始

```bat
cd ai-module
python server.py
```

启动后：

- API 列表：http://127.0.0.1:8765/
- 健康检查：http://127.0.0.1:8765/v1/health
- 网页演示：双击打开 `web/ai-demo.html`（或嵌入官网）

> 无任何模型也能用：内置规则引擎（BERT 式理解的轻量实现）离线可用。
> 想启用真·大模型，见下文"接入大模型"。

---

## 🔌 如何插入你的软件

### 1️⃣ C++ 软件（如 ErBaiAV 杀毒引擎）

```cpp
// 用 WinHTTP POST JSON 即可，示例见 clients/demo_cpp.cpp
// 编译: cl /EHsc clients/demo_cpp.cpp /link winhttp.lib
// 运行: demo_cpp.exe "疑似勒索软件：尝试连接tor节点并加密磁盘"
```

典型用法：扫描到可疑文件 → 把文件名/大小/熵/特征串发给 `/v1/analyze/file` → 得到 AI 判定与解读。

### 2️⃣ Python 软件

```python
from erbaiav_ai.sdk import AIClient
client = AIClient("http://127.0.0.1:8765")
r = client.analyze_text("紧急通知：点击链接输入密码验证，否则冻结账户！")
print(r["label"], r["confidence"], r["reasons"])
```

完整示例：`clients/demo_python.py`

### 3️⃣ 网页 / JS

```js
fetch("http://127.0.0.1:8765/v1/analyze/text", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: "可疑内容" })
}).then(r => r.json()).then(j => console.log(j.data));
```

完整示例：`clients/demo_js.js`；现成网页：`web/ai-demo.html`（可 `<iframe>` 嵌入官网）。

### 4️⃣ 任意语言 / 命令行

```bat
curl -X POST http://127.0.0.1:8765/v1/analyze/text -H "Content-Type: application/json" -d "{\"text\":\"检测到勒索软件连接tor节点\"}"
```

---

## 🧠 接入真·大模型（推荐，Qwen 风格）

### 远程 API（云上大模型）

```bat
set AI_REMOTE_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
set AI_REMOTE_KEY=你的阿里云百炼API Key
set AI_REMOTE_MODEL=qwen-coder-plus   :: 写代码用 qwen-coder-plus / deepseek-coder；对话用 qwen-plus
python server.py
```

兼容任何 OpenAI 格式接口：通义千问、DeepSeek、智谱、Kimi、GPT 等。

### 本地大模型（Llama 风格，离线）

```bat
:: 1) 安装 Ollama: https://ollama.com
:: 2) 拉取小模型（量化，内存友好）
ollama pull qwen2.5:3b
:: 3) 启动服务（自动检测到 Ollama）
python server.py
```

### 本地 BERT 句向量（可选）

```bat
python scripts/download_models.py   :: 安装 sentence-transformers
python server.py
```

---

## ✍️ 让 AI 写代码

把自然语言需求直接变成可运行的代码，也能讲解已有代码。后端优先级：
**远程大模型（Qwen-Coder 等）→ 本地 Ollama → 内置模板**（离线也能用，内置 12 个常见模板：冒泡/快速排序、二分查找、斐波那契、HTTP 服务、词频统计、文件读写、邮箱提取、网页爬虫、数组去重、SQLite 等）。

```bash
# 1) 写代码
curl -X POST http://127.0.0.1:8765/v1/code -H "Content-Type: application/json" \
  -d "{\"request\":\"用 Python 写一个冒泡排序\",\"language\":\"python\"}"

# 2) 讲解代码
curl -X POST http://127.0.0.1:8765/v1/code/explain -H "Content-Type: application/json" \
  -d "{\"code\":\"def add(a,b): return a+b\",\"language\":\"python\"}"
```

Python SDK 用法：

```python
from erbaiav_ai.sdk import AIClient
client = AIClient("http://127.0.0.1:8765")
r = client.code("用 Python 写一个冒泡排序")          # 写代码
print(r["backend"], r["code"])                     # backend=remote/local/templates
r2 = client.explain_code("def add(a,b): return a+b")  # 讲解代码
print(r2["explanation"], r2["stats"])
```

网页演示：打开 `http://127.0.0.1:8765/` 的"写代码"标签页，输入需求即可生成。

> 离线模板只能匹配内置关键词；想要**任意**代码，配置一个代码模型即可（见下文）。

---

## 📡 API 一览

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| GET | `/v1/health` | 健康检查/后端状态 | - |
| POST | `/v1/analyze/text` | 文本威胁分析 | `{"text","context"}` |
| POST | `/v1/analyze/file` | 文件/元数据分析 | `{"path"}` 或 `{"meta":{name,size,entropy,magic,md5}}` |
| POST | `/v1/chat` | AI 对话助手 | `{"text","history","system"}` |
| POST | `/v1/code` | 写代码：自然语言 → 代码 | `{"request","language"}` |
| POST | `/v1/code/explain` | 讲解一段代码 | `{"code","language"}` |
| POST | `/v1/embed` | 文本向量(BERT式) | `{"text"}` |
| POST | `/v1/search` | 语义检索 TopK | `{"query","corpus":[{"id","text"}],"top_k"}` |
| POST | `/v1/report` | 扫描报告解读 | `{"summary"}` |

| POST | `/v1/agent/run` | 编程代理：计划→读写文件→执行命令→总结 | `{"task","workspace"}` |
| POST | `/v1/agent/plan` | 编程代理：只看计划（不执行） | `{"task","workspace"}` |
| POST | `/v1/fs/list` | 列出工作区文件 | `{"path","workspace"}` |
| POST | `/v1/fs/read` | 读取工作区文件 | `{"path","workspace"}` |
| POST | `/v1/fs/write` | 写入/覆盖工作区文件 | `{"path","content","workspace"}` |
| POST | `/v1/fs/search` | 在工作区按正则搜索 | `{"pattern","workspace"}` |
| POST | `/v1/exec` | 在工作区目录执行命令 | `{"cmd","workspace","timeout"}` |
| POST | `/v1/guard/status` | 数据修改拦截：保护状态与信任区 | `{"workspace"}` |
| POST | `/v1/guard/enable` | 开启数据修改拦截（mode=block/off） | `{"workspace","mode"}` |
| POST | `/v1/guard/disable` | 关闭数据修改拦截 | `{"workspace"}` |
| POST | `/v1/guard/trust` | 信任某路径（拦截后选择信任，放行后续修改） | `{"workspace","path","reason"}` |
| POST | `/v1/guard/untrust` | 取消信任某路径 | `{"workspace","path"}` |
| POST | `/v1/guard/attempt` | 模拟程序尝试修改数据（write/delete/rename） | `{"workspace","kind","path","content","new_path","source"}` |
| POST | `/v1/guard/decide` | 处理被拦截事件（allow/block/restore） | `{"workspace","event_id","action"}` |

响应格式：`{"ok":true,"data":{...}}`；出错：`{"ok":false,"error":"..."}`（含 CORS 头，网页可直接调用）。

---

## 🛡️ 数据修改拦截（发现修改电脑数据 → 直接拦截 → 可选信任）

这是二伯杀毒的**数据保护**能力：程序尝试修改电脑数据（写入/覆盖/删除/重命名/移动）时，**直接拦截**，
自动备份原文件并生成一条待处理事件；拦截后由用户选择：

- **信任并放行（allow）**：把该路径加入信任区，并重放被拦截的修改（以后不再拦截该路径）；
- **继续拦截（block）**：拒绝该次修改，文件保持原样，备份保留；
- **回滚恢复（restore）**：从备份恢复原文件。

信任区与事件日志保存在受保护目录下的 `.erbai-guard/`（config.json / trusted.json / events.jsonl / backup/），
零依赖，重启不丢失。

```bash
# 1) 开启保护并查看状态
curl -X POST http://127.0.0.1:8765/v1/guard/enable -H "Content-Type: application/json" -d '{"workspace":"C:/demo","mode":"block"}'
curl -X POST http://127.0.0.1:8765/v1/guard/status -H "Content-Type: application/json" -d '{"workspace":"C:/demo"}'

# 2) 恶意程序尝试覆盖重要文件 -> 直接被拦截（返回 event_id，不执行修改）
curl -X POST http://127.0.0.1:8765/v1/guard/attempt -H "Content-Type: application/json" -d '{"workspace":"C:/demo","kind":"write","path":"报告.docx","content":"被篡改","source":"evil.exe"}'

# 3) 用户选择【信任并放行】或【继续拦截】或【回滚恢复】
curl -X POST http://127.0.0.1:8765/v1/guard/decide -H "Content-Type: application/json" -d '{"workspace":"C:/demo","event_id":"evt_xxx","action":"allow"}'
```

Python SDK：

```python
from erbaiav_ai.sdk import AIClient
c = AIClient("http://127.0.0.1:8765")
c.guard_enable("C:/demo", mode="block")                    # 开启保护
r = c.guard_attempt("write", "报告.docx", workspace="C:/demo",
                    content="被篡改", source="evil.exe")   # 模拟攻击 -> 被拦截
print(r["blocked"], r["event_id"])
print(c.guard_decide(r["event_id"], "allow", workspace="C:/demo"))  # 信任并放行
```

命令行（不启动服务也能用）：

```bat
cd ai-module
python -m erbaiav_ai.guard --workspace C:/demo enable
python -m erbaiav_ai.guard --workspace C:/demo attempt-write 报告.docx "被篡改" --source evil.exe
python -m erbaiav_ai.guard --workspace C:/demo events
python -m erbaiav_ai.guard --workspace C:/demo decide evt_xxx allow
```

> 说明：这是**用户态文件操作拦截**（应用层 API 级别），演示商业杀软的"数据保护/勒索防护"原理；
> 真实的底层写保护需要文件系统过滤驱动/内核回调（如 Windows 迷你过滤器），属于后续规划。

---

## 🤖 编程代理（Codex 式）

把编程任务交给代理：它像 Codex 一样 **理解任务 → 制定计划 → 读写工作区文件 → 执行命令验证 → 总结**。
默认工作区是 `ai-module/workspace/`（可用 `AI_WORKSPACE` 或请求体里的 `workspace` 指定），
所有文件读写都被限制在工作区内（防路径穿越），命令在工作区目录内执行并带超时。

```bash
# 1) 跑一个完整任务（写代码 + 运行验证）
curl -X POST http://127.0.0.1:8765/v1/agent/run -H "Content-Type: application/json" \
  -d "{\"task\":\"用 Python 写一个快速排序，保存为 main.py，然后运行验证\"}"

# 2) 只看计划，不执行
curl -X POST http://127.0.0.1:8765/v1/agent/plan -H "Content-Type: application/json" \
  -d "{\"task\":\"用 Python 写一个快速排序\"}"

# 3) 手动操作文件 / 执行命令
curl -X POST http://127.0.0.1:8765/v1/fs/list -H "Content-Type: application/json" -d "{}"
curl -X POST http://127.0.0.1:8765/v1/fs/write -H "Content-Type: application/json" \
  -d "{\"path\":\"hello.py\",\"content\":\"print('hi')\"}"
curl -X POST http://127.0.0.1:8765/v1/exec -H "Content-Type: application/json" \
  -d "{\"cmd\":\"python hello.py\"}"
```

Python SDK 用法：

```python
from erbaiav_ai.sdk import AIClient
client = AIClient("http://127.0.0.1:8765")

# 让代理完整干活
r = client.agent_run("用 Python 写一个快速排序，保存为 main.py，然后运行验证")
print(r["backend"], r["summary"])        # 后端与总结
for a in r["actions"]:                   # 每一步动作与结果
    print(a["action"], a.get("ok"), a.get("cmd") or a.get("path"))

# 代理自己不能干时，手动操作工作区
print(client.fs_list())
print(client.fs_write("hello.py", "print('hi')"))
print(client.exec_cmd("python hello.py"))
```

网页演示：打开 `http://127.0.0.1:8765/` 的 **"编程代理"** 标签页 —— 输入任务 → 开始编程 → 看计划/执行日志/文件树，还能手动读写文件、跑命令。

> 离线时代理用**规则模板**干活（生成内置模板代码并运行验证）；配置 Qwen-Coder 后，
> 代理会用大模型规划任意任务（写任何代码、改多个文件、跑测试）。

---

## 🌐 部署

- **本机**：`python server.py`（默认 127.0.0.1:8765）
- **局域网/其他机器调用**：`set AI_HOST=0.0.0.0` 后启动，防火墙放行 8765
- **Docker**：`docker compose -f docker/docker-compose.yml up -d`
- **开机自启**：用 Windows 任务计划程序运行 `python server.py`，或做成服务

---

## 🧩 目录结构

```
ai-module/
├── server.py                  # 零依赖 HTTP 服务入口
├── erbaiav_ai/
│   ├── engine.py              # 引擎：组合 规则/BERT/Qwen/Llama 后端
│   ├── codegen.py             # 代码生成/讲解（远程→本地→模板）
│   ├── agent.py               # 编程代理（Codex 式：计划→执行→验证→总结）
│   ├── fsops.py               # 安全工作区文件操作（防路径穿越）
│   ├── rules.py               # 内置规则引擎（离线兜底）
│   ├── local_backend.py       # 本地模型（BERT 句向量 / Ollama）
│   ├── remote_backend.py      # 远程 OpenAI 兼容 API（Qwen 等）
│   └── sdk.py                 # Python SDK 客户端
├── clients/
│   ├── demo_python.py         # Python 接入示例
│   ├── demo_js.js             # JS 接入示例
│   └── demo_cpp.cpp           # C++ WinHTTP 接入示例
├── web/ai-demo.html           # 网页演示（可嵌入官网）
├── docker/                    # Docker / docker-compose
├── scripts/download_models.py # 可选：装 BERT 依赖
├── workspace/               # 代理的默认工作区（自动创建，可改 AI_WORKSPACE）
└── README.md
```
