# 状态机与分手协议

## 权限状态机详解

```text
创建记录
  │
  ▼
[private]  ←────────── 撤回申请（revoke_unlock）
  │
  │ 用户点击「申请共享」（request_unlock）
  │ 用户在 7 档预设或日历中自选开放时间，写入 SessionRecord.unlock_at
  ▼
[pending_unlock] ─── 可追加内容 / 改时间 / 立即解锁 / 撤回
  │
  │ application.maintenance.tick() 检查：
  │ now() >= unlock_at
  ▼
[shared] ──▶ 双方在「🏠 我们」可见，且 unlock_at == shared_at
```

**关键约束**

- 解锁推进基于 `SessionRecord.unlock_at`（用户在申请时自选）
- 申请共享时可选：立即 / 1 天 / 3 天 / 1 周 / 1 个月 / 90 天 / 自定义日期；默认 1 周
- `pending_unlock` 阶段可追加内容、改 `unlock_at`、立即解锁、撤回；「修改时间」「立即解锁」需勾选二次确认
- 不变量：`status == "shared"` 时 `unlock_at == shared_at`，由 `request_unlock` / `unlock_now` / `reschedule_unlock` 三条路径共同保证

---

## 分手协议详解

### 单方发起（`backend.application.couples.start_uncouple`）

```text
start_uncouple(user_id)
  │
  └─ application.couples.uncoupling.start_uncouple()
       ├─ couple_status → "frozen"
       ├─ 记录 uncouple_initiated_by, uncouple_initiated_at
       └─ freeze_ends_at = now() + 90 天

冻结期内：
  ├─ is_frozen() → True，全局只读
  ├─ 双方均可导出自己的文件（collect_export_files）
  └─ application.maintenance.tick() 到期 → destroy_couple_data() → dissolved
```

### 双方同意（`backend.application.couples.confirm_uncouple`）

```text
confirm_uncouple(user_id)
  │
  └─ application.couples.uncoupling.confirm_uncouple()
       └─ 立即调用 destroy_couple_data()
            ├─ 删除全部 sessions（按 couple_id 过滤）
            ├─ 删除对应磁盘文件和 .md 文件
            └─ 双方 user.couple_id → null，couple_status → "dissolved"
```

### 数据导出规则

导出仅包含：`session.user_id == 当前用户` 的所有 session 的文件（不含对方记录）。

> 当前实现尚未包含情感周报历史的导出（设计中预期 `export_couple_data()` 应输出 `reports.json`，待后续任务落地）。

---

*本文档与代码同步维护。状态流转规则变更时，请同步更新本文件。*
