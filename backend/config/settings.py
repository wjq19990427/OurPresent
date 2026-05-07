"""
Global constants and field schema configuration.
All modules import path constants and FIELD_SCHEMA from here.
"""

from pathlib import Path

# Relative to the repository root.
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "db.json"
ASSETS_DIR = BASE_DIR / "Assets"
PENDING_DIR = ASSETS_DIR / "Pending"
FINAL_DIR = ASSETS_DIR / "Final"

TEXT_EXTS = {".txt", ".md"}

TOKEN_EXPIRE_HOURS = 24

FIELD_SCHEMA: list[dict] = [
    {
        "key": "content_time",
        "label": "创建时间",
        "required": True,
        "type": "date_or_text",
        "placeholder": "选择或输入日期",
        "help": "这段内容实际发生或创作的时间",
    },
    {
        "key": "description",
        "label": "描述",
        "required": True,
        "type": "textarea",
        "placeholder": "用文字描述这段内容……",
        "help": "多模态内容必须填写，供后期智能体检索",
    },
    {
        "key": "feeling",
        "label": "感受",
        "required": True,
        "type": "textarea",
        "placeholder": "当时的感受……",
        "help": "",
    },
    {
        "key": "reason",
        "label": "记录原因",
        "required": False,
        "type": "textarea",
        "placeholder": "为什么想记录这个？（选填）",
        "help": "",
    },
]
