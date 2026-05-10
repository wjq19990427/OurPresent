### `backend/config/settings.py` — 全局配置

所有后端模块从这里导入路径常量和字段定义，避免重复定义。

#### 路径常量

```python
BASE_DIR    = Path(... )          # 项目根目录
DATA_DIR    = BASE_DIR / "data"
DB_PATH     = DATA_DIR / "database.db"
LEGACY_DB_PATH = DATA_DIR / "db.json"
ASSETS_DIR  = BASE_DIR / "Assets"
PENDING_DIR = ASSETS_DIR / "Pending"
FINAL_DIR   = ASSETS_DIR / "Final"
```

#### 其他常量

```python
TEXT_EXTS          = {".txt", ".md"}
TOKEN_EXPIRE_HOURS = 24
```

#### `FIELD_SCHEMA`

驱动 UI 渲染、字段校验和 Markdown 归档生成的核心配置。新增元数据字段时，优先在这里追加。

```python
FIELD_SCHEMA: list[dict] = [
    {
        "key": str,
        "label": str,
        "required": bool,
        "type": str,
        "placeholder": str,
        "help": str,
    },
    ...
]
```

`type` 当前可选值：

| type | 渲染控件 | 存储格式 |
|------|----------|----------|
| `"textarea"` | 多行文本框 | `str` |
| `"text"` | 单行文本框 | `str` |
| `"date_or_text"` | 日期选择 + 自由输入 | `str` |

当前默认字段：

| key | label | required | type |
|-----|-------|----------|------|
| `content_time` | 创建时间 | ✅ | `date_or_text` |
| `description` | 描述 | ✅（文件型） | `textarea` |
| `feeling` | 感受 | ✅ | `textarea` |
| `reason` | 记录原因 | ❌ | `textarea` |