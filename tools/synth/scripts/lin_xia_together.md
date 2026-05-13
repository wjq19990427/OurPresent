---
schema_version: 1
outcome: together
outcome_reason: 林澈和夏予仍愿意通过延时共享把误会慢慢说清。
metadata:
  name: lin_xia_together
  weeks: 6
  generated_at: 2026-01-05 09:00:00
  notes: 人可读剧本；重放时不调用大模型。
personas:
  seed_id: lin_xia_together
  start_date: 2026-01-05
  a:
    id: A
    username: 合成林澈
    display_name: 林澈
    tone: 敏感但愿意承担，遇到压力会先收紧自己
    communication_style: 先写下来整理，再用短句确认边界
    relationship_stage: 摩擦
    emotional_anchors:
      - 刚搬进共同租住的小房子
      - 工作上线周期让作息变得不稳定
      - 想证明自己可靠但害怕显得控制
  b:
    id: B
    username: 合成夏予
    display_name: 夏予
    tone: 外向温和，失落时容易用玩笑带过
    communication_style: 偏即时沟通，希望情绪被当场接住
    relationship_stage: 摩擦
    emotional_anchors:
      - 期待共同生活里的仪式感
      - 近期和朋友的比较让安全感下降
      - 想要更多主动的解释和拥抱
couples:
  - ref: primary
    a:
      id: A
      username: 合成林澈
      display_name: 林澈
      tone: 敏感但愿意承担，遇到压力会先收紧自己
      communication_style: 先写下来整理，再用短句确认边界
      relationship_stage: 摩擦
      emotional_anchors:
        - 刚搬进共同租住的小房子
        - 工作上线周期让作息变得不稳定
        - 想证明自己可靠但害怕显得控制
    b:
      id: B
      username: 合成夏予
      display_name: 夏予
      tone: 外向温和，失落时容易用玩笑带过
      communication_style: 偏即时沟通，希望情绪被当场接住
      relationship_stage: 摩擦
      emotional_anchors:
        - 期待共同生活里的仪式感
        - 近期和朋友的比较让安全感下降
        - 想要更多主动的解释和拥抱
    password: synth-pass-20
coverage:
  covered:
    - 永久私密
    - 延时共享_1小时
    - 延时共享_1天
    - 延时共享_1周
    - 延时共享_1个月
    - 调整解锁时间_推后
    - 调整解锁时间_提前
    - 立即解锁
    - 伴侣读取后评论互动
  skipped:
    - 冻结期销毁完整链路
---

# lin_xia_together

结局：`together`。林澈和夏予仍愿意通过延时共享把误会慢慢说清。

这份 Markdown 是合成数据的唯一剧本来源。上方 frontmatter 放角色卡、关系
和覆盖范围等结构字段；下方正文按时间顺序排列事件、记录和后续行为。

编辑时优先改每个 `session` 代码块里的 `fields.description`、
`fields.feeling`、`fields.reason`，不要改 `schema_version` 或关系引用字段，
除非你确实要改变剧本结构。

## 时间线与记录

### 2026-01-05 · evt_01 · 周一早晨一起整理新家厨房

- 事件视角：`shared`
- 由哪条记录继续发展：无
- A 的内心：林澈：我想把生活过得有秩序，也怕自己的急躁吓到对方。
- B 的内心：夏予：我感到被照顾，也担心自己跟不上对方的节奏。

```yaml timeline
id: evt_01
date: 2026-01-05
perspective: shared
theme: 周一早晨一起整理新家厨房
seed_from: null
inner_voice:
  A: 林澈：我想把生活过得有秩序，也怕自己的急躁吓到对方。
  B: 夏予：我感到被照顾，也担心自己跟不上对方的节奏。
```

#### sess_01_private · 作者 A · private

- 写入关系：`primary`
- 创建时间：`2026-01-05 09:00:00`
- 描述：周一早晨一起整理新家厨房
- 感受：林澈：我想把生活过得有秩序，也怕自己的急躁吓到对方。
- 选择这个公开状态的原因：这是一段只想先放在自己心里的记录。

```yaml session
ref: sess_01_private
couple_ref: primary
author: A
event_id: evt_01
branch: private
created_at: 2026-01-05 09:00:00
source_type: text
fields:
  content_time: 2026-01-05
  description: 周一早晨一起整理新家厨房
  feeling: 林澈：我想把生活过得有秩序，也怕自己的急躁吓到对方。
  reason: 这是一段只想先放在自己心里的记录。
actions: []
```

### 2026-01-10 · evt_02 · 项目上线前的深夜加班

- 事件视角：`A`
- 由哪条记录继续发展：无
- A 的内心：林澈：我很疲惫，但不想把压力全部倒给伴侣。
- B 的内心：夏予：我想靠近，却不知道怎样不打扰。

