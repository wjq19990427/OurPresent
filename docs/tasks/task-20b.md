# Task 20b: 合成剧本载体由 JSON 改为 Markdown（人可读单源）

## 变更说明

**类型**：优化
合成数据的剧本（角色卡 / 时间线 / 延时表达行为）目前是 JSON，结构清楚但读起来像配置文件。本任务把剧本载体换成 Markdown，让作者能像读编剧本那样浏览 timeline 与每条 session 的延时行为，必要时还能直接在 MD 里改一段感受文本后重放入库。

**Branch**：`codex/task-20b`
**前置任务**：task-20（已合并）
**与 task-21 关系**：核心文件集不重叠，可并行（详见末尾「并行执行指南」）

## 背景

task-20 已落地合成流水：`tools/synth/run_synth.py` 跑通 persona → timeline → sessions 全链路，剧本 `tools/synth/scripts/任务20_合成数据剧本.json` 是中间产物，`replay.py` 读它回放入库。

问题：JSON 顶层有 7 个键（`schema_version / metadata / personas / couples / sessions / timeline / destroy_actions / coverage`），其中真正承载"剧情"的 `timeline`（双视角内心戏）和 `sessions`（延时表达行为序列）是这条流水的灵魂；但 JSON 里它们和结构字段挤在一起，作者要逐字段跳读才能拼出一条事件的全貌。我们希望剧本既是给机器读的源，也是给人读的剧本本子。

## 目标

1. 剧本载体改为单一 Markdown 文件，**MD 即 SSoT**，不再保存 JSON 形态的剧本
2. 阅读体验：能按时间顺序一气读完，每条事件下能直接看到该日 A/B 视角的内心戏、对应的 session 文本、以及延时表达的 action 序列
3. 重放等价：现有 JSON 样例迁移到 MD 后，replay 入库结果与 JSON 时代等价（couples 数、sessions 分布、destroy 链路等可观测指标一致）
4. 可编辑：作者在 MD 中直接修改某条 session 的文本字段（`description / feeling / reason`），下次 replay 落库的对应记录反映该改动
5. 可手写：提供一份**最小可重放的 MD 剧本模板**，使用者可以从模板拷一份，手工填角色卡 / 事件 / sessions，不经过 LLM 就能跑通 replay
6. 业务逻辑零改：`driver.py` 只换 loader，不动 application 层调用链

## 改动范围

**许动**：

- `tools/synth/script_io.py`（新增）：MD ↔ dict 的 load/dump，含结构校验
- `tools/synth/actions.py`：`build_script` 产物结构保持不变，但调用方落盘改走 `script_io.dump_md`
- `tools/synth/run_synth.py`：剧本落盘改为 `.md`
- `tools/synth/replay.py`：剧本入参改为 `.md`，调 `script_io.load_md`
- `tools/synth/scripts/任务20_合成数据剧本.md`：现有 JSON 样例迁移到 MD（同名 `.json` 删除；迁移脚本一次性转换或重跑生成器二选一，由实现工评估，产物语义等价即可）
- `tools/synth/scripts/template.md`（新增）：手写模板，含 frontmatter 占位字段、1 对角色卡占位、2 条 timeline 事件占位、覆盖 `private` 与 `pending_unlock` 至少 2 条 session 占位、空 `destroy_actions` 节；模板内行内注释（HTML 注释或显眼标记）说明哪些字段必填、哪些字段不要手改（如 `schema_version`）
- `tools/synth/scripts/.gitignore` 项（如有）相应改为忽略 `*.md`，但需保留入库的样例剧本
- `.gitignore`：原 `tools/synth/scripts/*.json` 改为 `tools/synth/scripts/*.md` 同时显式 `!tools/synth/scripts/任务20_合成数据剧本.md`，保留样例入库
- `tools/synth/README.md`：替换 JSON 相关示例，新增「如何阅读 / 编辑 MD 剧本」「frontmatter 与正文的分工」「从模板手写一份剧本并 replay」三节
- `tools/synth/tests/`：新增至少 3 项 pytest——
  - round-trip：现有剧本 dict → `dump_md` → `load_md` 后结构等价
  - 损坏剧本（缺 frontmatter / personas 字段缺失 / actions 段格式坏）→ 在任何写入发生前 `raise`，DB 文件未创建
  - 模板可重放：`tools/synth/scripts/template.md` 直接通过 `replay.py` 能跑通入库，无运行期报错（验证模板自身合法）

**不许动**：

- `backend/**`、`frontend/**`、`data/`、生产 `Assets/`
- 剧本 dict 的语义字段名（`branch / author / couple_ref / fields.description / fields.feeling / fields.reason / actions[].type / actions[].at / actions[].unlock_at / actions[].text` 等保持原样；本任务只换序列化容器，不改 schema 语义）
- `backend/application/*` 调用顺序与参数

