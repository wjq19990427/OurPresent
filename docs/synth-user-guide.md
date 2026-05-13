# 合成数据工具使用说明

本文档面向 OurPresent 的产品使用者、测试人员和演示准备者，说明如何用 `tools/synth/` 生成一套虚构情侣数据。它不是给生产用户使用的功能，而是帮助你在没有真实隐私数据的情况下，快速准备一个可展示、可回归、可重复生成的本地数据库。

## 1. 这个工具是做什么的

OurPresent 的核心体验围绕亲密关系、私密记录、延时共享和解除绑定展开。如果用真实情侣的数据做测试，会有明显的隐私风险；如果只手工造几条记录，又很难覆盖真实使用中的复杂路径。

合成数据工具解决的是这个问题：它会从虚构情侣角色卡出发，生成一段关系时间线，再把这些事件转成真实应用里的记录、共享、调整、评论和销毁流程，最后写入一个独立 SQLite 数据库。

生成后，你可以得到：

- 一对虚构用户
- 已绑定的情侣关系
- 一组中文关系事件和记录
- 永久私密记录
- 1 小时、1 天、1 周、1 个月后解锁的延时共享样本
- 推后 / 提前开放时间的样本
- 立即解锁样本
- 伴侣读取后评论互动样本
- 关系解除冻结期后的销毁链路样本

这些数据适合用于本地演示、回归验证、未来迁移验证和功能走查。它不应该被当作真实用户数据，也不应该写入项目默认的 `data/database.db`。

## 2. 你会得到哪些文件

一次生成通常会产生两类结果：

- Markdown 剧本：保存在 `tools/synth/scripts/`，例如 `lin_xia_together.md` 或 `mo_qin_destroyed.md`
- 隔离数据库：推荐保存在 `tools/synth/.synth_db/data/database.db`

剧本是这套数据的来源文件。它不是导出日志，也不是临时缓存；只要保留这份 Markdown，就可以在不再次调用大模型的情况下，重新生成同一套虚构数据。为了方便阅读，每份剧本只讲一对情侣；这对情侣最终继续在一起，还是进入冻结期并销毁数据，由生成时的 `outcome` 决定。

数据库是应用可读取的 SQLite 文件。默认不会替换正式本地库，你需要显式设置 `SYNTH_DB_PATH` 才能运行。

## 3. 几个概念先说清楚

剧本：一份 Markdown 文件，描述一对情侣的角色卡、关系事件、要写入的记录、记录之后发生的共享/评论/销毁行为。

生成：从单对情侣角色卡和时间线创建剧本。离线生成使用内置确定性内容和 persona 的 `expected_outcome`；联网生成会调用 Minimax 生成时间线并判断结局。

重放：按已有剧本重新执行一遍数据写入过程。它不会再问模型要新内容，而是严格照着 Markdown 里的字段调用应用层 API，把用户、关系、记录和后续行为写进隔离数据库。

frontmatter：Markdown 顶部两条 `---` 中间的结构区，放剧本版本、结局、角色卡、账号关系、覆盖范围等字段。

正文：frontmatter 下面的可阅读内容，按时间顺序展示事件、A/B 内心、记录正文和记录之后的行为。

`timeline`：关系事件。它说明某天发生了什么、双方内心怎么想，但它自己不会直接写入数据库。

`session`：一条要写入数据库的记录。它包含作者、发生日期、描述、感受、原因和公开状态。

`actions`：记录保存后继续发生的行为，例如申请延时共享、调整解锁时间、立即共享或添加评论。

## 4. 使用前准备

先在项目根目录安装依赖：

```bash
uv sync
```

然后设置合成数据库路径。推荐使用下面这个隔离路径：

```bash
export SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db
```

不要把 `SYNTH_DB_PATH` 设置成 `data/database.db`。工具会主动拒绝这个路径，避免误写真实本地数据。

如果你只想使用内置中文样例，不需要配置大模型 key。如果你想让 Minimax 重新生成时间线，需要额外设置：

```bash
export MINIMAX_API_KEY=你的_Minimax_key
export MINIMAX_BASE_URL=https://api.minimax.io/v1
export MINIMAX_MODEL=MiniMax-M2.5
```

