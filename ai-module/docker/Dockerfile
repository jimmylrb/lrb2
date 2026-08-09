# 二伯AI 可插拔服务 · Docker 部署
# 构建: docker build -f docker/Dockerfile -t erbaiav-ai .
# 运行: docker run -p 8765:8765 -e AI_REMOTE_KEY=sk-xxx erbaiav-ai
FROM python:3.12-slim
WORKDIR /app
COPY . /app
EXPOSE 8765
ENV AI_HOST=0.0.0.0
ENV AI_PORT=8765
CMD ["python", "server.py"]