## 关键约束

- **MD 是 SSoT**：仓库里不再保存任何形态的剧本 JSON 文件。LLM 生成阶段在内存里可以以任意中间格式存在，但落盘统一 `.md`
- **frontmatter 与正文的分工**：纯结构字段（`schema_version / metadata / personas / couples` 含密码与 ref / `coverage`）放 frontmatter；剧情字段（`timeline / sessions / destroy_actions`）以人可读形式呈现在正文。具体语法（YAML frontmatter + 章节标题 + actions 用 fenced code block 还是表格）由实现工评估，但必须满足：
  - 人可以从上到下读完不用脑内拼装
  - 解析鲁棒，round-trip 等价（同一个 dict dump 后再 load 必须 deep-equal）
- **不引入新依赖**：优先用 stdlib（自家小解析器 + yaml）；如果实在需要 `python-frontmatter` 这类轻量库，先评估是否值得在 `pyproject.toml` 加项；若需新增依赖，README 中说明取舍
- **driver 启动期断言**：MD 缺失必需 frontmatter 字段、sessions 引用了 timeline 不存在的 `event_id`、actions 段结构坏 → 在 `patched_backend` 进入之前 `raise`，确保没有任何 SQLite 写入发生
- **不污染生产 settings**：MD 解析与 schema 校验只发生在 `tools/synth/` 内部
- **保留 actions 时间戳精度**：JSON 里 `at` 是 `"YYYY-MM-DD HH:MM:SS"`，MD 化后必须能 round-trip 这个精度，不允许悄悄降级为日期

## 验收

实现工完工时，下列行为可被人工或脚本观测：

- `tools/synth/scripts/任务20_合成数据剧本.md` 存在且 git 已入库；同名 `.json` 已删除
- 用 `replay.py` 跑该 MD 剧本，落到隔离 SQLite 的 couples/sessions/dissolved_couples 计数与 task-20 时代的 JSON 重放结果一致
- 在 MD 中手改 `sess_06_share_now` 的 `description` 一句话，重新 replay，对应记录的 description 字段反映改动
- 故意删掉 MD frontmatter 的 `personas` 段，replay 立刻报错退出，隔离 DB 文件未生成
- `run_synth.py --offline` 跑一次，产物是 `.md` 而不是 `.json`
- `tools/synth/scripts/template.md` 存在并入库；从该模板复制一份、按内联说明填一对角色卡 + 两条事件 + 两条 session，`replay.py` 能直接跑通入库
- `tools/synth/README.md` 有人能看懂怎么打开 MD 读剧本、frontmatter 里哪些字段不要手改、如何从模板手写一份剧本

## 不在本任务范围

- 重新调用 Minimax 重新生成内容（迁移时复用现有剧本语义即可）
- 在 Streamlit 内嵌剧本浏览器
- 自动 fixture 化 / pytest 集成（仍延续 task-20 的命令行流程）
- 接入 task-21 的 PG（task-21 自己跑剧本做跨 DB 验收）

## 自查

- 任务卡有没有写"用 ruamel.yaml 还是 python-frontmatter"？没有——交给实现工评估
- 任务卡有没有规定 MD 章节标题用 `##` 还是 `###`？没有——只规定可读性与 round-trip 等价
- 任务卡有没有规定 actions 用表格还是 fenced yaml？没有——同上
- 任务卡有没有规定模板里要不要预置销毁链路样例？没有——只规定模板必须能 replay 通过，覆盖到的分支由实现工评估

## 并行执行指南

Wave 1（同时开 2 个 worktree）：

- Codex A → task-20b（主改文件：`tools/synth/script_io.py` 新增、`tools/synth/actions.py`、`tools/synth/run_synth.py`、`tools/synth/replay.py`、`tools/synth/scripts/任务20_合成数据剧本.md`、`tools/synth/scripts/template.md` 新增、`tools/synth/README.md`、`tools/synth/tests/`）
- Codex B → task-21（主改文件：`backend/infrastructure/database/*`、`backend/config/settings.py`、`docker-compose.yml`、`pyproject.toml`；详见 task-21 卡）

文件冲突分析：
- task-20b 不动 `backend/`，task-21 不动 `tools/synth/`
- 共享潜在文件 `pyproject.toml`：task-20b 默认不新增依赖（首选 stdlib），如必须新增，与 task-21 实现工口头协调一次合并顺序；`.gitignore` 同理，分行追加无冲突

Wave 2：本批次无后置依赖任务。task-22（FastAPI 包装）按既定路线在 task-21 落地后启动。
