"""
OurPresent — 数据层
所有磁盘 I/O、状态机推进、数据销毁均在此模块完成。
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ── 路径常量 ──────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
DB_PATH    = DATA_DIR / "db.json"
ASSETS_DIR = BASE_DIR / "Assets"
PENDING_DIR = ASSETS_DIR / "Pending"
FINAL_DIR   = ASSETS_DIR / "Final"

TEXT_EXTS = {".txt", ".md"}

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
        "required":    True,   # 文件型记录强制必填（RAG 语料）
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

# ── 目录初始化 ────────────────────────────────────────────────────────────
def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)


# ── 数据库读写 ────────────────────────────────────────────────────────────
_EMPTY_DB: dict = {"users": [], "couples": [], "sessions": [], "auth_tokens": []}


def load_db() -> dict:
    if not DB_PATH.exists():
        return {k: list(v) for k, v in _EMPTY_DB.items()}
    try:
        raw = json.loads(DB_PATH.read_text(encoding="utf-8"))
        # 兼容旧格式（纯 sessions 列表）
        if isinstance(raw, list):
            return {"users": [], "couples": [], "sessions": raw, "auth_tokens": []}
        if "auth_tokens" not in raw:
            raw["auth_tokens"] = []
        return raw
    except (json.JSONDecodeError, OSError):
        return {k: list(v) for k, v in _EMPTY_DB.items()}


def save_db(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── 用户 CRUD ─────────────────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    salt = "ourpresent_salt_v1"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def create_user(username: str, password: str) -> dict:
    """创建新用户，返回 user 记录。调用方需确保 username 唯一。"""
    db = load_db()
    user_id = "usr_" + uuid.uuid4().hex[:8]
    user = {
        "user_id":       user_id,
        "username":      username,
        "password_hash": _hash_password(password),
        "couple_id":     None,
        "joined_at":     _now_str(),
    }
    db["users"].append(user)
    save_db(db)
    return user


def get_user_by_username(username: str) -> Optional[dict]:
    db = load_db()
    for u in db["users"]:
        if u["username"] == username:
            return u
    return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    db = load_db()
    for u in db["users"]:
        if u["user_id"] == user_id:
            return u
    return None


def verify_password(user: dict, password: str) -> bool:
    return user["password_hash"] == _hash_password(password)


def _update_user(user_id: str, fields: dict) -> None:
    db = load_db()
    for u in db["users"]:
        if u["user_id"] == user_id:
            u.update(fields)
            break
    save_db(db)


# ── 情侣绑定 CRUD ─────────────────────────────────────────────────────────
def send_couple_request(from_user_id: str, to_user_id: str) -> dict:
    """发起绑定请求，返回新建的 couple 记录。"""
    db = load_db()
    couple_id = "cp_" + uuid.uuid4().hex[:8]
    couple = {
        "couple_id":             couple_id,
        "user_a":                from_user_id,
        "user_b":                to_user_id,
        "created_at":            _now_str(),
        "couple_status":         "pending_bind",   # "pending_bind"|"active"|"frozen"|"dissolved"
        "uncouple_initiated_by": None,
        "uncouple_initiated_at": None,
        "both_agreed_uncouple":  False,
        "freeze_ends_at":        None,
    }
    db["couples"].append(couple)
    save_db(db)
    return couple


def get_couple_by_id(couple_id: str) -> Optional[dict]:
    db = load_db()
    for c in db["couples"]:
        if c["couple_id"] == couple_id:
            return c
    return None


def get_couple_for_user(user_id: str) -> Optional[dict]:
    """返回该用户当前有效的 couple 记录（active/frozen，不含已解散）。"""
    db = load_db()
    for c in db["couples"]:
        if c["couple_status"] in ("pending_bind", "active", "frozen"):
            if user_id in (c["user_a"], c["user_b"]):
                return c
    return None


def get_pending_requests_for_user(user_id: str) -> list[dict]:
    """返回目标为该用户且状态为 pending_bind 的绑定请求列表。"""
    db = load_db()
    return [
        c for c in db["couples"]
        if c["couple_status"] == "pending_bind" and c["user_b"] == user_id
    ]


def accept_couple_request(couple_id: str) -> None:
    """接受绑定，双方 user 的 couple_id 更新。"""
    db = load_db()
    couple = None
    for c in db["couples"]:
        if c["couple_id"] == couple_id:
            c["couple_status"] = "active"
            couple = c
            break
    if couple:
        for u in db["users"]:
            if u["user_id"] in (couple["user_a"], couple["user_b"]):
                u["couple_id"] = couple_id
    save_db(db)


def reject_couple_request(couple_id: str) -> None:
    db = load_db()
    db["couples"] = [c for c in db["couples"] if c["couple_id"] != couple_id]
    save_db(db)


def _update_couple(couple_id: str, fields: dict) -> None:
    db = load_db()
    for c in db["couples"]:
        if c["couple_id"] == couple_id:
            c.update(fields)
            break
    save_db(db)


# ── 解绑协议 ──────────────────────────────────────────────────────────────
def initiate_uncouple(user_id: str) -> None:
    """单方发起分手，进入 3 个月冻结期。"""
    couple = get_couple_for_user(user_id)
    if not couple or couple["couple_status"] != "active":
        return
    freeze_ends = datetime.now() + timedelta(days=90)
    _update_couple(couple["couple_id"], {
        "couple_status":         "frozen",
        "uncouple_initiated_by": user_id,
        "uncouple_initiated_at": _now_str(),
        "freeze_ends_at":        freeze_ends.strftime("%Y-%m-%d %H:%M:%S"),
    })


def agree_uncouple(user_id: str) -> None:
    """对方同意解绑，立即销毁数据。"""
    couple = get_couple_for_user(user_id)
    if not couple:
        return
    _update_couple(couple["couple_id"], {"both_agreed_uncouple": True})
    destroy_couple_data(couple["couple_id"])


# ── 数据销毁 ──────────────────────────────────────────────────────────────
def destroy_couple_data(couple_id: str) -> None:
    """销毁情侣关系的全部数据（sessions + 文件）。"""
    db = load_db()

    # 删除所有相关 sessions 及文件
    to_remove = [s for s in db["sessions"] if s.get("couple_id") == couple_id]
    for s in to_remove:
        _delete_session_files(s)
    db["sessions"] = [s for s in db["sessions"] if s.get("couple_id") != couple_id]

    # 更新 couple 状态 & 清理用户 couple_id
    for c in db["couples"]:
        if c["couple_id"] == couple_id:
            c["couple_status"] = "dissolved"
    for u in db["users"]:
        if u.get("couple_id") == couple_id:
            u["couple_id"] = None

    save_db(db)


def _delete_session_files(session: dict) -> None:
    for f in session.get("files", []):
        p = Path(f.get("path", ""))
        if p.exists():
            p.unlink(missing_ok=True)
    # 删除对应的 .md
    md = FINAL_DIR / f"{session['session_id']}.md"
    md.unlink(missing_ok=True)


# ── 状态机推进（每次加载时调用）─────────────────────────────────────────
def tick(db: dict) -> bool:
    """推进时间锁和冻结期，如有变化返回 True（调用方应重新 save_db）。"""
    now = datetime.now()
    changed = False

    # 时间锁：pending_unlock → shared（满 90 天）
    for s in db["sessions"]:
        if s.get("visibility") == "pending_unlock":
            upload_dt = _parse_dt(s.get("upload_time", ""))
            if upload_dt and (now - upload_dt).days >= 90:
                s["visibility"] = "shared"
                s["shared_at"]  = _now_str()
                changed = True

    # 冻结期到期 → 销毁
    for c in db["couples"]:
        if c.get("couple_status") == "frozen" and c.get("freeze_ends_at"):
            ends = _parse_dt(c["freeze_ends_at"])
            if ends and now >= ends:
                destroy_couple_data(c["couple_id"])
                changed = True

    # 过期登录 token 清理
    before = len(db.get("auth_tokens", []))
    db["auth_tokens"] = [
        t for t in db.get("auth_tokens", [])
        if _parse_dt(t.get("expires_at", "")) and _parse_dt(t["expires_at"]) > now
    ]
    if len(db["auth_tokens"]) != before:
        changed = True

    return changed


def load_db_with_tick() -> dict:
    """加载 DB 并推进状态机，供 UI 层使用。"""
    db = load_db()
    if tick(db):
        save_db(db)
        db = load_db()
    return db


# ── Session CRUD ──────────────────────────────────────────────────────────
def _is_text_session(session: dict) -> bool:
    if session.get("source_type") == "text":
        return True
    exts = {Path(f["filename"]).suffix.lower() for f in session.get("files", [])}
    return bool(exts) and exts.issubset(TEXT_EXTS)


def validate_session(session: dict) -> list[str]:
    """返回未填写的必填字段 label 列表；空列表表示完整。"""
    skip = {"description"} if _is_text_session(session) else set()
    return [
        f["label"]
        for f in FIELD_SCHEMA
        if f["required"] and f["key"] not in skip
        and not str(session.get(f["key"], "")).strip()
    ]


def _build_session_base(user_id: str, couple_id: Optional[str]) -> dict:
    now = datetime.now()
    sid = now.strftime("%Y%m%d_%H%M%S")
    return {
        "session_id":          sid,
        "user_id":             user_id,
        "couple_id":           couple_id,
        "status":              "pending",
        "visibility":          "private",
        "unlock_requested_at": None,
        "shared_at":           None,
        "upload_time":         now.strftime("%Y-%m-%d %H:%M:%S"),
        "archive_time":        "",
        "is_complete":         False,
        "edit_history":        [],
        "files":               [],
        "source_type":         "file",
        "content_time":        "",
        "description":         "",
        "feeling":             "",
        "reason":              "",
        "comments":            [],
    }


def save_session_pending(
    user_id: str,
    couple_id: Optional[str],
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None:
    db = load_db()
    s = _build_session_base(user_id, couple_id)
    s["source_type"] = source_type
    s.update({k: v for k, v in field_values.items() if k in {f["key"] for f in FIELD_SCHEMA}})
    s["files"] = _write_files(s["session_id"], file_data_list, PENDING_DIR)
    s["is_complete"] = not validate_session(s)
    db["sessions"].append(s)
    save_db(db)


def save_session_final(
    user_id: str,
    couple_id: Optional[str],
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None:
    db = load_db()
    s = _build_session_base(user_id, couple_id)
    s["source_type"] = source_type
    s["status"]       = "final"
    s["archive_time"] = _now_str()
    s.update({k: v for k, v in field_values.items() if k in {f["key"] for f in FIELD_SCHEMA}})
    s["files"] = _write_files(s["session_id"], file_data_list, FINAL_DIR)
    s["is_complete"] = True
    db["sessions"].append(s)
    save_db(db)
    _write_md(s)


def move_to_final(session_id: str) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id:
            new_files = []
            for f in s["files"]:
                src = Path(f["path"])
                dst = FINAL_DIR / src.name
                if src.exists():
                    shutil.move(str(src), str(dst))
                f["path"] = str(dst)
                new_files.append(f)
            s["files"]        = new_files
            s["status"]       = "final"
            s["archive_time"] = _now_str()
            s["is_complete"]  = True
            save_db(db)
            _write_md(s)
            return


def update_session_fields(session_id: str, new_values: dict) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] != session_id:
            continue
        valid_keys = {f["key"] for f in FIELD_SCHEMA}
        if s["status"] == "final":
            changes = {}
            for k, v in new_values.items():
                if k in valid_keys and s.get(k) != v:
                    if k == "description" and _is_text_session(s):
                        continue
                    changes[k] = {"from": s.get(k, ""), "to": v}
            if changes:
                s["edit_history"].append({
                    "edited_at": _now_str(),
                    "changes":   changes,
                })
        for k, v in new_values.items():
            if k in valid_keys:
                s[k] = v
        s["is_complete"] = not validate_session(s)
        save_db(db)
        if s["status"] == "final":
            _write_md(s)
        return


def request_unlock(session_id: str) -> None:
    """用户触发时间锁授权，标记申请时间。"""
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id and s.get("visibility") == "private":
            s["visibility"]          = "pending_unlock"
            s["unlock_requested_at"] = _now_str()
            break
    save_db(db)


def revoke_unlock(session_id: str) -> None:
    """撤回授权申请，恢复为 private。"""
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id and s.get("visibility") == "pending_unlock":
            s["visibility"]          = "private"
            s["unlock_requested_at"] = None
            break
    save_db(db)


# ── 评论 CRUD ─────────────────────────────────────────────────────────────
def add_comment(session_id: str, author_id: str, text: str) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id:
            now = datetime.now()
            s["comments"].append({
                "id":         now.strftime("%Y%m%d_%H%M%S_") + str(now.microsecond),
                "author":     author_id,
                "text":       text,
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            })
            save_db(db)
            if s["status"] == "final":
                _write_md(s)
            return


def delete_comment(session_id: str, comment_id: str) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id:
            s["comments"] = [c for c in s["comments"] if c["id"] != comment_id]
            save_db(db)
            if s["status"] == "final":
                _write_md(s)
            return


# ── 数据导出（冻结期内，仅导出自己的数据）────────────────────────────────
def collect_export_files(user_id: str) -> list[Path]:
    """返回该用户可导出的文件路径列表。"""
    db = load_db()
    paths: list[Path] = []
    for s in db["sessions"]:
        if s.get("user_id") != user_id:
            continue
        for f in s.get("files", []):
            p = Path(f.get("path", ""))
            if p.exists():
                paths.append(p)
    return paths


# ── 文件写入工具 ──────────────────────────────────────────────────────────
def _write_files(
    session_id: str,
    file_data_list: list[tuple[bytes, str]],
    target_dir: Path,
) -> list[dict]:
    result = []
    for i, (data, original_name) in enumerate(file_data_list):
        safe_name  = _safe_filename(original_name)
        stored     = f"{session_id}_{i:03d}_{safe_name}"
        dest       = target_dir / stored
        dest.write_bytes(data)
        result.append({
            "filename":      stored,
            "original_name": original_name,
            "path":          str(dest),
        })
    return result


def _safe_filename(name: str) -> str:
    illegal = r'\/:*?"<>|'
    for ch in illegal:
        name = name.replace(ch, "_")
    return name


# ── Markdown 生成 ─────────────────────────────────────────────────────────
def _write_md(session: dict) -> None:
    names   = [f["original_name"] for f in session.get("files", [])]
    title   = names[0] if names else session["session_id"]
    count   = len(names)
    lines   = [
        f"# {title}（共 {count} 个文件）\n",
        f"**上传时间**：{session.get('upload_time', '')}\n",
        f"**归档时间**：{session.get('archive_time', '')}\n",
    ]
    for field in FIELD_SCHEMA:
        val = session.get(field["key"], "")
        if val:
            lines += [f"\n## {field['label']}\n", f"{val}\n"]

    comments = session.get("comments", [])
    if comments:
        lines.append("\n---\n\n## 评论区\n")
        for c in comments:
            lines += [f"\n**{c['created_at']}**\n\n{c['text']}\n"]

    history = session.get("edit_history", [])
    if history:
        lines.append("\n---\n\n## 编辑历史\n")
        for h in reversed(history):
            lines.append(f"\n### {h['edited_at']}\n")
            for k, v in h["changes"].items():
                label = next((f["label"] for f in FIELD_SCHEMA if f["key"] == k), k)
                lines.append(f"- **{label}**：「{v['from']}」→「{v['to']}」\n")

    md_path = FINAL_DIR / f"{session['session_id']}.md"
    md_path.write_text("".join(lines), encoding="utf-8")


# ── 工具函数 ──────────────────────────────────────────────────────────────
def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


# ── 登录 Token（持久化登录状态）──────────────────────────────────────────
TOKEN_EXPIRE_HOURS = 24


def create_auth_token(user_id: str) -> str:
    """创建登录 token，写入 DB，返回 token 字符串。"""
    db = load_db()
    token = uuid.uuid4().hex
    expires_at = datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    db.setdefault("auth_tokens", []).append({
        "token":      token,
        "user_id":    user_id,
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_db(db)
    return token


def validate_auth_token(token: str) -> Optional[dict]:
    """校验 token，有效时返回对应 user 记录，无效/过期返回 None。"""
    if not token:
        return None
    db = load_db()
    now = datetime.now()
    for t in db.get("auth_tokens", []):
        if t["token"] == token:
            expires = _parse_dt(t.get("expires_at", ""))
            if expires and expires > now:
                return get_user_by_id(t["user_id"])
            break
    return None


def revoke_auth_token(token: str) -> None:
    """使 token 失效（退出登录时调用）。"""
    if not token:
        return
    db = load_db()
    db["auth_tokens"] = [t for t in db.get("auth_tokens", []) if t["token"] != token]
    save_db(db)
