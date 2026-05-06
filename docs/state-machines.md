# 状态机与分手协议

## 权限状态机详解

```text
创建记录
  │
  ▼
[private]  ←────────── 撤回申请（revoke_unlock）
  │
  │ 用户点击「申请共享」（request_unlock）
  ▼
[pending_unlock]
  │
  │ state_machine.tick() 检查：
  │ now() - upload_time ≥ 90 天
  ▼
[shared] ──▶ 伴侣在「情侣空间」可见
```

**关键约束**

- 解锁等待基于 `upload_time`（内容上传时间），而非 `unlock_requested_at`（申请时间）
- 无法通过提前申请绕过 90 天限制
- `pending_unlock` 阶段可随时撤回，不影响 90 天计时；下次重新申请时，已流逝时间仍计入

---

## 分手协议详解

### 单方发起（`auth_manager.start_uncouple`）

```text
start_uncouple(user_id)
  │
  └─ session_manager.initiate_uncouple(user_id)
       ├─ couple_status → "frozen"
       ├─ 记录 uncouple_initiated_by, uncouple_initiated_at
       └─ freeze_ends_at = now() + 90 天

冻结期内：
  ├─ is_frozen() → True，全局只读
  ├─ 双方均可导出自己的文件（collect_export_files）
  └─ state_machine.tick() 到期 → destroy_couple_data() → dissolved
```

### 双方同意（`auth_manager.confirm_uncouple`）

```text
confirm_uncouple(user_id)
  │
  └─ session_manager.agree_uncouple(user_id)
       └─ 立即调用 destroy_couple_data()
            ├─ 删除全部 sessions（按 couple_id 过滤）
            ├─ 删除对应磁盘文件和 .md 文件
            └─ 双方 user.couple_id → null，couple_status → "dissolved"
```

### 数据导出规则

导出仅包含：`session.user_id == 当前用户` 的所有 session 的文件（不含对方记录、AI 生成报告）。

---

*本文档与代码同步维护。状态流转规则变更时，请同步更新本文件。*
