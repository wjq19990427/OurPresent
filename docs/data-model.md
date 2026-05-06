# 数据模型

所有数据存储于 `data/db.json`，顶层为对象，包含四张表。

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
  "username":      "Alice",
  "password_hash": "e3b0c44298...",          // SHA-256(固定盐 + 密码)
  "couple_id":     "cp_12345678",           // 未绑定时为 null
  "joined_at":     "2026-04-30 12:00:00"
}
```

### Couple

```jsonc
{
  "couple_id":             "cp_12345678",
  "user_a":                "usr_a1b2c3d4",  // 发起绑定请求的一方
  "user_b":                "usr_e5f6g7h8",  // 收到请求的一方
  "created_at":            "2026-04-30 12:00:00",
  "couple_status":         "active",        // pending_bind|active|frozen|dissolved
  "uncouple_initiated_by": null,
  "uncouple_initiated_at": null,
  "both_agreed_uncouple":  false,
  "freeze_ends_at":        null
}
```

### Session

```jsonc
{
  "session_id":          "20260430_120000",  // YYYYMMDD_HHMMSS
  "user_id":             "usr_a1b2c3d4",
  "couple_id":           "cp_12345678",
  "status":              "pending",          // "pending" | "final"
  "visibility":          "private",          // "private" | "pending_unlock" | "shared"
  "unlock_requested_at": null,
  "shared_at":           null,
  "upload_time":         "2026-04-30 12:00:00",
  "archive_time":        "",
  "is_complete":         false,
  "edit_history":        [],
  "files": [
    {
      "filename":      "20260430_120000_000_photo.jpg",
      "original_name": "photo.jpg",
      "path":          "Assets/Pending/20260430_120000_000_photo.jpg"
    }
  ],
  "source_type":  "file",                    // "file" | "text"
  "content_time": "2026-04-01",
  "description":  "...",
  "feeling":      "...",
  "reason":       "",
  "comments": [
    {
      "id":         "20260430_120000_123456",
      "author":     "usr_a1b2c3d4",
      "text":       "评论内容",
      "created_at": "2026-04-30 12:00:00"
    }
  ]
}
```

### edit_history 条目

```jsonc
{
  "edited_at": "2026-04-30 13:00:00",
  "changes": {
    "feeling": { "from": "旧感受", "to": "新感受" }
  }
}
```

### AuthToken

```jsonc
{
  "token":      "a1b2c3d4e5f6...",  // UUID hex
  "user_id":    "usr_a1b2c3d4",
  "expires_at": "2026-05-01 12:00:00"
}
```

---

*本文档与代码同步维护。数据结构变更时，请同步更新本文件。*
