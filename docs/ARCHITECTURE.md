# OurPresent 架构索引（L1）

本文档是项目架构总入口与模块索引，回答两个问题：

1. **项目长什么样**：技术栈、目录结构、依赖方向、关键设计决策
2. **想了解某模块细节去哪里读**：每份 L2 契约（`docs/api/*.md`）的覆盖范围

> 改动公开签名或语义时，必须先读对应 L2 契约，并在改完后同步更新该 L2 文档。

## 1. 技术栈

- 前端：Streamlit
- 业务层：本地 Python 模块（`backend/`）
- 数据层：`data/database.db`（SQLite）
- 文件存储：`Assets/Pending/` 与 `Assets/Final/`
- 依赖管理：`uv`
- 测试与风格：`pytest`（`backend/tests/`）、`ruff`

## 2. 目录结构

```text
backend/
├── api/
├── application/
│   ├── auth/
│   ├── couples/
│   ├── maintenance/
│   └── sessions/
├── config/
├── domain/
│   └── models/
└── infrastructure/
    ├── ai/
    ├── database/
    └── media/

frontend/
└── streamlit_app/
    ├── components.py
    └── pages/
```

## 3. 分层依赖

```text
backend/config/settings
    ↓
backend/domain/models
    ↓
backend/infrastructure/database/*_repo
    ↓
backend/application/*
    ↓
frontend/streamlit_app/*
    ↓
main.py
```

**约束**：

- 上层只依赖下层，禁止循环依赖
- `frontend` 优先走 `application`；仅查询型读取允许直连 `infrastructure`
- `application` 不直接读写与 session 无关的文件系统数据；持久化统一过 `infrastructure`

## 4. 关键设计决策（不变量）

- **整库 dict 编程模型**：`load_db()/save_db()` 一次性读写整库，业务层操作内存字典。底层介质已切到 SQLite，但保留接口语义以避免大面积改动。多实例并发场景需另设方案。
- **dataclass + repository 已落地边界**：auth、couples、session 创建链路使用 `User/Couple/SessionRecord/AuthToken`；session UI 仍部分以 dict 流转，是有意保留以降低重构风险。
- **`tick()` 跨表推进**：时间锁推进、冻结期销毁、token 过期清理天然跨 `sessions/couples/auth_tokens`，因此归 `application/maintenance` 而非任一子域。
- **`destroy_couple_data()` 跨表协调**：销毁逻辑跨多张表，由 `application` 层用例协调，不下放到 repository。
- **时间锁基准**：90 天等待基于 `upload_time` 而非 `unlock_requested_at`，无法通过提前申请绕过。

## 5. L2 契约目录

每份 L2 文档描述对应代码模块的公开签名、行为、副作用与约束。改动这些模块前必读。

| 文档 | 覆盖代码 | 用途 |
|------|----------|------|
| [`api/main.md`](./api/main.md) | `main.py` | 应用入口、`st.session_state` 关键键、启动序列 |
| [`api/config.md`](./api/config.md) | `backend/config/settings.py` | 路径常量、`FIELD_SCHEMA`、token 过期常量 |
| [`api/domain_models.md`](./api/domain_models.md) | `backend/domain/models/*` | `User` / `Couple` / `SessionRecord` / `AuthToken` |
| [`api/infra_db.md`](./api/infra_db.md) | `backend/infrastructure/database/*` | `db.py` + 四份 `*_repo.py` |
| [`api/infra_media.md`](./api/infra_media.md) | `backend/infrastructure/media/thumbnails.py` | 视频缩略图、PIL 转换 |
| [`api/infra_ai.md`](./api/infra_ai.md) | `backend/infrastructure/ai/agent_skills.py` | RAG 接口预留（占位实现） |
| [`api/app_auth.md`](./api/app_auth.md) | `backend/application/auth/*` | 注册 / 登录 / token 用例 |
| [`api/app_couple.md`](./api/app_couple.md) | `backend/application/couples/*` | 绑定 / 解绑 / 冻结期 |
| [`api/app_sessions.md`](./api/app_sessions.md) | `backend/application/sessions/*` | 创建 / 编辑 / 共享 / 评论 / 导出 / 销毁 |
| [`api/app_maintenance.md`](./api/app_maintenance.md) | `backend/application/maintenance/ticking.py` | `tick()` / `load_db_with_tick()` |
| [`api/frontend_streamlit.md`](./api/frontend_streamlit.md) | `frontend/streamlit_app/*` | 页面 / 组件 / 详情渲染 |

## 6. 阅读路径

- **新人接手**：本文 → `docs/PRD.md` → 想改的模块对应 `docs/api/*.md`
- **改字段或存储结构**：`docs/data-model.md` + `api/domain_models.md` + `api/infra_db.md`
- **改时间锁或解绑逻辑**：`docs/state-machines.md` + `api/app_couple.md` + `api/app_maintenance.md`
- **接入新存储后端 / 第二阶段 AI**：`docs/extension-guide.md`
- **首次使用产品**：`docs/user-guide.md`
