---
<!-- schema_version 是解析契约版本，除非工具代码升级，否则不要手改。 -->
schema_version: 1
metadata:
  name: template
  weeks: 1
  generated_at: 2026-01-05 09:00:00
  notes: 最小可重放模板；复制后可以改角色、事件和记录文本。
personas:
  seed_id: 手写模板
  start_date: 2026-01-05
  couples:
    - id: cp_template_seed
      role: primary
      a:
        id: A
        username: 合成模板A
        display_name: 模板甲
        tone: 敏感但愿意表达
        communication_style: 先写下来整理，再当面确认
        relationship_stage: 练习沟通
        emotional_anchors:
          - 刚开始认真练习记录关系里的小事
          - 想把难说出口的话用更温和的方式交给对方
      b:
        id: B
        username: 合成模板B
        display_name: 模板乙
        tone: 温和直接，期待及时回应
        communication_style: 先确认感受，再讨论下一步
        relationship_stage: 练习沟通
        emotional_anchors:
          - 希望重要情绪不要只靠猜
          - 愿意给对方一点整理时间
couples:
  - ref: primary
    a:
      username: 合成模板A
    b:
      username: 合成模板B
    password: synth-pass-template
coverage:
  covered:
    - 永久私密
    - 延时共享_1天
  skipped: []
---

# 最小可重放 Markdown 剧本模板

这份模板可以直接执行，用来确认格式正确。复制它以后，通常只需要改三类内容：

- frontmatter 里的角色卡与账号名。
- 每个 `timeline` 代码块里的事件日期、主题和 A/B 内心。
- 每个 `session` 代码块里的 `fields.description`、`fields.feeling`、`fields.reason`，以及需要验证延时共享时的 `actions`。

`ref`、`couple_ref`、`event_id` 是引用字段：改它们时要同步改所有引用处，否则工具会在写入数据库前报错。

## 时间线与记录

### 2026-01-05 · evt_01 · 第一次认真写下没有说出口的话

- 事件视角：`A`
- 由哪条记录继续发展：无
- A 的内心：模板甲：我想先把心情放在一个安全的地方。
- B 的内心：模板乙：我知道对方需要一点整理时间。

```yaml timeline
id: evt_01
date: 2026-01-05
perspective: A
theme: 第一次认真写下没有说出口的话
seed_from: null
inner_voice:
  A: 模板甲：我想先把心情放在一个安全的地方。
  B: 模板乙：我知道对方需要一点整理时间。
```

#### sess_template_private · 作者 A · private

- 写入关系：`primary`
- 创建时间：`2026-01-05 09:10:00`
- 描述：我把今天的犹豫先写下来，没有立刻发给你。
- 感受：模板甲：我还没准备好被看见，但已经比昨天更诚实。
- 选择这个公开状态的原因：这条记录只保存给自己看，不会自动分享给伴侣。

```yaml session
ref: sess_template_private
couple_ref: primary
author: A
event_id: evt_01
branch: private
created_at: 2026-01-05 09:10:00
source_type: text
fields:
  content_time: 2026-01-05
  description: 我把今天的犹豫先写下来，没有立刻发给你。
  feeling: 模板甲：我还没准备好被看见，但已经比昨天更诚实。
  reason: 这条记录只保存给自己看，不会自动分享给伴侣。
actions: []
```

### 2026-01-06 · evt_02 · 决定晚一点把心情交给对方

- 事件视角：`B`
- 由哪条记录继续发展：无
- A 的内心：模板甲：我希望这次不是把压力丢过去。
- B 的内心：模板乙：如果晚一点能说得更清楚，我愿意等。

```yaml timeline
id: evt_02
date: 2026-01-06
perspective: B
theme: 决定晚一点把心情交给对方
seed_from: null
inner_voice:
  A: 模板甲：我希望这次不是把压力丢过去。
  B: 模板乙：如果晚一点能说得更清楚，我愿意等。
```

#### sess_template_pending · 作者 B · pending_unlock

- 写入关系：`primary`
- 创建时间：`2026-01-06 10:00:00`
- 描述：我先记录下期待被回应的心情，明天再让你看到。
- 感受：模板乙：我有一点失落，但也愿意把话说得柔软一点。
- 选择这个公开状态的原因：这条记录会先保持未公开，并在指定时间后允许共享。

```yaml session
ref: sess_template_pending
couple_ref: primary
author: B
event_id: evt_02
branch: pending_unlock
created_at: 2026-01-06 10:00:00
source_type: text
fields:
  content_time: 2026-01-06
  description: 我先记录下期待被回应的心情，明天再让你看到。
  feeling: 模板乙：我有一点失落，但也愿意把话说得柔软一点。
  reason: 这条记录会先保持未公开，并在指定时间后允许共享。
actions:
  - type: request_unlock
    at: 2026-01-06 11:00:00
    unlock_at: 2026-01-07 10:00:00
```

## 关系解除与数据销毁动作

这里留空表示模板不验证关系解除和数据销毁流程。需要验证时，按样例剧本补一条包含 `couple_ref`、`initiator`、`start_uncouple_at`、`destroy_at`、`reason` 的动作。

```yaml destroy_actions
[]
```
