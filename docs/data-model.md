# 数据模型

所有数据持久化当前落在 `data/database.db`（SQLite），代码层使用 `backend/domain/models` 中的 `dataclass` 作为一等模型。

当前对应关系：

- `users[]` ↔ `User`
- `couples[]` ↔ `Couple`
- `sessions[]` ↔ `SessionRecord`
- `auth_tokens[]` ↔ `AuthToken`

Repository 通过 `from_dict()` / `to_dict()` 在持久化字典记录与模型之间转换。

当前底层是 SQLite，但应用层仍以如下顶层对象结构在内存中读写，包含四类聚合数据。

```jsonc
{
  "users":       [ /* User 记录列表 */ ],
  "couples":     [ /* Couple 记录列表 */ ],
  "sessions":    [ /* Session 记录列表 */ ],
  "auth_tokens": [ /* 登录 Token 列表 */ ]
}
```

### User

```jsonc
{
  "user_id":       "usr_a1b2c3d4",          // 唯一 ID（注册时 UUID4 前 8 位）
  "username":      "Alice",                 // 用户名（2-20 字符，唯一）
  "password_hash": "e3b0c44298...",         // SHA-256(固定盐 + 密码)
  "couple_id":     "cp_12345678",           // 绑定的伴侣关系 ID，未绑定时为 null
  "joined_at":     "2026-04-30 12:00:00"    // 注册时间
}
```

### Couple

```jsonc
{
  "couple_id":             "cp_12345678",              // 情侣关系唯一 ID（创建时 UUID4 前 8 位）
  "user_a":                "usr_a1b2c3d4",             // 发起绑定请求的一方
  "user_b":                "usr_e5f6g7h8",             // 接收绑定请求的一方
  "created_at":            "2026-04-30 12:00:00",      // 绑定创建时间
  "couple_status":         "active",                   // 关系状态：pending_bind|active|frozen|dissolved
  "uncouple_initiated_by": null,                       // 谁发起解绑（user_a 或 user_b），无解绑时为 null
  "uncouple_initiated_at": null,                       // 解绑发起时间，无解绑时为 null
  "both_agreed_uncouple":  false,                      // 是否双方都同意解绑（true = 已确认解绑）
  "freeze_ends_at":        null                        // 冻结期结束时间，无冻结时为 null（冻结期90天）
}
```

### Session

```jsonc
{
  "session_id":          "20260430_120000",              // 记录唯一 ID（YYYYMMDD_HHMMSS 格式）
  "user_id":             "usr_a1b2c3d4",                 // 记录创建者的用户 ID
  "couple_id":           "cp_12345678",                  // 所属的伴侣关系 ID，单人记录时为 null
  "status":              "pending",                      // 记录状态：pending（灵感墙）| final（已归档）
  "visibility":          "private",                      // 可见性：private（私密）| pending_unlock（待解锁）| shared（共享）
  "unlock_requested_at": null,                           // 申请共享的时间，未申请时为 null
  "shared_at":           null,                           // 自动解锁共享的时间，未共享时为 null（90天后自动）
  "upload_time":         "2026-04-30 12:00:00",          // 记录上传/创建时间
  "archive_time":        "",                             // 记录归档时间，未归档时为空字符串
  "is_complete":         false,                          // 是否完整（所有必填字段已填）
  "edit_history":        [],                             // 编辑历史记录列表
  "files": [
    {
      "filename":      "20260430_120000_000_photo.jpg",  // 系统生成的规范化文件名
      "original_name": "photo.jpg",                      // 用户上传时的原始文件名
      "path":          "Assets/Pending/20260430_120000_000_photo.jpg"  // 文件存储路径
    }
  ],
  "source_type":  "file",                                // 数据来源：file（文件上传）| text（纯文本）
  "content_time": "2026-04-01",                          // 事件/内容发生的时间（非上传时间）
  "description":  "...",                                 // 记录描述/备注
  "feeling":      "...",                                 // 当时的感受
  "reason":       "",                                    // 记录原因/上传原因
  "comments": [
    {
      "id":         "20260430_120000_123456",            // 评论唯一 ID（时间戳+随机数）
      "author":     "usr_a1b2c3d4",                      // 评论作者的用户 ID
      "text":       "评论内容",                           // 评论文本
      "created_at": "2026-04-30 12:00:00"                // 评论创建时间
    }
  ]
}
```

### edit_history 条目

```jsonc
{
  "edited_at": "2026-04-30 13:00:00",       // 本次编辑的时间
  "changes": {
    "feeling": { "from": "旧感受", "to": "新感受" }  // 变更的字段及其新旧值对比
  }
}
```

### AuthToken

```jsonc
{
  "token":      "a1b2c3d4e5f6...",  // 登录 token（UUID hex 格式），用于持久化登录
  "user_id":    "usr_a1b2c3d4",      // 该 token 所属的用户 ID
  "expires_at": "2026-05-01 12:00:00" // token 过期时间（默认 24 小时）
}
```

---

*本文档与代码同步维护。数据结构变更时，请同步更新本文件。*
