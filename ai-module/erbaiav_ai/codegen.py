# -*- coding: utf-8 -*-
'''代码生成模块：把自然语言需求变成代码。

后端优先级：
  1. 远程大模型（Qwen-Coder / DeepSeek-Coder 等，OpenAI 兼容）
  2. 本地 Ollama 代码模型（qwen2.5-coder 等）
  3. 内置代码模板引擎（离线兜底，覆盖常见算法/脚本）
'''
import re

from . import local_backend
from . import remote_backend

CODE_SYSTEM = (
    '你是一个专业的编程助手。请根据用户需求直接输出完整、可运行的代码，'
    '包含必要的注释。语言以用户指定为准；未指定则选择最合适的语言。'
)

EXPLAIN_SYSTEM = '你是一名耐心的编程老师，请用中文清晰地解释代码的作用、关键逻辑和注意事项。'

TEMPLATES = [
    {
        'name': 'Python 冒泡排序',
        'lang': 'python',
        'keys': ['冒泡', 'bubble sort', 'bubblesort'],
        'desc': '经典排序算法（O(n^2)）',
        'code': r'''def bubble_sort(arr):
    # 冒泡排序：重复遍历，把大的元素逐步交换到末尾
    n = len(arr)
    for i in range(n - 1):
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

if __name__ == '__main__':
    data = [5, 2, 9, 1, 7, 6]
    print('排序前:', data)
    print('排序后:', bubble_sort(data))''',
    },
    {
        'name': 'Python 快速排序',
        'lang': 'python',
        'keys': ['快速排序', '快排', 'quicksort', '排序'],
        'desc': '分治排序算法（平均 O(n log n)）',
        'code': r'''def quick_sort(arr):
    # 快速排序：选定基准，分治递归
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    mid = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + mid + quick_sort(right)

if __name__ == '__main__':
    print(quick_sort([3, 6, 8, 10, 1, 2, 1]))''',
    },
    {
        'name': 'Python 二分查找',
        'lang': 'python',
        'keys': ['二分', 'binary search', 'binary_search'],
        'desc': '在有序数组中快速定位（O(log n)）',
        'code': r'''def binary_search(arr, target):
    # 二分查找：要求 arr 已升序排列，返回下标或 -1
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

if __name__ == '__main__':
    print(binary_search([1, 3, 5, 7, 9, 11], 7))  # 3''',
    },
    {
        'name': 'Python 斐波那契数列',
        'lang': 'python',
        'keys': ['斐波那契', 'fibonacci', 'fib'],
        'desc': '迭代方式生成斐波那契数列',
        'code': r'''def fibonacci(n):
    # 斐波那契数列：f(0)=0, f(1)=1
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

if __name__ == '__main__':
    print([fibonacci(i) for i in range(10)])  # 前 10 项''',
    },
    {
        'name': 'Python HTTP 服务',
        'lang': 'python',
        'keys': ['http', '服务器', '服务', '端口', 'server'],
        'desc': '用标准库起一个 HTTP 服务（无需装框架）',
        'code': r'''from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class ApiHandler(BaseHTTPRequestHandler):
    # 极简 HTTP 服务：GET /ping 返回 JSON
    def do_GET(self):
        if self.path == '/ping':
            body = json.dumps({'ok': True, 'msg': 'pong'}, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8000), ApiHandler)
    print('服务已启动: http://127.0.0.1:8000/ping')
    server.serve_forever()''',
    },
    {
        'name': 'Python 单词频率统计',
        'lang': 'python',
        'keys': ['单词', '词频', '统计', 'word'],
        'desc': '统计文本中每个单词的出现次数',
        'code': r'''from collections import Counter
import re


def word_freq(text):
    # 统计文本中每个单词的出现次数（不区分大小写）
    words = re.findall(r'[A-Za-z]+', text.lower())
    return Counter(words)


if __name__ == '__main__':
    sample = 'hello world hello python world world'
    print(word_freq(sample))''',
    },
    {
        'name': 'Python 文件读写',
        'lang': 'python',
        'keys': ['文件', '读写', '读取', 'file'],
        'desc': '读取/写入 UTF-8 文本文件',
        'code': r'''def read_file(path):
    # 读取文本文件（UTF-8）
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path, content):
    # 写入文本文件（UTF-8）
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


if __name__ == '__main__':
    write_file('demo.txt', '你好，AI！')
    print(read_file('demo.txt'))''',
    },
    {
        'name': 'Python 提取邮箱地址',
        'lang': 'python',
        'keys': ['邮箱', 'email', '正则'],
        'desc': '用正则从文本中提取邮箱',
        'code': r'''import re

EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'


def extract_emails(text):
    # 从文本中提取所有邮箱地址
    return re.findall(EMAIL_PATTERN, text)


if __name__ == '__main__':
    sample = '联系我: tom@example.com 或 jerry@test.org.cn'
    print(extract_emails(sample))''',
    },
    {
        'name': 'Python 网页爬虫',
        'lang': 'python',
        'keys': ['爬虫', '抓取', 'crawler', 'scraper'],
        'desc': '抓取网页标题（需要 requests + beautifulsoup4）',
        'code': r'''import requests
from bs4 import BeautifulSoup  # 需要: pip install requests beautifulsoup4


def fetch_title(url):
    # 抓取网页并返回标题
    resp = requests.get(url, timeout=10)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, 'html.parser')
    return soup.title.string.strip() if soup.title else '无标题'


if __name__ == '__main__':
    print(fetch_title('https://example.com'))''',
    },
    {
        'name': 'JavaScript 数组去重',
        'lang': 'javascript',
        'keys': ['去重', '数组', 'unique', 'javascript', 'js'],
        'desc': '用 Set 去重并保留顺序',
        'code': r'''// 数组去重（保留首次出现顺序）
function unique(arr) {
  return [...new Set(arr)];
}

// 用法示例
console.log(unique([1, 2, 2, 3, 1, 4])); // [1, 2, 3, 4]''',
    },
    {
        'name': 'JavaScript 防抖函数',
        'lang': 'javascript',
        'keys': ['防抖', '节流', 'debounce', 'throttle'],
        'desc': '连续触发时只在停止后执行一次',
        'code': r'''// 防抖：连续触发时只在停止后执行一次
function debounce(fn, delay = 300) {
  let timer = null;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

// 用法示例：窗口缩放时只打印一次
window.addEventListener('resize', debounce(() => console.log('resized'), 500));''',
    },
    {
        'name': 'Python SQLite 存储',
        'lang': 'python',
        'keys': ['sqlite', '数据库', 'database'],
        'desc': '用标准库 sqlite3 建表并插入数据',
        'code': r'''import sqlite3


def init_db(path='app.db'):
    # 创建用户表
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)')
    conn.commit()
    return conn


def add_user(conn, name):
    conn.execute('INSERT INTO users (name) VALUES (?)', (name,))
    conn.commit()


if __name__ == '__main__':
    conn = init_db()
    add_user(conn, 'Alice')
    for row in conn.execute('SELECT * FROM users'):
        print(row)''',
    },
]


