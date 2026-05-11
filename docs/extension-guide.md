# 扩展开发指南与第二阶段接口预留

以下内容从原始 `README` 迁移而来，尽量保留原始描述与代码片段。

## 扩展开发指南

### 1. 新增元数据字段

在 `backend/config/settings.py` 的 `FIELD_SCHEMA` 末尾追加一个字典，无需修改其他代码：

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

**a. 上传器允许新类型**（`frontend/streamlit_app/pages/tab_upload.py`）：

```python
files = st.file_uploader(
    "选择文件",
    type=["jpg", "jpeg", "png", "mp4", "txt", "md", "pdf"],  # 添加 "pdf"
    ...
)
```

**b. 若新类型属于「文字型」，在 `backend/config/settings.py` 追加扩展名**：

```python
TEXT_EXTS = {".txt", ".md", ".rst"}
```

**c. 在 `frontend/streamlit_app/components.py` 的 `_session_thumb` 和 `render_detail` 中添加预览分支**。

### 3. 替换密码哈希方案

生产环境应替换 `backend/infrastructure/database/users_repo.py` 中的 `_hash_password()` 和 `verify_password()`：

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
| `infrastructure.database.db.load_db()` | 读本地 SQLite 并组装整库字典 | 查询关系数据库 / NoSQL |
| `infrastructure.database.db.save_db()` | 全量写回本地 SQLite | 写入数据库 |
| `application.sessions.files.write_session_files()` | 写本地文件 | 上传到 OSS / S3 |
| `application.sessions.move_to_final()` | 本地 `shutil.move` | 远程 copy + delete |

### 5. 前后端分离迁移

当前 Streamlit 全栈架构的迁移路线：

1. `backend/infrastructure/database/*.py` + `backend/application/*` → 直接作为 FastAPI / Flask 的持久化与业务层
2. `backend/application/auth` + `backend/application/couples` → 封装为 `/register`、`/login`、`/couple/*` REST 接口
3. 权限检查（`can_view_session`）移至后端，前端不做权限判断
4. `frontend/streamlit_app/` → 替换为独立前端（React / Vue / Next.js），通过 API 通信
5. `backend/application/maintenance/ticking.py` 中的 `tick()` → 改为独立定时任务（cron / APScheduler）

### 6. 添加独立定时任务（生产环境）

当前 `tick()` 依赖页面加载触发。生产环境建议改为独立定时任务：

```python
# cron_worker.py（每小时执行一次）
from backend.application.maintenance import tick
from backend.infrastructure.database.db import load_db, save_db

if __name__ == "__main__":
    db = load_db()
    if tick(db):
        save_db(db)
```

配合 `crontab` 或 `APScheduler` 定期运行，确保冻结期到期时及时销毁数据。

---

## 第二阶段 · 情感周报已落地（v3.0.0）

情感周报已于 v3.0.0 完整落地。详见：

- 设计稿：[`weekly_report.md`](./weekly_report.md)
- L2 契约：[`api/app_reports.md`](./api/app_reports.md) / [`api/infra_ai.md`](./api/infra_ai.md)
- Opus 复审与技术债：[`phase2_audit.md`](./phase2_audit.md)

### 已实现的数据采样接口

`backend/infrastructure/ai/agent_skills.py`：

```python
def get_shared_sessions_for_rag(
    couple_id: str,
    window: tuple[datetime, datetime] | None = None,
) -> list[dict]
```

- 仅返回 `visibility == "shared"` 的 session
- 传 `window` 时按 `shared_at ∈ [start, end]` 过滤
- 字段未脱敏，由 application 层（如 `reports/semantic.py`）负责按白名单截字段后才传给 LLM

### LLM 输入字段白名单（已固化）

`backend/application/reports/semantic.py` 严格只把以下字段送入 LLM：

| 字段 | 用途 |
|------|------|
| `description` | 主要文本 |
| `feeling` | 情感 Metadata |
| `content_time` | 时间 Metadata |
| `user_id` | 作者标识（用于同日共鸣分组） |

明确**不传**：`session_id` / `couple_id` / 文件路径 / 文件名（防 LLM 回写引用与跨域污染）。

### 反原文引用兜底（已实现）

`backend/application/reports/guard.py` 对生成结果做最长公共子串检测：
- `weather.narrative` 与所有 `resonance.*.excerpt`
- 对照 source sessions 的 `description + feeling` 拼接语料
- 单一连续重合 ≥ 12 字符 → 整份 report 标 `status="failed"`，不展示

### 后续 AI 模块的 System Prompt 约束（备忘）

实时情感助手 / NVC 润色器接入时，System Prompt 仍需遵守：

- 禁止对双方行为做对错判断
- 回复格式强制遵循「观察 → 感受 → 需要 → 请求」四步结构（NVC 框架）
- 仅允许引用 `visibility == "shared"` 的数据，不得访问私密记录
- 不得在回复中具体引用对方记录的原文（防止隐私泄露）
- 字段白名单与 `reports/semantic.py` 对齐；切勿放宽

---

*本文档与代码同步维护。扩展接口或第二阶段规划变更时，请同步更新本文件。*
