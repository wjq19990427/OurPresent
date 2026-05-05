"""
第二阶段 AI 智能体接口预留（Phase 2 占位）。
当前均为未实现存根，配置 OURPRESENT_API_KEY 后接入 LLM。
"""

from __future__ import annotations

from backend.db_manager import load_db


def get_shared_sessions_for_rag(couple_id: str) -> list[dict]:
    """
    返回指定情侣关系下所有 visibility=="shared" 的 sessions，供 RAG 索引。
    强约束：私密记录严禁进入向量库。
    """
    db = load_db()
    return [
        s for s in db["sessions"]
        if s.get("couple_id") == couple_id
        and s.get("visibility") == "shared"
    ]


def get_report_history(couple_id: str) -> list[dict]:
    """
    返回该情侣的历史周报记录（第二阶段新增 reports 表后实现）。
    """
    raise NotImplementedError("Phase 2: 周报功能尚未实现")
