# Task 12b: 登录页迁移至移动端风格

**类型**：feature（UI 改版）  
**Branch**：`codex/task-12b`  
**前置任务**：task-12a 建议先合并（避免改同一文件时产生冲突）

## 背景

登录页当前为两列桌面布局（左：表单，右：功能介绍），与认证后所有页面的单列移动端风格不一致，体感割裂。

## 目标行为（用户可见）

- 进入登录页，所有内容单列垂直排列，无左右分栏
- 功能介绍不再作为右列并排呈现，改以可折叠区域或页面底部辅助说明形式出现
- 整体视觉语言（间距、按钮宽度、分组方式）与「我的」「我们」「设置」三个 tab 保持一致

## 改动范围

**许动**：
- `main.py`：`render_auth_page()` 函数内部
- `frontend/streamlit_app/components.py`：仅复用已有组件，不改现有组件签名

**不许动**：
- auth 逻辑（登录 / 注册 / token 校验）
- `backend/` 任何文件
- `docs/STATUS.md` / `CHANGELOG.md`

## 验收行为

- 窄窗口（移动端宽度）下不出现横向滚动条
- 视觉风格与 `tab_mine.py` 一致
- 登录、注册功能行为与改版前完全相同

自动化检查：
- `uv run python -c "import main"` 无报错
- `uv run pytest` 全绿

## 必读契约

- `docs/api/frontend_streamlit.md`（当前 UI 结构）
