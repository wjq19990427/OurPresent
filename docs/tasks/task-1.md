# Task 1: session 子域 dataclass 化

**类型**：refactor
**Branch**：`codex/task-1`
**前置任务**：无

## 目标

消除 `backend/application/sessions/*` 与 `frontend/streamlit_app/{components.py,pages/*.py}` 公开签名中的 `session: dict` 形参，统一使用 `SessionRecord` dataclass。让 v2.1.0 已经在 repository 边界落地的 dataclass 模型贯穿到 UI 层。

## 改动范围

**许动**：

- `backend/application/sessions/*.py`（所有以 `session: dict` 为参或返回 dict 的函数）
- `backend/infrastructure/database/sessions_repo.py`（公开签名调整为 `SessionRecord`）
- `frontend/streamlit_app/components.py`
- `frontend/streamlit_app/pages/*.py` 中所有传 session 给 component 的地方

**不许动**：

- `SessionRecord.files / comments / edit_history` 内部仍保持 `list[dict]`（`docs/api/domain_models.md` 已明确保留这一折中，本任务不扩到子结构）
- `auth` / `couples` / `maintenance` 子域
- 持久化字段集和 DB schema
- 任何与 session 无关的模块

## 接口约定

- **dict ↔ dataclass 转换边界放在 `sessions_repo` 内部**：repo 公开签名以 `SessionRecord` 为准（入参、出参均不再是 dict）；`SessionRecord.from_dict()` / `to_dict()` 仅在 repo 内部使用
- application 层、frontend 层一律收发 `SessionRecord`
- `is_text_session` / `validate_session` / `can_view_session` / `render_card` / `render_detail` / `render_comments` 等当前签名为 `(session: dict, ...)` 的函数全部改为 `(session: SessionRecord, ...)`
- `_session_thumb` / `_visibility_badge` / `_days_until_unlock` 等内部辅助同样切换
- 子结构（`files` 列表里的 file dict、`comments` 列表里的 comment dict、`edit_history` 列表里的 entry dict）保持现有 dict 结构，调用方继续用键访问

## 已知陷阱

- 现有代码中可能存在 `session["status"] = "final"` 这类原地 mutate 的 dict 风格写法，dataclass 化后必须改为属性赋值或者通过 repo 提供的更新方法
- Streamlit 的 `st.session_state` 序列化对 dataclass 友好，但若有地方直接把 session 整体塞进 widget key / form state，需要确认行为一致

## 验收行为（用户视角）

启动 `uv run streamlit run main.py`，以下流程全部跑通且无 `AttributeError` / `KeyError`：

- 注册 → 登录 → 上传文件 + 文字记录 → 暂存到灵感墙 → 编辑 → 完成并归档
- 在已归档区编辑字段，编辑历史正确追加
- 申请共享 / 撤回共享，可见性标签变化正确
- 绑定情侣后，伴侣可在「💌 情侣空间」看到 `shared` 状态的记录（只读）
- 添加和删除评论，已归档记录的 `Final/{id}.md` 同步更新
- 冻结期导出，文件清单只含自己的内容
- 销毁后双方关系数据彻底清理

自动化检查：

- `uv run python -c "import backend, frontend; print('OK')"`
- `uv run pytest` 全绿
- `uv run ruff check .` 无错

## 必读契约

- `docs/api/domain_models.md`（SessionRecord 字段全集 + from_dict/to_dict 语义）
- `docs/api/app_sessions.md`（七个子模块当前的 dict 签名）
- `docs/api/frontend_streamlit.md`（components 和 pages 当前的 dict 签名）
- `docs/api/infra_db.md`（sessions_repo 当前对外形态）

## 文档同步

实现完成后必须同步更新这四份 L2 契约的相关签名段落。L2 契约更新视为本任务的一部分，未更新不算完成。
