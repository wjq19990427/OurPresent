# Task 21: PostgreSQL 迁移 · Docker Compose · 保留整库语义

> **冻结 2026-05-13**：项目战略转向商业化 + 端到端加密（详见 `docs/DIRECTION.md`）。本任务卡的核心前提"整库明文 load_db/save_db 不变、application 零感知"与 E2EE 下"服务端只持有密文 + 元数据索引"的最终形态不兼容。在 E2EE 架构决策出来之前，本卡不要开工；届时大概率要重写而非沿用。

**类型**：infra（数据库介质迁移）
**Branch**：`codex/task-21`
**前置任务**：task-20（合成剧本作为跨 DB 一致性验收基线）

## 背景

当前持久化是单文件 SQLite (`data/database.db`)，配合 `load_db() / save_db()` 整库 dict 编程模型。这套形态适合本地 Demo 但不可部署到多实例环境。

本任务把介质换成 PostgreSQL，配合本地 Docker Compose 提供数据库服务，**为后续 task-22 FastAPI 包装、生产化部署铺路**。

明确的取舍：本任务**只换介质**，**不**改业务编程模型。`load_db() / save_db()` 整库语义保留，application / domain / frontend / synth 全部零感知。性能层面的行级并发优化、连接池调参等留到独立 task。一次只做一件事。

## 目标

1. 提供 `docker-compose.yml` 在本地拉起 PostgreSQL（pin 一个明确大版本，建议 16.x）
2. `backend/infrastructure/database/` 后端切换：`load_db()` 从 PG 读、`save_db()` 整库 upsert 到 PG，**保留返回值 / 入参 / 异常 / 时间字符串格式契约**
3. 新增启动期连接校验（参考 task-15 对 `DEEPSEEK_BASE_URL` 的 https 校验风格）
4. 现有 71+ pytest **全绿**（fixture 改造，业务断言不动）
5. task-20 合成剧本在 PG 上回放产出**与 SQLite 等价**的逻辑状态（visibility / counts / comments / dissolved 等关键维度对齐）
6. 同步清理 task-20 四条遗留（详见下文「顺手处理」）

## 改动范围

**许动**：

- `docker-compose.yml`（新增项目根；至少一个 `postgres` service + named volume + 健康检查）
- `backend/infrastructure/database/db.py`：底层介质切换；`EMPTY_DB / now_str / parse_dt / load_db / save_db / ensure_dirs` 签名与语义不变
- `backend/infrastructure/database/*_repo.py`：如内部直接持有 SQLite 连接的逻辑需迁移，签名与返回值不变
- `backend/config/settings.py`：新增 `DATABASE_URL`（或拆分字段）配置项 + 启动期校验
- `backend/tests/conftest.py` / fixtures：把测试库从临时 SQLite 文件迁到测试 PG schema（或独立 db），保证测试隔离
- `pyproject.toml` / `uv.lock`：引入 PG 驱动（驱动选型由实现工评估，但**禁止引 ORM**，保持当前 raw SQL 风格）
- `.env` / `.env.example`：新增 `DATABASE_URL`；同步补 task-20 漏掉的 `SYNTH_ASSETS_ROOT` 占位 + 注释
- `tools/synth/driver.py`：把 `SYNTH_DB_PATH` 路径语义升级为「合成专属 PG schema 或独立 db」—— 具体形态由实现工评估（共享 PG 实例 + 隔离 schema vs 独立 PG service）
- `docs/ARCHITECTURE.md`：第 1 节技术栈 + 第 2 节目录结构 + 第 4 节关键设计决策同步
- `docs/api/infra_db.md`：L2 契约更新（介质切换 + 启动期校验 + 测试 fixture 形态）
- `README.md`：顶层目录变化（docker-compose.yml）+ 协作工作流（如何拉起本地 PG）小段
- `docs/STATUS.md` / `CHANGELOG.md`：任务完成后由架构师同步

**不许动**：