```yaml timeline
id: evt_02
date: 2026-01-10
perspective: A
theme: 项目上线前的深夜加班
seed_from: null
inner_voice:
  A: 林澈：我很疲惫，但不想把压力全部倒给伴侣。
  B: 夏予：我想靠近，却不知道怎样不打扰。
```

#### sess_02_pending_1h · 作者 B · pending_unlock

- 写入关系：`primary`
- 创建时间：`2026-01-10 09:01:00`
- 描述：项目上线前的深夜加班
- 感受：夏予：我想靠近，却不知道怎样不打扰。
- 选择这个公开状态的原因：想让对方稍后看到，而不是在情绪最满的时候立刻共享。

```yaml session
ref: sess_02_pending_1h
couple_ref: primary
author: B
event_id: evt_02
branch: pending_unlock
created_at: 2026-01-10 09:01:00
source_type: text
fields:
  content_time: 2026-01-10
  description: 项目上线前的深夜加班
  feeling: 夏予：我想靠近，却不知道怎样不打扰。
  reason: 想让对方稍后看到，而不是在情绪最满的时候立刻共享。
actions:
  - type: request_unlock
    at: 2026-01-10 10:01:00
    unlock_at: 2026-01-10 11:01:00
```

### 2026-01-15 · evt_03 · 临时取消的周末短途旅行

- 事件视角：`B`
- 由哪条记录继续发展：无
- A 的内心：林澈：我知道计划被打乱不是谁的错，可还是有点失落。
- B 的内心：夏予：我表面说没关系，其实很想被认真安慰。

```yaml timeline
id: evt_03
date: 2026-01-15
perspective: B
theme: 临时取消的周末短途旅行
seed_from: null
inner_voice:
  A: 林澈：我知道计划被打乱不是谁的错，可还是有点失落。
  B: 夏予：我表面说没关系，其实很想被认真安慰。
```

#### sess_03_pending_1d · 作者 A · pending_unlock

- 写入关系：`primary`
- 创建时间：`2026-01-15 09:02:00`
- 描述：临时取消的周末短途旅行
- 感受：林澈：我知道计划被打乱不是谁的错，可还是有点失落。
- 选择这个公开状态的原因：想让对方稍后看到，而不是在情绪最满的时候立刻共享。

```yaml session
ref: sess_03_pending_1d
couple_ref: primary
author: A
event_id: evt_03
branch: pending_unlock
created_at: 2026-01-15 09:02:00
source_type: text
fields:
  content_time: 2026-01-15
  description: 临时取消的周末短途旅行
  feeling: 林澈：我知道计划被打乱不是谁的错，可还是有点失落。
  reason: 想让对方稍后看到，而不是在情绪最满的时候立刻共享。
actions:
  - type: request_unlock
    at: 2026-01-15 10:02:00
    unlock_at: 2026-01-16 09:02:00
```

### 2026-01-20 · evt_04 · 读到一条旧消息后的误会

- 事件视角：`shared`
- 由哪条记录继续发展：无
- A 的内心：林澈：我害怕被误解，于是说话变硬了。
- B 的内心：夏予：我听见的是防备，不是解释。

```yaml timeline
id: evt_04
date: 2026-01-20
perspective: shared
theme: 读到一条旧消息后的误会
seed_from: null
inner_voice:
  A: 林澈：我害怕被误解，于是说话变硬了。
  B: 夏予：我听见的是防备，不是解释。
```

#### sess_04_reschedule_later · 作者 B · pending_unlock

- 写入关系：`primary`
- 创建时间：`2026-01-20 09:03:00`
- 描述：读到一条旧消息后的误会
- 感受：夏予：我听见的是防备，不是解释。
- 选择这个公开状态的原因：想让对方稍后看到，而不是在情绪最满的时候立刻共享。

```yaml session
ref: sess_04_reschedule_later
couple_ref: primary
author: B
event_id: evt_04
branch: pending_unlock
created_at: 2026-01-20 09:03:00
source_type: text
fields:
  content_time: 2026-01-20
  description: 读到一条旧消息后的误会
  feeling: 夏予：我听见的是防备，不是解释。
  reason: 想让对方稍后看到，而不是在情绪最满的时候立刻共享。
actions:
  - type: request_unlock
    at: 2026-01-20 10:03:00
    unlock_at: 2026-01-27 09:03:00
  - type: reschedule_unlock
    at: 2026-01-20 11:03:00
    unlock_at: 2026-02-03 09:03:00
```

### 2026-01-25 · evt_05 · 给对方准备没有说出口的小礼物

- 事件视角：`A`
- 由哪条记录继续发展：无
- A 的内心：林澈：我想慢慢修补，不想显得像在讨好。
- B 的内心：夏予：我隐约感到对方在努力，但还没准备好回应。

