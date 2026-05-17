# task-28 · M2：服务端本地 Docker Compose 骨架

## 变更说明

**类型**：新功能

搭建本地 FastAPI 服务端环境——用户（或架构师）在本机一条命令启动 FastAPI + PostgreSQL + Minio + Nginx，并能通过手机微信访问 `https://<cloudflared 子域>/healthz` 得到 `{"status": "ok"}`。这是 Phase 2 后续所有里程碑的服务端基础。

---

## 前置条件

- `server/` 骨架已在 M0 就位（README / docker-compose.yml / Dockerfile / app/main.py）
- 本机需已安装：Docker Desktop · mkcert · cloudflared

## 工作范围

涉及目录：`server/`

**`server/app/main.py`**：补全为可启动的 FastAPI 应用，至少包含：
- `GET /healthz` → `{"status": "ok", "version": "0.1.0"}`
- 启动时日志确认 DB / Minio 连接（连不上只 warn，不 crash）

**`server/docker-compose.yml`**：已有占位骨架，实现工对照以下约束补全：
- FastAPI 容器等 PG 健康检查通过后再启动（已有 healthcheck 骨架）
- Minio 首次启动后需创建 bucket `ourpresent`（entrypoint 脚本或 mc 初始化容器）
- 四个服务名：`api / db / minio / nginx`，保持不变

**`server/nginx/nginx.conf`**：已有占位，补全为：
- 80 → 301 跳 443
- 443 代理到 `api:8000`；`/ws` 路径升级 WebSocket（已有骨架）
- 证书路径 `/etc/nginx/certs/cert.pem` / `key.pem`（已固定）

**`server/Dockerfile`**：已有占位，补全为可正常 build 的镜像（uv sync + uvicorn 启动）

**`server/.env.example`**：新建示例环境变量文件，含：
- `DATABASE_URL` / `OBJECT_STORE_ENDPOINT` / `OBJECT_STORE_ACCESS_KEY` / `OBJECT_STORE_SECRET_KEY`

**`server/.gitignore`**：新建，忽略 `certs/` / `.env` / `__pycache__/` / `.venv/`

## 不做的事

- 不建 PG schema（M4 再做）
- 不实现任何业务 API（只有 `/healthz`）
- 不集成 cloudflared 到 compose（cloudflared 在本机外层跑，命令行文档写进 README 即可）
- 不写单元测试（/healthz 太简单，留到 M3）

## 验收

- [ ] `docker compose up --build`（在 `server/` 目录）无错误启动全部 4 个服务
- [ ] `curl -k https://localhost/healthz` 返回 `{"status": "ok", ...}`
- [ ] `cloudflared tunnel --url https://localhost:443`（或 `http://localhost:8000`）拿到临时子域名
- [ ] 手机微信内置浏览器访问 `https://<子域名>/healthz` 返回 200（证明穿透成功）
- [ ] `server/README.md` 补充本地启动步骤（mkcert 命令 + compose + cloudflared）

## 并行约束

- **Wave 1**（与 task-27 并行）：核心文件不重叠（server/ vs miniprogram/）
- 依赖 task-27 完成才能进入 M3
