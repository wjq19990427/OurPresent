# Task 20: AI 合成数据 workflow MVP（角色卡 + 时间线 + 延时行为）

**类型**：feature（开发期工具）
**Branch**：`codex/task-20`
**前置任务**：无（独立工具链，不依赖业务代码改动）

## 背景

项目语义涉及私人隐私，不能用真实用户数据驱动测试、回归与未来 PG 迁移。需要一条 AI 驱动的合成数据生产线：从虚构情侣角色出发，生成一段时间内完整的「记录—延时表达—解锁/调整/销毁」行为流水，落到独立 DB 用于后续 FastAPI 包装、PG 迁移的端到端基线。

合成工具是**开发期工具**，不是 backend 业务功能，不进入 `backend/`，不被 `frontend/` 依赖，不参与生产逻辑分层。

## 目标

1. 新增独立顶层目录 `tools/synth/`，与 `backend/` / `frontend/` 平级
2. 接入 MiniMax-M2.5（用户提供的 coding plan token），独立 LLM 客户端，**不复用** `backend/infrastructure/ai/llm_client.py`
3. 实现「角色卡 → 时间线 → 延时表达行为」三层语义的合成流水
4. 合成产物必须**经过 `backend/application/` 公开入口落库**，不直接调 repository / 不直接写 SQLite
5. 通过环境变量 `SYNTH_DB_PATH` 强制 DB 隔离，**未设置或指向 `data/database.db` 时必须拒绝运行**
6. 中间产物是人可读的剧本 JSON，支持「不调 LLM 纯重放」二次跑

## 三层语义（核心约束）

合成不是「随便造点数据」，必须按下列三层结构展开，缺一不算完成：

### 1. 角色卡（Persona）

- 一对情侣 = 两份独立角色卡
- 至少覆盖：性格基调 / 沟通风格 / 关系阶段（热恋 / 平稳 / 摩擦 / 冷淡）/ 当前情感锚点（近期共同事件、各自关注的议题）
- 角色卡是剧本的**输入种子**，由人工或 LLM 起草，落到磁盘 JSON 后可复用

### 2. 时间线（Timeline）

- 在角色卡基础上，由 LLM 展开 N 周（默认 4–12 周，可配置）的事件序列
- 每条 event 至少包含：日期、所属用户视角（A / B / 共同）、事件主题、双方各自的真实感受文本
- 时间线必须双视角对齐：同一事件可以有 A、B 各自的内心独白，不能合并成单一第三人称叙述

### 3. 延时表达行为（Delayed-share actions）—— 项目灵魂特性，必须重点覆盖

每条 event 对应一条或多条 session 行为，**必须覆盖以下分布**（不要全是简单路径）：

- `private` 永久私密（用户写了不打算共享）
- `pending_unlock` + `unlock_at` 自选（≥ 1 小时、≥ 1 天、≥ 1 周、≥ 1 月 各有样本）
- `pending_unlock` 中途**调整 `unlock_at`**（推后 / 提前）
- `pending_unlock` **立即解锁**（`share_now` 路径）
- 共享后被另一方读取 → 触发情感互动（落到下一条 event 的种子）
- 冻结期销毁分支（至少 1 对样本走完 `destroy_couple_data` 完整链路）

未覆盖到的分支需在剧本 JSON 显式标 `skipped` 并写明原因，不能默默漏。

## 改动范围

**许动**：

