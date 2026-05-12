# 合成数据流水线

`tools/synth/` 是开发期专用的合成数据流水线，用虚构情侣角色生成 OurPresent 测试数据，并写入隔离 SQLite。它不使用真实用户数据，也不改动 `backend/` 生产逻辑。

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

## 调用 Minimax 生成

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/run_synth.py \
  --persona tools/synth/personas/sample_couples.json \
  --weeks 6
```

这会先校验 Minimax 环境变量，再从角色卡生成时间线，把人可读剧本 JSON 写到 `tools/synth/scripts/`，最后通过 application 层公开 API 重放入库。

## 离线样例运行

没有 API key 时可以用离线路径做 smoke test：

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/run_synth.py --offline
```

离线路径仍会走同一套 replay driver，并生成任务要求的延时共享行为分布。

## 不调模型重放

```bash
SYNTH_DB_PATH=tools/synth/.synth_db/data/database.db \
uv run python tools/synth/replay.py tools/synth/scripts/任务20_合成数据剧本.json
```

重放默认会重置隔离 DB 和隔离 Assets 目录。同一份剧本重放两次会得到等价的逻辑 DB 状态。只有在明确想追加写入已有合成库时，才使用 `--append`。

## 剧本覆盖内容

生成的剧本包含三层：

- `personas`：每对情侣两份独立角色卡，包含性格基调、沟通风格、关系阶段和情感锚点。
- `timeline`：带日期的双视角事件；其中一条事件由前一次共享记录和评论互动继续发酵。
- `sessions`：延时表达行为，覆盖永久私密、1 小时 / 1 天 / 1 周 / 1 个月后解锁、推后解锁、提前解锁、立即解锁、伴侣读取后评论，以及冻结期销毁样例。

如果未来生成器无法覆盖某个分支，必须把该分支写入 `coverage.skipped` 并说明原因。

## 清理

正常 replay 只会重置配置好的合成 DB 和合成 Assets 根目录。需要手动清理时：

```bash
rm -rf tools/synth/.synth_db
```

不要把 `SYNTH_DB_PATH` 指向 `data/database.db`。