def _detect_lang(req):
    low = (req or '').lower()
    if 'python' in low or '.py' in low:
        return 'python'
    if 'javascript' in low or 'js' in low or '前端' in req:
        return 'javascript'
    if 'c++' in low or 'cpp' in low or 'c语言' in req:
        return 'cpp'
    if 'java' in low:
        return 'java'
    if 'html' in low or '网页' in req:
        return 'html'
    return 'python'


def _score(req, keys):
    low = req.lower()
    return sum(1 for k in keys if k.lower() in low)


def _best_template(req):
    best, best_score = None, 0
    for t in TEMPLATES:
        sc = _score(req, t['keys'])
        if sc > best_score:
            best, best_score = t, sc
    return best, best_score


def _stats(code):
    lines = [ln for ln in code.splitlines() if ln.strip()]
    funcs = re.findall(r'^\s*(?:def|function)\s+([A-Za-z_][A-Za-z0-9_]*)', code, re.M)
    imports = re.findall(r'^\s*(?:import|from)\s+([A-Za-z0-9_\.]+)', code, re.M)
    return {
        'lines': len(lines),
        'functions': funcs[:10],
        'imports': list(dict.fromkeys(imports))[:10],
    }


def _basic_explain(code):
    st = _stats(code)
    parts = ['（本地规则模式简要分析）']
    if st['functions']:
        parts.append('包含函数: ' + ', '.join(st['functions']))
    if st['imports']:
        parts.append('引用模块: ' + ', '.join(st['imports']))
    parts.append('共 %d 行代码' % st['lines'])
    parts.append('配置 AI_REMOTE_KEY（Qwen-Coder）可让大模型逐行详细讲解。')
    return '；'.join(parts)


