# 合成数据流水线

`tools/synth/` 是开发期专用的合成数据流水线，用虚构情侣角色生成 OurPresent 测试数据，并写入隔离 SQLite。它不使用真实用户数据，也不改动 `backend/` 生产逻辑。

这里的“剧本”是一份 Markdown 文件：它同时给人阅读、给程序读取。程序会按剧本里的角色、时间线、记录和后续行为，在隔离数据库里创建用户、绑定情侣、保存记录、设置延时共享、写评论、执行关系解除后的数据销毁。

## 常用术语

- 剧本：`tools/synth/scripts/*.md` 里的 Markdown 文件，描述要生成哪几个人、哪些关系事件、哪些记录和后续行为。
- 生成：从角色卡和时间线创建一份剧本。离线生成不调用模型；联网生成会调用 Minimax 生成时间线。
- 重放：不再调用模型，而是按已有 Markdown 剧本逐步执行应用层 API，把同一批虚构数据写进隔离 SQLite。这个词的含义就是“按剧本重新跑一遍数据写入过程”。
- frontmatter：Markdown 顶部 `---` 到 `---` 之间的结构区，放版本、角色卡、账号、关系引用、覆盖范围等不适合夹在正文里的字段。
- 正文：frontmatter 下面的可阅读剧本内容，按时间顺序展示事件、A/B 内心、要写入的记录、以及这条记录之后发生的共享或评论动作。
- `timeline`：关系事件。它不直接写数据库，主要给 `sessions` 提供事件背景、日期和双视角内心。
- `session`：要写入数据库的一条记录。它包含作者、发生日期、描述、感受、原因和可见性分支。
- `actions`：某条记录保存后继续发生的行为，例如申请延时共享、调整解锁时间、立即解锁或添加评论。

## 环境变量

每次运行前必须设置隔离数据库路径：

```bash
export SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db
export MINIMAX_API_KEY=...
export MINIMAX_BASE_URL=https://api.minimax.io/v1
export MINIMAX_MODEL=MiniMax-M2.5
```

`SYNTH_DB_PATH` 必填。为空或指向 `data/database.db` 时，driver 会在任何写入发生前直接报错退出。

附件目录也会隔离。当前实现是在 synth 进程内 monkey-patch backend 的路径常量，默认写到 `tools/synth/.synth_db/Assets/`。可以用 `SYNTH_ASSETS_ROOT` 覆盖，但不能指向项目根目录下的 `Assets/`。

## 离线样例运行

没有 API key 时可以用离线路径做 smoke test：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/run_synth.py --offline
```

这会生成 `tools/synth/scripts/任务20_合成数据剧本.md`，然后立刻把这份剧本写入隔离数据库。终端会输出剧本路径、数据库路径和各类记录数量。

离线路径仍会走同一套重放 driver，并生成任务要求的延时共享行为分布。

## 调用 Minimax 生成

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/run_synth.py \
  --persona tools/synth/personas/sample_couples.json \
  --weeks 6
```

这会先校验 Minimax 环境变量，再从角色卡生成时间线，把 Markdown 剧本写到 `tools/synth/scripts/`，最后通过 application 层公开 API 写入隔离数据库。

## 不调模型，按已有剧本写库

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/replay.py tools/synth/scripts/任务20_合成数据剧本.md
```

默认行为会先清空配置好的隔离数据库和隔离附件目录，再按剧本重新写入。这样同一份剧本跑多次会得到等价的逻辑数据，方便对比和回归。

只有在明确想把多份剧本追加到同一个合成库时，才使用 `--append`：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/replay.py tools/synth/scripts/任务20_合成数据剧本.md --append
```

## 如何阅读 Markdown 剧本

先从正文读，不必先读 frontmatter。正文按时间顺序排列：

- `### 日期 · 事件编号 · 事件主题` 是一天的关系事件。
- 事件下面的 A/B 内心帮助理解双方感受。
- `#### 记录编号 · 作者 · 可见性分支` 是实际要写入数据库的一条记录。
- 记录的 `description` 是发生了什么，`feeling` 是当事人的感受，`reason` 是为什么选择这个公开状态。
- 每条记录下面的 `actions` 是保存记录之后继续发生的行为。空列表 `[]` 表示保存后没有额外动作。

可见性分支的含义：

- `private`：永久私密。记录只属于作者，不会自动让伴侣看到。
- `pending_unlock`：延时共享。记录先保持未公开，之后通过 `request_unlock` 设置未来可公开的时间。
- `shared`：已共享。记录会进入伴侣可见路径；如果后面有 `add_comment`，表示伴侣读到后写了评论。
- `destroyed`：用于验证关系解除后的销毁链路。写入后会在 `destroy_actions` 指定的流程里被清理。

## frontmatter 与正文的分工

frontmatter 放结构字段，正文放剧情字段。这样做是为了让人阅读时先看故事线，同时让程序能在写数据库前完整校验引用关系。

frontmatter 里通常不要手改：

- `schema_version`：剧本格式版本，工具升级前保持 `1`。
- `couples[].ref`：关系引用名，正文里的 `session.couple_ref` 会用它找到要写入哪对关系。
- `couples[].password`：合成账号注册时用的密码。
- `coverage`：本剧本覆盖的业务分支。只有当你真的增删分支时再改。

正文里最常手改：

- `timeline` 代码块里的 `date`、`theme`、`inner_voice.A`、`inner_voice.B`。
- `session` 代码块里的 `fields.description`、`fields.feeling`、`fields.reason`。
- `actions` 里的时间。时间必须保持 `YYYY-MM-DD HH:MM:SS`，否则会在写入前报错。

如果改了 `event_id`，要同步改引用它的 `session.event_id`。如果改了 `couple_ref`，要确保 frontmatter 的 `couples[].ref` 里存在同名关系。

## 从模板手写一份剧本

最小模板在：

```text
tools/synth/scripts/template.md
```

建议流程：

1. 复制模板为一个新的 `.md` 文件。
2. 改 frontmatter 里的角色卡、用户名和剧本名。
3. 保留至少两条 `timeline`，并确保每条 `session.event_id` 能找到对应事件。
4. 至少保留一条 `private` 记录和一条 `pending_unlock` 记录。`pending_unlock` 记录需要有 `request_unlock` 动作，并填写 `at` 与 `unlock_at`。
5. 运行 `uv run python tools/synth/replay.py 你的剧本.md`。如果结构坏了，工具会在创建数据库前报错。

模板本身可以直接执行，用来确认本地环境和格式解析都正常。

## 剧本覆盖内容

入库样例 `任务20_合成数据剧本.md` 覆盖：

- 永久私密记录
- 1 小时、1 天、1 周、1 个月后解锁的延时共享样本
- 推后和提前调整解锁时间
- 立即解锁
- 伴侣读取后评论互动
- 关系解除冻结期后的数据销毁链路

如果未来生成器无法覆盖某个分支，必须把该分支写入 `coverage.skipped` 并说明原因。

## 清理

正常重放只会重置配置好的合成 DB 和合成 Assets 根目录。需要手动清理时：

```bash
rm -rf tools/synth/.synth_db
```

不要把 `SYNTH_DB_PATH` 指向 `data/database.db`。
