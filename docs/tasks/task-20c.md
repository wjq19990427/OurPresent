# task-20c · 合成剧本：单 persona / 单剧本 / 结局由 LLM 决定

## 变更说明

类型：重构

合成数据流水线改为「一份 persona 文件 = 一对情侣 = 一份剧本」；剧本最终走向（在一起继续延时共享 vs 走到冻结期销毁数据）由大模型在生成时自行判断写入剧本，方便不断追加新的角色样本去测试不同结局，而不必每次都改大 JSON 或同时跑两份产物。

---

## 背景

task-20b 把剧本载体改成 Markdown 之后，剧本本身的可读性已经足够，但**生成端**还有两处和"动态新增样本"相冲突的设计：

1. `tools/synth/personas/sample_couples.json` 用 `couples[]` 数组 + `role=primary` / `role=destroy_sample` 把两对情侣塞进同一份 JSON。新增样本只能改这份大 JSON，不能像"再加一个文件"那样直接扩展。
2. `run_synth.py` 一次跑会产出两份 md（主线 + 销毁线），结局由 `actions.py` 里硬编码的 `PRIMARY_SESSION_SPECS` / `DESTROY_SESSION_SPECS` 选其一，LLM 完全不参与结局判断。

合并后的真正语义应该是：**一对情侣一份 persona，一次生成一份剧本；这对情侣最终是在一起还是走到销毁，由 LLM 看着角色卡自己写**。

## 行为契约

### 1. persona schema 改造

`tools/synth/personas/` 下每份 JSON 顶层就是单对情侣，删掉 `couples[]` 与 `role`：

- 保留 `seed_id` / `start_date` / `a` / `b`，字段语义不变
- 新增可选字段 `expected_outcome ∈ {"together", "destroyed"}`，仅离线 fallback 使用；联网模式下被 LLM 输出覆盖
- 旧的双对 JSON 拆为两份单对 JSON 样例（命名能反映角色，例如 `lin_xia_together.json` / `mo_qin_destroyed.json`），各自带不同的 `expected_outcome`

`load_persona_seed` / `validate_persona_seed` 同步改为按"单对"形态校验，不再有 primary/destroy_sample 概念。

### 2. LLM 输出契约扩展

`timeline.py` 调 Minimax 时 prompt 让模型同时输出三项：

```json
{
  "outcome": "together" | "destroyed",
  "outcome_reason": "≤ 1 行说明这对情侣为什么走到这个结局",
  "events": [...]
}
```

`generate_timeline` 的返回签名扩展为同时携带 outcome 与 outcome_reason（具体载体由实现自定，但要让 `build_script` 拿得到）。离线 deterministic 路径返回 `persona["expected_outcome"]`（缺省视为 `"together"`）与既有的事件列表。

### 3. 剧本骨架由 outcome 驱动

`actions.py` 合并为单一入口 `build_script(persona, timeline, outcome, outcome_reason, weeks)`：

- `outcome=together`：维持原 PRIMARY 那套延时共享 + 评论互动分布，`destroy_actions=[]`
- `outcome=destroyed`：剧本前段仍要有正常的延时共享 / 互动记录（不能只剩一条 destroyed session 就草草结束），结尾再追加冷淡阶段 session + `destroy_actions` 触发 `start_uncouple` 与 `destroy_couple_data`
- frontmatter 新增 `outcome` / `outcome_reason` 字段；正文人可读处也应当能看到结局
- 删除独立的 `build_destroy_script` 入口

`driver.py` / `replay.py` 写库阶段**不感知 outcome**——`destroy_actions` 是否为空就足以决定是否触发销毁链路。

### 4. CLI

`run_synth.py`：

- `--persona` 接收单 persona 文件路径
- 一次调用 → 一份 md + 一次写库；终端 `script=` 只打印一行
- 新增 `--outcome together|destroyed` 调试覆盖；不传时联网由 LLM 决定，离线读 persona 字段
- 删除"一次生成两份产物"的逻辑，不支持批量

`replay.py` 行为不变（仍按已有 md 写库），但要能识别 frontmatter 里新加的 outcome 字段（容许存在即可，不用据此分支）。

### 5. 样例与文档

- 旧 `任务20_合成数据剧本.md` / `任务20_销毁链路剧本.md` 由新流程重新生成（离线即可），各自带 `outcome` frontmatter，文件名可改为反映角色而不必带"任务20"
- `scripts/template.md` 同步带 `outcome: together` 默认值与 outcome_reason 占位
- `tools/synth/README.md` 重写"剧本覆盖内容"段：从"两份 md 覆盖不同分支"改为"一对情侣一份 md，结局由 LLM 判断"
- `docs/synth-user-guide.md` 同步更新涉及 persona / 产物份数 / outcome 的章节

## 不要做

- 不改 `script_io.py` 的解析器本身，只在 frontmatter 字段白名单里接纳新字段
- 不改 `driver.py` 写库语义；销毁仍走 `destroy_actions`
- 不引入新依赖
- 不动 `backend/` 任何文件
- 不做"扫目录批量生成所有 persona 的剧本"功能

## 验收清单

- [ ] `personas/` 下每份 JSON 描述单对情侣，旧 `sample_couples.json` 拆为两份单对样例
- [ ] `run_synth.py --persona <single.json> --offline` 输出一份 md + 一次写库，终端 `script=` 只一行
- [ ] LLM 模式下 prompt 让模型同时输出 outcome / outcome_reason / events，三者全部进入剧本 frontmatter
- [ ] 离线 fallback 读 `expected_outcome`，缺省视为 `together`；`--outcome` 显式覆盖以上两种来源
- [ ] `outcome=destroyed` 的剧本前段仍有正常延时共享记录，结尾才进入冷淡 → uncouple → destroy 完整链路
- [ ] `tools/synth/tests/test_synth_workflow.py` 新增至少 1 项 outcome=destroyed 端到端用例；原有用例保持通过
- [ ] `tools/synth/README.md` 与 `docs/synth-user-guide.md` 反映新语义
- [ ] CHANGELOG `[Unreleased]` 补一行，STATUS「最近完成」「下一步」对应更新

## 涉及文件

核心：
- `tools/synth/personas/*.json`（重组）
- `tools/synth/persona.py`
- `tools/synth/timeline.py`
- `tools/synth/actions.py`
- `tools/synth/run_synth.py`
- `tools/synth/script_io.py`（仅 frontmatter 字段白名单）
- `tools/synth/scripts/*.md`（重新生成）
- `tools/synth/tests/test_synth_workflow.py`

文档：
- `tools/synth/README.md`
- `docs/synth-user-guide.md`
- `CHANGELOG.md` `[Unreleased]`
- `docs/STATUS.md`

## 并行执行指南

Wave 1（与 task-21 同时开 worktree）：
- Codex A → task-20c（核心文件全部在 `tools/synth/`）
- Codex B → task-21（核心文件在 `backend/infrastructure/` + `docker/`）

两者核心文件零交集；都改 `CHANGELOG.md` / `docs/STATUS.md`，但只有少量行，合并时 trivial。