- `tools/synth/`（全新目录）
- `tools/synth/personas/`（示例角色卡 JSON，可入库 1–2 对作为开箱即用样例）
- `tools/synth/scripts/`（剧本 JSON 落盘目录；建议加入 `.gitignore` 子项，避免污染仓库）
- `tools/synth/minimax_client.py`：Minimax 客户端封装
- `tools/synth/persona.py` / `tools/synth/timeline.py` / `tools/synth/actions.py`：三层语义生成器
- `tools/synth/driver.py`：把剧本写入 DB 的执行器，**只调 `backend/application/` 公开函数**
- `tools/synth/cli.py` 或 `tools/synth/run_synth.py`：命令行入口
- `tools/synth/replay.py`：从已存剧本 JSON 重放（不调 LLM）
- `tools/synth/README.md`：使用说明（如何起种子、如何跑、如何重放、如何重置 SYNTH_DB）
- `.env` / `.env.example`：新增 `MINIMAX_API_KEY` / `MINIMAX_BASE_URL` / `MINIMAX_MODEL` / `SYNTH_DB_PATH`（架构师已加，确认即可）
- `.gitignore`：追加 `tools/synth/scripts/*.json`、`tools/synth/.synth_db/*`
- `pyproject.toml` / `uv.lock`：按需引入 Minimax HTTP 客户端依赖（推荐复用 `httpx`，不引新栈）
- 顶层 `docs/ARCHITECTURE.md`：第 2 节目录结构追加 `tools/synth/` 说明（1–2 行）
- `docs/STATUS.md`：完成后由架构师更新

**不许动**：

- `backend/**` 任何业务代码（synth 是工具不是 backend feature；如发现 application 公开入口不够用，开新 task，不要顺手改）
- `backend/tests/**`（synth 自己的测试放 `tools/synth/tests/`）
- `frontend/**`
- `data/database.db`、`Assets/Final/`、`Assets/Pending/`（合成必须走 `SYNTH_DB_PATH` 指向的独立路径与独立 Assets 根）

## 关键约束

- **DB 隔离硬约束**：driver 启动时必须断言 `SYNTH_DB_PATH` 已设置、不等于生产路径、父目录可写；任一不满足直接 `raise` 终止
- **Assets 路径隔离**：合成产生的文件不能写入项目根 `Assets/`，由 driver 注入独立 Assets 根（具体怎么注入由实现工评估：env 覆盖 vs settings monkey-patch 二选一，但**写在 README 里**说清楚选了哪个、为什么）
- **必经 application 层**：session 创建走 `save_session_pending` / `save_session_final`、共享走 `request_unlock` / `share_now`、销毁走 `destroy_couple_data`；不允许 `import` 任何 `backend.infrastructure.*` 直接写库
- **Minimax 客户端启动期校验**：缺 key、`MINIMAX_BASE_URL` scheme 非 https、`MINIMAX_MODEL` 未设置 → 抛错（参考 task-15 对 DeepSeek 的处理）
- **剧本可重放**：LLM 输出落盘后，`replay.py` 不再调 LLM，仅按剧本回放写 DB。剧本格式自定义，但要支持二次跑出**字节级一致**的 DB 状态（除时间戳容差外）
- **模型固定**：`MINIMAX_MODEL=MiniMax-M2.5`（架构师已写入 `.env`），不要在代码里硬编码 model id，统一从环境变量读
- **不污染生产 settings**：Minimax 相关 env 读取只发生在 `tools/synth/` 内部，不进 `backend/config/settings.py`

## 验收

实现工完工时，下列行为可被人工或脚本观测：

- 给定一对角色卡 JSON，跑一次 `run_synth.py`，产出至少一份剧本 JSON + 一个写满数据的独立 SQLite 文件
- 该 SQLite 中可观察到上述「延时表达行为分布」全部六类分支至少各一条
- 同一份剧本 JSON 用 `replay.py` 跑两次，最终 DB 状态等价（除时间戳）
- 误把 `SYNTH_DB_PATH` 指向 `data/database.db`，driver 立刻报错退出，没有任何写入发生
- `tools/synth/README.md` 有人能看懂怎么起种子、怎么跑、怎么清

## 不在本任务范围

- PG 迁移、Docker、FastAPI 包装（task-21 / task-22）
- 合成数据用于真实模型评测、A/B（后续独立 task）
- Streamlit 内嵌「一键合成」按钮（暂不做，命令行入口即可）
- 自动 fixture 化 / pytest 集成（先把流水跑通，集成留到下个 task）