- `backend/application/**`（任何业务逻辑改动开新 task）
- `backend/domain/**`
- `frontend/**`
- `tools/synth/**` 除 `driver.py` 必要适配外不动剧本生成器
- `backend/tests/test_*.py` 测试断言本体（只能改 fixture / conftest / 数据库引导逻辑）
- 任何 `load_db() / save_db()` 调用方的代码（包括 `application/maintenance/ticking.py` 的整库扫描）

## 关键约束

- **接口契约硬约束**：`load_db()` 返回的字典结构 / 字段命名 / 时间字符串格式 (`%Y-%m-%d %H:%M:%S`) 必须与 SQLite 实现逐字段对齐。`bcrypt` hash 字段、JSON 序列化字段（如 `comments_json`）的存储形态在 PG 端用什么类型由实现工决定，但反序列化后给到 application 层的形态不变
- **整库 dict 模型保留**：禁止把 `save_db()` 拆成 per-row UPSERT 暴露给 application；continue to 写整库快照。性能问题留给下一 task
- **启动期连接校验**：缺 `DATABASE_URL` / 连接拒绝 / schema 不存在 → 抛错并终止进程（不静默 fallback 到 SQLite）。错误信息**不**回显环境变量原文，避免污染日志（参考 task-15 风格）
- **Docker Compose 边界**：本任务只提供 PG 服务，**不**容器化 Streamlit。app 仍在本地 `uv run streamlit run main.py`，通过 `localhost:5432` 连容器内 PG
- **测试隔离**：测试 PG 必须与开发 PG 物理隔离（独立 db 或独立 schema）。CI 友好（实现工评估 GitHub Actions service container 形态，但任务卡不强制）
- **task-20 回放等价验收**：把 task-20 合成剧本跑两次 ——
  1. 在 SQLite 上跑一次，记录 `summarize_sqlite()` 输出
  2. 在 PG 上跑一次，用等价 SQL 抽出同样字段
  3. 两份输出在 key 集合 / counts / dissolved 等可观测维度等价（时间戳容差除外）
- **schema 迁移**：当前 SQLite 启动迁移逻辑（`load_db` 内的 `_migrate_db` 累积补字段）必须在 PG 端等价存在 —— 要么一次性 DDL 把累积结果一把建表，要么保留增量迁移。具体形态由实现工选

## 顺手清理 task-20 四条遗留

下列四条来自 task-20 review，搭车本次迁移一并处理（不开独立 task）：

1. **synth 合成补 `save_session_pending` 路径**：当前所有合成 session 走 `save_session_final`。补一条剧本分支或一个测试，让 `save_session_pending → move_to_final` 路径在合成期被实际执行
2. **`SynthClock` 类型守卫**：在 `tools/synth/driver.py` 的 `SynthClock` 加注释说明「仅 stub `.now()/now_str()`，依赖 backend 当前 datetime 用法」；或者改成继承 `datetime` 让属性访问 fallback 到真 datetime。二选一，写明选择理由
3. **销毁链补 `confirm_uncouple`**：synth driver 的 `destroy_actions` 处理从「`start_uncouple` + `destroy_couple_data` 直连」改为「`start_uncouple` + `confirm_uncouple` + 等价时间推进 + `destroy_couple_data`」，让完整业务链路被实跑
4. **`SYNTH_ASSETS_ROOT` 占位**：`.env.example` 加 `SYNTH_ASSETS_ROOT=` 占位 + 一行注释说明用途

## 验收

- `docker compose up -d` 启动 PG，`uv run streamlit run main.py` 应用正常启动并完成首次 `load_db()`
- `uv run pytest backend/` 全绿
- task-20 跨 DB 一致性验收脚本（实现工自决形态，可以是新 pytest 也可以是 README 步骤）输出等价
- 误删 `DATABASE_URL` env → 启动即报错退出，不静默 fallback
- `docs/api/infra_db.md` 反映新形态，与代码一致
- 任务卡顺手清理四条全部完成

## 不在本任务范围

- FastAPI 包装（task-22）
- `load_db()/save_db()` 整库模型改行级（独立后续 task）
- Streamlit 容器化（独立后续 task）
- 连接池调参、读写分离、replica（独立后续 task）
- 数据迁移工具（当前 SQLite 库内只有测试数据，task-20 合成可重生，**不**做 SQLite → PG 数据搬运）
