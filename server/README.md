# OurPresent · server

Phase 2 服务端。FastAPI（Python 3.12）+ PostgreSQL 16 + Minio（S3 兼容）+ Nginx。

**现状**：M0 骨架，M2 实现工将在此目录补全。

详见 [`docs/PHASE2.md`](../docs/PHASE2.md)。

## 快速启动（M2 完成后有效）

```bash
# 生成本地 TLS 证书（需先装 mkcert）
mkcert -install
mkcert -cert-file certs/cert.pem -key-file certs/key.pem localhost 127.0.0.1

# 启动全栈
docker compose up --build
```

健康检查：`curl -k https://localhost/healthz`

## 目录结构

```
server/
├── app/            # FastAPI 应用
│   └── main.py
├── nginx/          # Nginx 配置
│   └── nginx.conf
├── certs/          # mkcert 本地证书（gitignore）
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```
