# OurPresent 技术报告

本文档面向开发者，描述当前 Alpha 版本的系统结构、依赖方向与代码阅读入口。

## 1. 技术概览

- 前端：Streamlit
- 业务层：本地 Python 模块
- 数据层：`data/database.db`（SQLite）
- 文件存储：`Assets/Pending/` 与 `Assets/Final/`
- 依赖管理：`uv`

## 2. 当前目录结构

```text
backend/
├── api/
├── application/
│   ├── auth/
│   ├── couples/
│   ├── maintenance/
│   └── sessions/
├── config/
├── domain/
│   └── models/
└── infrastructure/
    ├── ai/
    ├── database/
    └── media/

frontend/
└── streamlit_app/
```

## 3. 分层关系

```text
backend/config/settings
    ↓
backend/domain/models
    ↓
backend/infrastructure/database/*_repo
    ↓
backend/application/*
    ↓
frontend/streamlit_app/*
    ↓
main.py
```

## 4. 模块职责

### `backend/application/`

- `auth/`：注册、登录、token 恢复登录
- `couples/`：绑定、解绑、冻结期规则
- `sessions/`：创建、编辑、评论、共享、导出、销毁
- `maintenance/`：`tick()` 和状态推进

### `backend/domain/models/`

当前已引入以下 `dataclass`：

- `User`
- `Couple`
- `SessionRecord`
- `AuthToken`

它们提供 `from_dict()` / `to_dict()`，用于在持久化字典记录与业务对象之间转换。

### `backend/infrastructure/database/`

- `db.py`：底层 SQLite 读写、旧 JSON 自动迁移、目录初始化、时间工具
- `users_repo.py`：用户查询、创建、密码校验
- `couples_repo.py`：情侣关系查询与状态更新
- `sessions_repo.py`：session 持久化入口
- `tokens_repo.py`：登录 token 持久化与校验

### `backend/infrastructure/media/`

- `thumbnails.py`：视频缩略图与图片字节转换

### `frontend/streamlit_app/`

- `components.py`：复用组件、辅助状态函数、详情渲染
- `pages/`：五个主 Tab 的页面逻辑

## 5. 当前设计取舍

- 认证、情侣关系链路已经改为 dataclass + repository
- session UI 仍以字典结构渲染，降低重构风险
- `load_db_with_tick()` 仍对整份内存字典做状态推进，因为它天然跨 `sessions / couples / auth_tokens`
- `destroy_couple_data()` 仍是跨表操作，用例层直接协调多张表

## 6. 推荐阅读顺序

1. 先看 [README.md](../README.md) 了解项目目标
2. 再看 [api-contracts.md](./api-contracts.md) 理解模块边界
3. 需要改字段或存储结构时看 [data-model.md](./data-model.md)
4. 需要改时间锁或解绑逻辑时看 [state-machines.md](./state-machines.md)
