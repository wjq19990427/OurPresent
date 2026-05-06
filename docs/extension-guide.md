# 扩展开发指南与第二阶段接口预留

以下内容从原始 `README` 迁移而来，尽量保留原始描述与代码片段。

## 扩展开发指南

### 1. 新增元数据字段

在 `core/config.py` 的 `FIELD_SCHEMA` 末尾追加一个字典，无需修改其他代码：

```python
{
    "key":         "location",
    "label":       "所在地",
    "required":    False,
    "type":        "text",
    "placeholder": "这段记忆发生在哪里？",
    "help":        "选填",
},
```

新字段自动出现在上传表单、灵感墙编辑区、已归档编辑区，并写入 `.md` 文件。旧有 session 读取时 `session.get("location", "")` 返回空字符串，不影响已有功能。

### 2. 新增支持的文件类型

**a. 上传器允许新类型**（`frontend/pages/tab_upload.py`）：

```python
files = st.file_uploader(
    "选择文件",
    type=["jpg", "jpeg", "png", "mp4", "txt", "md", "pdf"],  # 添加 "pdf"
    ...
)
```

**b. 若新类型属于「文字型」，在 `core/config.py` 追加扩展名**：

```python
TEXT_EXTS = {".txt", ".md", ".rst"}
```

**c. 在 `frontend/components.py` 的 `_session_thumb` 和 `render_detail` 中添加预览分支**。

### 3. 替换密码哈希方案

生产环境应替换 `backend/db_manager.py` 中的 `_hash_password()` 和 `verify_password()`：

```python
import bcrypt

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(user: dict, password: str) -> bool:
    return bcrypt.checkpw(password.encode(), user["password_hash"].encode())
```

### 4. 接入外部存储

替换以下函数即可切换存储后端：

| 函数（`backend/`） | 当前行为 | 替换方向 |
|--------------------|----------|----------|
| `db_manager.load_db()` | 读本地 JSON | 查询关系数据库 / NoSQL |
| `db_manager.save_db()` | 写本地 JSON | 写入数据库 |
| `utils/file_processor.write_files()` | 写本地文件 | 上传到 OSS / S3 |
| `session_manager.move_to_final()` | 本地 `shutil.move` | 远程 copy + delete |

### 5. 前后端分离迁移

当前 Streamlit 全栈架构的迁移路线：

1. `backend/db_manager.py` + `backend/session_manager.py` + `backend/auth_manager.py` → 直接作为 FastAPI / Flask 数据访问和业务层
2. `backend/auth_manager.py` → 封装为 `/register`、`/login`、`/couple/*` REST 接口
3. 权限检查（`can_view_session`）移至后端，前端不做权限判断
4. `frontend/` → 替换为独立前端（React / Vue），通过 API 通信
5. `core/state_machine.tick()` → 改为独立定时任务（cron / APScheduler）

### 6. 添加独立定时任务（生产环境）

当前 `tick()` 依赖页面加载触发。生产环境建议改为独立定时任务：

```python
# cron_worker.py（每小时执行一次）
from backend.db_manager import load_db, save_db
from core.state_machine import tick

if __name__ == "__main__":
    db = load_db()
    if tick(db):
        save_db(db)
```

配合 `crontab` 或 `APScheduler` 定期运行，确保冻结期到期时及时销毁数据。

---

## 第二阶段接口预留

第一阶段已为 AI 智能体接入预留完整边界：

### RAG 向量化接口

每条 Session 包含以下可作为 Chunk + Metadata 的字段：

| 字段 | RAG 用途 |
|------|----------|
| `description` | 主要文本 Chunk（文件型必填） |
| `feeling` | 情感 Metadata |
| `content_time` | 时间 Metadata |
| `visibility` | 过滤条件（**只允许检索 `shared` 记录**） |
| `couple_id` | 关系域隔离 |
| `user_id` | 作者标识 |
| `shared_at` | 共享时间 Metadata |

**检索过滤规则（情感周报 Agent 必须遵守）**：

```python
# core/agent_skills.py 已实现此过滤
rag_chunks = [
    s for s in db["sessions"]
    if s.get("couple_id") == target_couple_id
    and s.get("visibility") == "shared"
]
```

### 智能体 System Prompt 约束（备忘）

实时情感助手接入时，System Prompt 需包含：

- 禁止对双方行为做对错判断
- 回复格式强制遵循「观察 → 感受 → 需要 → 请求」四步结构（NVC 框架）
- 仅允许引用 `visibility == "shared"` 的数据，不得访问私密记录
- 不得在回复中具体引用对方记录的原文（防止隐私泄露）

---

*本文档与代码同步维护。扩展接口或第二阶段规划变更时，请同步更新本文件。*
