# Phase 2 工作文档 · 本地最小闭环

**最后更新**：2026-05-16
**性质**：Phase 2 的具体执行规划。本地优先，端到端 E2EE 在本地真机上跑通后再上云。
**前置文档**：`docs/DIRECTION.md` · `docs/E2EE.md` · `docs/ROADMAP.md`

## 战略前提

- **本地优先**：M0~M6 全部在本地 Docker Compose + 真机内网穿透完成，含真机配对 / 延时派送 / 伴侣恢复 / 口令恢复 / 销毁
- **上云 = 配置切换**：三个环境变量切换（`DATABASE_URL` / `OBJECT_STORE_ENDPOINT` / `API_BASE_URL`）+ HTTPS 证书 + 小程序合法域名白名单
- **不双形态维护**：现有 Alpha Streamlit 留在本地继续作 UX 实验台，不上云、不与新服务端共享代码
- **不与学长服务器共用**：隐私污染面 / 故障域耦合 / 备案归属问题，等本地跑通后单独要一台

## 终态架构（Phase 2 完成时的形态）

```
微信小程序 (libsodium.js)               云端 / 本地
    │                                    │
    │  HTTPS + WSS                       │
    │ ─────────────────────────────────► │
    │                                    │
    │                              ┌─────┴─────┐
    │                              │  Nginx    │
    │                              │  (TLS)    │
    │                              └─────┬─────┘
    │                                    │
    │                              ┌─────┴─────┐
    │                              │  FastAPI  │
    │                              │  (Uvicorn)│
    │                              └──┬───┬────┘
    │                                 │   │
    │                          ┌──────┘   └──────┐
    │                       ┌──┴──┐         ┌────┴────┐
    │                       │  PG │         │ OSS/Minio│
    │                       │ 16  │         │ (S3 兼容)│
    │                       └─────┘         └─────────┘
    密钥 K_couple 仅在设备                密文 BLOB + 元数据
```

服务端**永远只看到**：公钥、couple_id、时间戳、unlock_at、密文 BLOB。

## 基础设施 · 本地 vs 上云对照

| 项目 | 本地阶段 | 上云阶段 |
|------|---------|---------|
| 服务端 | Docker Compose `uvicorn` | 同 compose 文件 push 到云机 |
| DB | 同机 Docker PG 16 | 同机 Docker PG 16（同 compose） |
| 对象存储 | **Minio**（S3 协议） | 阿里 OSS / 腾讯 COS（同样 S3 协议） |
| TLS | `mkcert` 自签 + 内网穿透 | Let's Encrypt + Nginx |
| 真机联调 | `cloudflared` 临时子域名 | 备案后正式域名 |
| 小程序白名单 | 勾选"不校验合法域名" + cloudflared URL | 备案后正式域名加白 |

**关键决策**：对象存储抽象层用 S3 协议（boto3 / `aioboto3`），endpoint 切换即可在 Minio 与阿里 OSS / 腾讯 COS 之间无缝迁移。

## 技术决策（已定档）

1. **服务端**：FastAPI（Python 3.12）+ Uvicorn + asyncpg + SQLAlchemy 2
2. **DB**：PostgreSQL 16
3. **对象存储**：S3 协议抽象层（本地 Minio，上云阿里 OSS / 腾讯 COS）
4. **部署**：Docker Compose（FastAPI + PG + Minio + Nginx + Certbot）单机
5. **CI/CD**：GitHub Actions → SSH 拉镜像（上云阶段才启用）
6. **仓库结构**：mono-repo，新增 `server/` + `miniprogram/` 两个目录与现有 `backend/` `frontend/` 共存
7. **API 风格**：REST + JSON，配对推送 / 解锁推送用 WebSocket

## 里程碑 · 本地版

依赖图：

```
M0 ─┬─ M1 ─┐
    └─ M2 ─┴─ M3 ── M4 ─┬─ M5a ─┐
                       └─ M5b ─┴─ M6
```

### M0 · 启动准备

- 用户：申请小程序 AppID（接口测试号即可，免主体免备案）
- 架构师：本文档落档 + `ROADMAP.md` 改写
- 架构师：起 `server/` 与 `miniprogram/` 目录结构（先 README + 占位 compose）

**完成判据**：本文档进 master + AppID 在手

### M1 · 客户端加密 smoke test（与 M2 并行）

- 创建 `miniprogram/` 工程脚手架（微信开发者工具 + TypeScript + 分包）
- 引入 libsodium.js，在开发者工具 + iOS 微信 + Android 微信跑三组 smoke test：
  - X25519 + HKDF-SHA256 派生
  - XChaCha20-Poly1305 AEAD 加解密
  - Argon2id（t=3, m=64MB）派生耗时
- 验证 `wx.setStorage` / `wx.scanCode` / `wx.getRandomValues` 真机行为
- 测试加密栈分包加载体积与首启动延时
- 产出 `docs/research/wechat-miniprogram-crypto-verified.md` 补丁报告

**完成判据**：`docs/E2EE.md` 依赖的所有小程序能力在真机验过

### M2 · 服务端最小骨架（与 M1 并行）