## 5. 最快跑通：离线样例

没有 API key 时，建议先跑离线样例：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/run_synth.py --offline
```

成功后终端会显示类似信息：

```text
script=tools/synth/scripts/lin_xia_together.md
db=/.../tools/synth/.synth_db/data/database.db
summary={'users': 2, 'couples': 1, 'sessions': 6, ...}
```

这表示已经生成一份 Markdown 剧本，并把它写入隔离数据库。默认样例是林澈 / 夏予的 `together` 结局，覆盖延时共享与评论互动路径；如果要离线生成销毁链路样例，换用 `tools/synth/personas/mo_qin_destroyed.json` 即可。

## 6. 调用 Minimax 生成

配置好 Minimax 环境变量后，运行：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/run_synth.py \
  --persona tools/synth/personas/lin_xia_together.json \
  --weeks 6
```

参数说明：

- `--persona`：角色卡 JSON 路径。默认使用内置样例。
- `--weeks`：生成几周的关系时间线，当前建议 4 到 12 周。
- `--offline`：不调用大模型，使用内置确定性样例。
- `--outcome together|destroyed`：调试时显式覆盖结局；不传时联网由 Minimax 判断，离线读取 persona 的 `expected_outcome`。
- `--append`：追加写入现有合成库。默认不建议使用，因为默认重跑会先清理隔离库，让结果更稳定。

联网模式下，Minimax 的 JSON 输出必须同时包含 `outcome`、`outcome_reason` 和 `events`。三者都会进入剧本 frontmatter 或正文。

## 7. 按已有剧本重新写库

如果你已经有一份 Markdown 剧本，可以不再调用大模型，直接按剧本写入隔离数据库：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/replay.py tools/synth/scripts/lin_xia_together.md
```

默认会清空并重建隔离数据库和隔离附件目录。这样同一份剧本每次生成出的逻辑数据都一致，方便排查问题和做回归对比。

例如重放默认样例：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/replay.py tools/synth/scripts/lin_xia_together.md
```

默认不要加 `--append`，这样每次重放都会从干净的隔离库开始。只有明确要把多份手写剧本追加到同一个隔离库里时才使用 `--append`。

如果剧本缺少 frontmatter、角色卡字段、事件引用，或者某个 `actions` 段格式不对，工具会在创建数据库前报错。也就是说，格式错误不会留下半写入的 SQLite 文件。

## 8. 怎么读 Markdown 剧本

建议先看正文，再看 frontmatter。正文是按时间顺序排的：

- `### 日期 · 事件编号 · 事件主题` 表示一条关系事件。
- 事件下面的 A/B 内心说明双方当时怎么理解这件事。
- `#### 记录编号 · 作者 · 公开状态` 表示要写入数据库的一条记录。
- `fields.description` 是这条记录描述了什么。
- `fields.feeling` 是作者的感受。
- `fields.reason` 是作者为什么选择这种公开方式。
- `actions` 是记录保存后发生的行为，空列表 `[]` 表示没有后续行为。

公开状态的定义：

- `private`：永久私密，只有作者自己可见。
- `pending_unlock`：延时共享，先不让伴侣看到，之后按 `unlock_at` 指定时间进入可共享路径。
- `shared`：已共享，伴侣可以看到；如果后面有 `add_comment`，表示伴侣读到后写了评论。
- `destroyed`：销毁链路样本，主要用于验证关系解除后数据会被清理。

行为类型的定义：

- `request_unlock`：申请把记录设为未来某个时间可共享，必须有 `at` 和 `unlock_at`。
- `reschedule_unlock`：调整已经申请的共享时间，必须有新的 `unlock_at`。
- `unlock_now`：立即共享，不再等原来的未来时间。
- `add_comment`：伴侣读到共享记录后添加评论，必须有 `author` 和 `text`。

所有带时分秒的时间都必须写成 `YYYY-MM-DD HH:MM:SS`，例如 `2026-01-06 11:00:00`。只写日期会被拒绝，因为延时共享需要精确到秒。

## 9. frontmatter 和正文分别能改什么