```yaml timeline
id: evt_05
date: 2026-01-25
perspective: A
theme: 给对方准备没有说出口的小礼物
seed_from: null
inner_voice:
  A: 林澈：我想慢慢修补，不想显得像在讨好。
  B: 夏予：我隐约感到对方在努力，但还没准备好回应。
```

#### sess_05_reschedule_earlier_1m · 作者 A · pending_unlock

- 写入关系：`primary`
- 创建时间：`2026-01-25 09:04:00`
- 描述：给对方准备没有说出口的小礼物
- 感受：林澈：我想慢慢修补，不想显得像在讨好。
- 选择这个公开状态的原因：想让对方稍后看到，而不是在情绪最满的时候立刻共享。

```yaml session
ref: sess_05_reschedule_earlier_1m
couple_ref: primary
author: A
event_id: evt_05
branch: pending_unlock
created_at: 2026-01-25 09:04:00
source_type: text
fields:
  content_time: 2026-01-25
  description: 给对方准备没有说出口的小礼物
  feeling: 林澈：我想慢慢修补，不想显得像在讨好。
  reason: 想让对方稍后看到，而不是在情绪最满的时候立刻共享。
actions:
  - type: request_unlock
    at: 2026-01-25 10:04:00
    unlock_at: 2026-03-11 09:04:00
  - type: reschedule_unlock
    at: 2026-02-10 09:04:00
    unlock_at: 2026-02-11 09:04:00
```

### 2026-01-30 · evt_06 · 一次共享记录被读到后的回复

- 事件视角：`B`
- 由哪条记录继续发展：sess_06_share_now
- A 的内心：林澈：我终于敢把那天的心情放出来一点。
- B 的内心：夏予：读到以后我很心疼，也更愿意下一次先问清楚。

```yaml timeline
id: evt_06
date: 2026-01-30
perspective: B
theme: 一次共享记录被读到后的回复
seed_from: sess_06_share_now
inner_voice:
  A: 林澈：我终于敢把那天的心情放出来一点。
  B: 夏予：读到以后我很心疼，也更愿意下一次先问清楚。
```

#### sess_06_share_now · 作者 B · shared

- 写入关系：`primary`
- 创建时间：`2026-01-30 09:05:00`
- 描述：一次共享记录被读到后的回复
- 感受：夏予：读到以后我很心疼，也更愿意下一次先问清楚。
- 选择这个公开状态的原因：决定提前把话说开，给下一次互动一个入口。

```yaml session
ref: sess_06_share_now
couple_ref: primary
author: B
event_id: evt_06
branch: shared
created_at: 2026-01-30 09:05:00
source_type: text
fields:
  content_time: 2026-01-30
  description: 一次共享记录被读到后的回复
  feeling: 夏予：读到以后我很心疼，也更愿意下一次先问清楚。
  reason: 决定提前把话说开，给下一次互动一个入口。
actions:
  - type: request_unlock
    at: 2026-01-30 10:05:00
    unlock_at: 2026-02-06 09:05:00
  - type: unlock_now
    at: 2026-01-30 11:05:00
  - type: add_comment
    author: A
    text: 我读到了，也终于明白那天你不是冷淡，是怕打扰我。
    at: 2026-01-30 12:05:00
```

### 2026-02-04 · evt_07 · 月末一起复盘关系节奏

- 事件视角：`shared`
- 由哪条记录继续发展：无
- A 的内心：林澈：我希望我们的亲密可以不靠猜。
- B 的内心：夏予：我希望被看见的同时，也保留自己的空间。

```yaml timeline
id: evt_07
date: 2026-02-04
perspective: shared
theme: 月末一起复盘关系节奏
seed_from: null
inner_voice:
  A: 林澈：我希望我们的亲密可以不靠猜。
  B: 夏予：我希望被看见的同时，也保留自己的空间。
```

这一天没有要写入数据库的记录。

### 2026-02-09 · evt_08 · 雨天在地铁站等到对方

- 事件视角：`A`
- 由哪条记录继续发展：无
- A 的内心：林澈：我发现自己还是很珍惜这些普通时刻。
- B 的内心：夏予：我愿意把紧张放慢一点。

```yaml timeline
id: evt_08
date: 2026-02-09
perspective: A
theme: 雨天在地铁站等到对方
seed_from: null
inner_voice:
  A: 林澈：我发现自己还是很珍惜这些普通时刻。
  B: 夏予：我愿意把紧张放慢一点。
```

这一天没有要写入数据库的记录。

## 关系解除与数据销毁动作

这里描述需要先进入解除关系冻结期、再销毁这对关系内数据的动作。
列表为空时表示这份剧本不验证销毁流程。

```yaml destroy_actions
[]
```