def list_templates():
    return '、'.join(t['name'] for t in TEMPLATES)


def generate(request, language=None):
    '''把自然语言需求变成代码（远程 -> 本地 -> 模板兜底）。'''
    request = (request or '').strip()
    if not request:
        return {
            'backend': 'templates', 'language': language or 'python',
            'code': '# 请输入你的需求，例如：用 Python 写一个冒泡排序',
            'name': '空需求', 'desc': '请描述你想让 AI 写的代码',
        }
    prompt = '需求：' + request
    if language:
        prompt += '\n语言：' + language

    # 1) 远程大模型（Qwen-Coder / DeepSeek-Coder 等）
    if remote_backend.configured():
        out = remote_backend.chat(
            [{'role': 'user', 'content': prompt}],
            system=CODE_SYSTEM, temperature=0.3, max_tokens=2048)
        if out and not out.startswith('['):
            return {
                'backend': 'remote', 'language': language or _detect_lang(request),
                'code': out, 'model': remote_backend.model_name(),
            }

    # 2) 本地 Ollama 代码模型
    out = local_backend.chat([{'role': 'user', 'content': prompt}], system=CODE_SYSTEM)
    if out:
        return {
            'backend': 'local', 'language': language or _detect_lang(request),
            'code': out, 'model': local_backend.OLLAMA_MODEL,
        }

    # 3) 内置模板兜底
    t, score = _best_template(request)
    if t and score > 0:
        return {
            'backend': 'templates', 'language': t['lang'], 'name': t['name'],
            'desc': t['desc'], 'code': t['code'],
            'note': '内置模板模式：设置 AI_REMOTE_KEY 或本地 Ollama 代码模型可写任意代码。',
        }
    return {
        'backend': 'templates', 'language': language or _detect_lang(request),
        'code': ('# 未匹配到内置模板\n# 可用模板：' + list_templates()
                 + '\n# 设置 AI_REMOTE_KEY 可让 Qwen-Coder 等大模型写任意代码'),
        'name': '未匹配', 'desc': '试试内置模板关键词，或配置大模型',
    }


def explain(code_text, language=None):
    '''讲解一段代码（远程 -> 本地 -> 规则兜底）。'''
    code_text = code_text or ''
    if not code_text.strip():
        return {'backend': 'rules', 'explanation': '（空代码，没有可解释的内容）',
                'stats': _stats(code_text)}
    prompt = '请用中文解释下面代码的作用、关键逻辑和注意事项：\n```\n' + code_text + '\n```'
    if remote_backend.configured():
        out = remote_backend.chat([{'role': 'user', 'content': prompt}],
                                  system=EXPLAIN_SYSTEM, temperature=0.3, max_tokens=800)
        if out and not out.startswith('['):
            return {'backend': 'remote', 'explanation': out, 'stats': _stats(code_text)}
    out = local_backend.chat([{'role': 'user', 'content': prompt}], system=EXPLAIN_SYSTEM)
    if out:
        return {'backend': 'local', 'explanation': out, 'stats': _stats(code_text)}
    return {'backend': 'rules', 'explanation': _basic_explain(code_text),
            'stats': _stats(code_text)}
