# OurPresent 技术报告

本文档面向开发者，描述当前 Alpha 版本的系统设计、模块边界与技术文档导航。

更细的技术内容已拆分为独立文档：

- API 约定与模块公开接口：[api-contracts.md](./api-contracts.md)
- 数据模型：[data-model.md](./data-model.md)
- 状态机与分手协议：[state-machines.md](./state-machines.md)
- 扩展开发与第二阶段接口预留：[extension-guide.md](./extension-guide.md)

## 1. 技术概览

### 1.1 运行形态

- 前端：Streamlit
- 业务层：本地 Python 模块
- 数据层：`data/db.json`
- 文件存储：`Assets/Pending/` 与 `Assets/Final/`
- 依赖管理：`uv`

### 1.2 目录结构

```text
OurPresent/
├── main.py
├── core/
├── utils/
├── backend/
├── frontend/
├── docs/
├── data/
├── Assets/
├── .streamlit/
├── pyproject.toml
└── uv.lock
```

文档中的路径统一使用仓库相对路径，并以 `/` 表示层级分隔；实际代码中使用 `pathlib.Path` 处理路径，以保证 macOS、Linux 和 Windows 下都能正常开发。

## 2. 架构设计

### 2.1 分层关系

```text
core/config
    ↓
utils/validators    utils/file_processor
    ↓                     ↓
backend/db_manager ←──────┘
    ↓
backend/session_manager
    ↓
backend/auth_manager
    ↓
core/state_machine
    ↓
frontend/components
    ↓
frontend/pages/*
    ↓
main.py
```

### 2.2 设计原则

| 层 | 职责 | 约束 |
|----|------|------|
| `core/` | 全局常量、跨层状态机 | 不依赖 Streamlit，不依赖 backend |
| `utils/` | 纯函数工具 | 无任何内部模块依赖 |
| `backend/` | 业务逻辑与数据访问 | 不依赖 Streamlit，可独立作为后端 API 层 |
| `frontend/` | UI 渲染 | 只调用 backend 和 utils，不直接操作 db.json |
| `main.py` | 组合入口 | 持有 `st.set_page_config`（必须首次调用） |

## 3. 模块清单

| 模块 | 说明 |
|------|------|
| `core/config.py` | 路径常量、FIELD_SCHEMA、TEXT_EXTS |
| `core/state_machine.py` | `tick()`、`load_db_with_tick()` |
| `core/agent_skills.py` | Phase 2 LLM 接口占位 |
| `utils/validators.py` | `validate_session()`、`_is_text_session()` |
| `utils/file_processor.py` | `write_files()`、`video_thumbnail()` |
| `backend/db_manager.py` | JSON 读写、User/Couple CRUD、Token 管理 |
| `backend/session_manager.py` | Session 生命周期、评论、可见性、数据销毁 |
| `backend/auth_manager.py` | 注册/登录/绑定业务校验 |
| `frontend/components.py` | 可复用 UI 组件 |
| `frontend/pages/` | 五个主 Tab 页面 |
| `main.py` | 应用入口 |

## 4. 阅读建议

- 想快速理解代码边界：先看本文，再看 [api-contracts.md](./api-contracts.md)
- 想改数据库或字段结构：看 [data-model.md](./data-model.md)
- 想改时间锁或解绑逻辑：看 [state-machines.md](./state-machines.md)
- 想接 AI 或做 Beta 重构：看 [extension-guide.md](./extension-guide.md)
