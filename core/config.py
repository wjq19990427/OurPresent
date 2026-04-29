"""
全局常量与字段 Schema 配置。
所有模块从这里导入路径常量和 FIELD_SCHEMA，不在其他地方重复定义。
"""

from pathlib import Path

# ── 路径常量（相对于项目根目录）──────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent   # 项目根：agents-a1c05cd7c4/
DATA_DIR    = BASE_DIR / "data"
DB_PATH     = DATA_DIR / "db.json"
ASSETS_DIR  = BASE_DIR / "Assets"
PENDING_DIR = ASSETS_DIR / "Pending"
FINAL_DIR   = ASSETS_DIR / "Final"

# ── 文件类型常量 ──────────────────────────────────────────────────────────
TEXT_EXTS = {".txt", ".md"}

# ── 登录 Token 有效期 ─────────────────────────────────────────────────────
TOKEN_EXPIRE_HOURS = 24

# ── 字段 Schema（驱动 UI 渲染，description 对文件型记录为必填）────────────
FIELD_SCHEMA: list[dict] = [
    {
        "key":         "content_time",
        "label":       "创建时间",
        "required":    True,
        "type":        "date_or_text",
        "placeholder": "选择或输入日期",
        "help":        "这段内容实际发生或创作的时间",
    },
    {
        "key":         "description",
        "label":       "描述",
        "required":    True,
        "type":        "textarea",
        "placeholder": "用文字描述这段内容……",
        "help":        "多模态内容必须填写，供后期智能体检索",
    },
    {
        "key":         "feeling",
        "label":       "感受",
        "required":    True,
        "type":        "textarea",
        "placeholder": "当时的感受……",
        "help":        "",
    },
    {
        "key":         "reason",
        "label":       "记录原因",
        "required":    False,
        "type":        "textarea",
        "placeholder": "为什么想记录这个？（选填）",
        "help":        "",
    },
]
