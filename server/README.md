# OurPresent · server

Phase 2 服务端。FastAPI（Python 3.12）+ PostgreSQL 16 + Minio（S3 兼容）+ Nginx。

详见 [`docs/PHASE2.md`](../docs/PHASE2.md)。

## 本地启动

```bash
cd server

# 可选：复制一份环境变量样例，按需覆盖默认值
cp .env.example .env

# 生成本地 TLS 证书（需先装 mkcert）
mkcert -install
mkdir -p certs
mkcert -cert-file certs/cert.pem -key-file certs/key.pem localhost 127.0.0.1

# 启动全栈
docker compose up --build
```

健康检查：`curl -k https://localhost/healthz`

返回示例：

```json
{"status":"ok","version":"0.1.0"}
```

## 微信 / 外网穿透验证

`cloudflared` 不放进 Compose，直接在宿主机启动：

```bash
cd server
cloudflared tunnel --url https://localhost:443 --protocol http2
```

`cloudflared` 会输出一个临时 `https://<subdomain>.trycloudflare.com` 地址。拿这个地址在手机微信内置浏览器访问 `/healthz`，返回 200 即代表本地 TLS 反代和穿透链路可用。

如果当前网络环境下默认 QUIC 连 edge 超时，可改用以下命令直连 FastAPI 源站，这也是本次验收时实际跑通的路径：

```bash
cd server
cloudflared tunnel --url http://localhost:8000 --protocol http2
```

## 验收记录

2026-05-17 本地验收结果：

- `docker compose up --build -d` 成功拉起 `api / db / minio / nginx` 四个服务。
- `curl -k https://localhost/healthz` 返回 `{"status":"ok","version":"0.1.0"}`。
- `cloudflared tunnel --url http://localhost:8000 --protocol http2` 成功建立临时公网入口，公开 `/healthz` 返回 `HTTP 200`。
- API 启动日志已确认 `Database connectivity check succeeded.` 与 `Object store connectivity check succeeded.`。
- `minio-init` 初始化容器已成功创建 bucket `ourpresent`。

仍需人工验证：

- 用手机微信内置浏览器打开临时 `trycloudflare.com` 地址下的 `/healthz`，确认返回 200。

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
├── .env.example
└── pyproject.toml
```
