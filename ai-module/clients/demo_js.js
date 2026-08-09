// 浏览器 / Node.js 调用二伯AI 服务的示例
// 网页里直接 <script src="demo_js.js"></script> 或 Node 运行
const AI_BASE = "http://127.0.0.1:8765";

async function callAI(path, payload) {
  const resp = await fetch(AI_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const json = await resp.json();
  if (!json.ok) throw new Error(json.error);
  return json.data;
}

(async () => {
  // 1. 文本威胁分析
  const r1 = await callAI("/v1/analyze/text", {
    text: "紧急通知：您的账户异常，请点击链接输入密码验证，否则将被冻结！",
  });
  console.log("[分析]", r1.label, r1.confidence, r1.reasons);

  // 2. 语义检索
  const r2 = await callAI("/v1/search", {
    query: "文件被锁了，要我付比特币",
    corpus: [
      { id: 1, text: "勒索软件加密文件索要比特币" },
      { id: 2, text: "挖矿木马占用CPU挖门罗币" },
      { id: 3, text: "钓鱼邮件诱导输入密码" },
    ],
    top_k: 2,
  });
  console.log("[检索]", r2);

  // 3. AI 对话
  const r3 = await callAI("/v1/chat", { text: "你好，介绍一下你自己" });
  console.log("[对话]", r3.backend, r3.content);
})();
