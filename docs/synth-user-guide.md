# 合成数据工具使用说明

本文档面向 OurPresent 的产品使用者、测试人员和演示准备者，说明如何用 `tools/synth/` 生成一套虚构情侣数据。它不是给生产用户使用的功能，而是帮助你在没有真实隐私数据的情况下，快速准备一个可展示、可回归、可重复生成的本地数据库。

## 1. 这个工具是做什么的

OurPresent 的核心体验围绕亲密关系、私密记录、延时共享和解除绑定展开。如果用真实情侣的数据做测试，会有明显的隐私风险；如果只手工造几条记录，又很难覆盖真实使用中的复杂路径。

合成数据工具解决的是这个问题：它会从一对虚构情侣角色卡出发，生成一段关系时间线，再把这些事件转成真实应用里的记录、共享、调整、评论和销毁流程，最后写入一个独立 SQLite 数据库。

生成后，你可以得到：

- 一对或多对虚构用户
- 已绑定的情侣关系
- 一组中文关系事件和记录
- 永久私密记录
- 1 小时、1 天、1 周、1 个月后解锁的延时共享样本
- 推后 / 提前开放时间的样本
- 立即解锁样本
- 伴侣读取后评论互动样本
- 冻结期销毁链路样本

这些数据适合用于本地演示、回归验证、未来迁移验证和功能走查。它不应该被当作真实用户数据，也不应该写入项目默认的 `data/database.db`。

## 2. 你会得到哪些文件

一次生成通常会产生两类结果：

- 剧本 JSON：保存在 `tools/synth/scripts/`，例如 `任务20_合成数据剧本.json`
- 隔离数据库：推荐保存在 `tools/synth/.synth_db/data/database.db`

剧本 JSON 是人可读的。它记录了角色卡、时间线、每条记录要执行的共享动作，以及覆盖了哪些业务分支。只要保留这份剧本，就可以在不再次调用大模型的情况下重复生成同一套数据。

数据库是应用可读取的 SQLite 文件。默认不会替换正式本地库，你需要显式设置 `SYNTH_DB_PATH` 才能运行。

## 3. 使用前准备

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

## 4. 最快跑通：离线样例

没有 API key 时，建议先跑离线样例：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/run_synth.py --offline
```

成功后终端会显示类似信息：

```text
script=tools/synth/scripts/任务20_合成数据剧本.json
db=/.../tools/synth/.synth_db/data/database.db
summary={'users': 4, 'couples': 2, 'sessions': 6, ...}
```

这表示已经生成剧本，并把剧本重放进隔离数据库。离线样例仍然会覆盖主要业务路径，因此足够用于 smoke test 和演示准备。

## 5. 调用 Minimax 生成

配置好 Minimax 环境变量后，运行：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/run_synth.py \
  --persona tools/synth/personas/sample_couples.json \
  --weeks 6
```

参数说明：

- `--persona`：角色卡 JSON 路径。默认使用内置样例。
- `--weeks`：生成几周的关系时间线，当前建议 4 到 12 周。
- `--offline`：不调用大模型，使用内置确定性样例。
- `--append`：追加写入现有合成库。默认不建议使用，因为默认重跑会先清理隔离库，让结果更稳定。

## 6. 重放已有剧本

如果你已经有一份剧本 JSON，可以不再调用大模型，直接重放：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/replay.py tools/synth/scripts/任务20_合成数据剧本.json
```

重放默认会清空并重建隔离数据库和隔离附件目录。这样同一份剧本每次生成出的逻辑数据都一致，方便排查问题和做回归对比。

只有当你明确想把多份剧本写进同一个合成库时，才加 `--append`：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/replay.py tools/synth/scripts/任务20_合成数据剧本.json --append
```

## 7. 如何查看生成结果

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

## 8. 角色卡怎么改

内置角色卡在：

```text
tools/synth/personas/sample_couples.json
```

每对情侣有两份角色卡，分别描述 A 和 B。你可以改：

- 中文用户名
- 展示名
- 性格基调
- 沟通风格
- 关系阶段
- 当前情感锚点

建议保持内容完全虚构，不要复制真实用户的姓名、事件、聊天记录或私人经历。这个工具的价值就在于用“像真的一样”的虚构数据替代真实隐私数据。

## 9. 剧本里有什么

剧本 JSON 大致分成几部分：

- `metadata`：剧本名称、生成时间、说明
- `personas`：角色卡
- `timeline`：按日期展开的双视角事件
- `sessions`：每条事件对应的记录和延时共享动作
- `destroy_actions`：冻结和销毁链路样本
- `coverage`：本剧本覆盖了哪些业务分支

剧本是为了让人能读懂和复查。你可以打开它确认“为什么会有这条记录”“这条记录什么时候解锁”“哪个分支被覆盖了”。

## 10. 清理合成数据

默认推荐路径下，清理命令是：

```bash
rm -rf tools/synth/.synth_db
```

剧本 JSON 默认被 `.gitignore` 忽略，不会进入版本库。如果你想保留某份剧本作为固定样例，可以另行放到明确要入库的位置，并在提交前确认其中没有真实隐私内容。

## 11. 安全边界

请记住这些规则：

- 不要使用真实用户数据作为角色卡输入。
- 不要把 `SYNTH_DB_PATH` 指向 `data/database.db`。
- 不要把合成附件目录指向项目根目录的 `Assets/`。
- 不要把 API key 写进文档或提交到仓库。
- 重放剧本默认会清空隔离合成库，请确认路径无误。

只要遵守这些边界，`tools/synth/` 就可以作为一个稳定、低风险的演示和回归数据来源。