- `server/` 目录起 FastAPI 项目（Poetry / uv 二选一对齐 backend/）
- `docker-compose.yml`：FastAPI + PG + Minio + Nginx
- mkcert 生成本地 TLS 证书；Nginx 反代 + 自签
- `/healthz` 健康检查端点
- `cloudflared` 配置：把 `https://<random>.trycloudflare.com` 反代到本机
- 小程序开发者工具白名单加临时域名

**完成判据**：手机微信里的 `wx.request('https://<cloudflared>/healthz')` 返回 200

### M3 · 配对协议端到端（依赖 M1 + M2）

按 `docs/E2EE.md` 第 2 节落地：

- 服务端：`POST /pairing/sessions`（10 min TTL）/ `PUT /pairing/sessions/{id}/peer` / WebSocket 推送 / `POST /pairing/complete`
- 客户端 A：临时 X25519 + IdentityKey + 二维码渲染
- 客户端 B：`wx.scanCode` → ECDH → 提交公钥
- 双方：HKDF 派 `K_couple` + 6 位 SAS 短码 UX + 当面口头核对
- 服务端：签名校验后绑定 `couple_id ↔ (A_id_pub, B_id_pub)`

**完成判据**：本地两台真机走完配对，本机 `K_couple` 一致；改服务端中转伪造公钥时短码不匹配 → 用户拒绝 → 终止

### M4 · 延时写入 + 派送门禁（依赖 M3）

- PG schema 新建（**task-21 假设作废**）：
  - `couples / users / pairing_sessions / sessions / media_objects / device_keys`
  - `sessions(id, couple_id, author_user_id, unlock_at, created_at, ciphertext_blob, aead_nonce, status)`
  - `media_objects(id, session_id, oss_key, aead_nonce, size_bytes)`
- 客户端：`K_couple` → HKDF 派子密钥 → AEAD 加密内容 / 媒体；媒体走 S3 PUT 到 Minio
- 服务端"延时派送门禁"中间件：
  - 撰写方任何时间 GET 自己内容
  - 接收方仅 `unlock_at <= now()` 时才返回 ciphertext
  - 元数据可暴露 unlock_at；禁暴露内容字段
- 工具：管理员调时钟接口（本地 only），便于把 90 天压成 5 秒回放

**完成判据**：A 写 90 天延时 → DB / Minio 抓字段全是密文 → 调时钟到点后 B 才能 GET → 解密看到原文

### M5 · 恢复机制（依赖 M4，5a / 5b 内部可并行）

- **5a 伴侣协助**：`POST /recovery/requests` + WebSocket 通知 B + 6 位短码 + 服务端中转 wrap 后的 K_couple
- **5b 用户口令**：Argon2id 派 K_backup → AEAD 加密 K_couple → `backup_blob` 上服务端 `backup` 表（本地阶段不接入 wx.cloud，等上云后再评估）

**完成判据**：M4 数据前提下，清空一方 storage → 5a 恢复成功；清空双方 storage → 5b 恢复成功

### M6 · 冻结期销毁 + 本地内测自验收（依赖 M5）

- 服务端 `POST /couple/destroy`：删 sessions / media_objects / Minio / recovery 残留
- 客户端 UI 链路：复用 Alpha 已打磨过的"冻结 → 反悔 → 销毁"双方握手映射
- 端到端自验收清单（架构师 + 用户两台真机）：
  - [ ] 配对 → 延时写入 → 解锁 → 评论 → 冻结 → 销毁 全跑通
  - [ ] PG 抽检：内容字段全部不可读
  - [ ] Minio 对象抽检：全部不可读
  - [ ] 清单方设备 storage → 5a 恢复成功
  - [ ] 清空双方 storage → 5b 恢复成功
  - [ ] 销毁后 PG + Minio 无残留

**完成判据**：上面 6 条全过 → Phase 2 本地阶段关闭 → 进入上云切换

## 上云切换（M6 完成后，备案下来后）

预计工作量 ≤ 1 天，纯配置切换：

1. 申请独立云服务器（不与学长共用）
2. 域名 DNS 指向云机
3. 同 `docker-compose.yml` 在云机起，环境变量切换：
   - `DATABASE_URL`：本地 → 云机 PG
   - `OBJECT_STORE_ENDPOINT`：Minio → 阿里 OSS / 腾讯 COS（S3 协议层不变）
   - `API_BASE_URL`：cloudflared → 正式域名
4. Let's Encrypt + Certbot 自动续签
5. 小程序"request 合法域名"换成正式域名
6. 真机回归 M6 自验收清单

上云完成后 → Phase 3 招测试者

## Phase 2 不做的事

- 不上云 Streamlit
- 不接 AI
- 不做多设备同步
- 不做完整监控告警
- 不做账号密码找回（K_couple 恢复是另一回事）
- 不引入 K8s / 服务网格

## 维护约定

- 本文档随里程碑推进更新（顶部带日期）
- 每个里程碑产出独立任务卡到 `docs/tasks/`
- 完成里程碑后在本文档「里程碑」节标 ✓ + 一句话总结
