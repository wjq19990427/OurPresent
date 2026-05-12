# Task 12a: 修复 `use_container_width` 废弃警告

**类型**：bugfix  
**Branch**：`codex/task-12a`  
**前置任务**：无

## 背景

Streamlit 已将 `use_container_width` 参数废弃，运行时出现警告：
`Please replace use_container_width with width`

## 目标

全局替换，消除所有废弃警告，不改业务逻辑。

替换规则：
- `use_container_width=True` → `width='stretch'`
- `use_container_width=False` → `width='content'`
- 未传该参数的调用不动

## 改动范围

- `frontend/streamlit_app/`（含 `components.py`、`pages/` 下所有文件）
- `main.py`

## 验收行为

`uv run streamlit run main.py` 启动后控制台无 `use_container_width` 相关警告。

自动化检查：
- `uv run ruff check .` 无错