frontmatter 适合放结构资料，正文适合放剧情资料。这个分工让剧本既能从上到下读懂，也能在写数据库前被完整校验。

frontmatter 里常见字段：

- `schema_version`：Markdown 剧本格式版本。现在是 `1`，不要为了改内容而改它。
- `outcome` / `outcome_reason`：这对情侣的结局及一行原因。
- `metadata`：剧本名称、生成周数、生成时间和备注。
- `personas`：角色卡，描述 A/B 的展示名、性格、沟通风格、关系阶段和情感锚点。
- `couples`：真正要注册和绑定的账号，`ref` 是正文引用这对关系时使用的名字。
- `coverage`：这份剧本覆盖了哪些业务路径，方便人工验收。

正文里最适合手改：

- `timeline.theme`
- `timeline.inner_voice.A`
- `timeline.inner_voice.B`
- `session.fields.description`
- `session.fields.feeling`
- `session.fields.reason`
- `actions[].at`
- `actions[].unlock_at`
- `actions[].text`

改引用字段时要一起改完整。例如把某条事件的 `id` 从 `evt_01` 改成 `evt_move_in`，就要把对应记录的 `event_id` 也改成 `evt_move_in`。如果只改一边，工具会在写数据库前报错。

## 10. 从模板手写一份剧本

模板文件在：

```text
tools/synth/scripts/template.md
```

推荐做法：

1. 复制模板为一个新 `.md` 文件。
2. 先只改中文内容，不改字段名。
3. 保留一对角色卡、两条 `timeline`、两条 `session`。
4. 至少保留一条 `private` 记录和一条 `pending_unlock` 记录。
5. 运行 `uv run python tools/synth/replay.py 你的剧本.md` 验证格式。

模板本身可以直接运行。如果模板都跑不通，先检查 `SYNTH_DB_PATH` 是否设置在隔离目录。

## 11. 如何查看生成结果

生成完成后，可以用 SQLite 工具查看数据库，也可以把应用指向这份合成库进行本地走查。

最直接的命令行检查：

```bash
sqlite3 tools/synth/.synth_db/data/database.db
```

进入 SQLite 后可以查看：

```sql
select username from users;
select couple_status from couples;
select visibility, count(*) from sessions group by visibility;
select description, feeling, reason from sessions limit 5;
```

你应该能看到中文用户名、中文记录内容，以及 `private` / `pending_unlock` / `shared` 等可见性状态。

如果要从应用界面查看，需要确保当前运行环境读取的是这份合成库，而不是默认生产库。此处只建议用于本地开发或演示，不建议把合成库和真实库混用。

## 12. 角色卡怎么改

内置角色卡在：

```text
tools/synth/personas/lin_xia_together.json
```

每份 persona JSON 顶层就是一对情侣，包含 `seed_id`、`start_date`、`a`、`b`，以及可选的 `expected_outcome`。你可以改：

- 中文用户名
- 展示名
- 性格基调
- 沟通风格
- 关系阶段
- 当前情感锚点
- 离线期望结局：`expected_outcome` 可设为 `together` 或 `destroyed`

建议保持内容完全虚构，不要复制真实用户的姓名、事件、聊天记录或私人经历。这个工具的价值就在于用“像真的一样”的虚构数据替代真实隐私数据。

## 13. 清理合成数据

默认推荐路径下，清理命令是：

```bash
rm -rf tools/synth/.synth_db
```

生成过程中的临时 Markdown 默认被 `.gitignore` 忽略。仓库会保留固定样例 `lin_xia_together.md`、`mo_qin_destroyed.md` 和一份模板 `template.md`，方便回归和手写起步。

## 14. 安全边界

请记住这些规则：

- 不要使用真实用户数据作为角色卡输入。
- 不要把 `SYNTH_DB_PATH` 指向 `data/database.db`。
- 不要把合成附件目录指向项目根目录的 `Assets/`。
- 不要把 API key 写进文档或提交到仓库。
- 默认按剧本写库会清空隔离合成库，请确认路径无误。

只要遵守这些边界，`tools/synth/` 就可以作为一个稳定、低风险的演示和回归数据来源。
