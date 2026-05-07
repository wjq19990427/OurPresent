# OurPresent

> 不要以遗憾为代价去学会爱，愿我们能保留每一份感情中的美好。

OurPresent 是一个面向情侣的私密双人记录空间。记录默认仅自己可见，在满足时间锁规则后才能对伴侣共享；关系结束时，系统提供冻结、导出和销毁机制来保护双方隐私。

当前仓库提供的是一个本地运行的 Streamlit Alpha Demo，重点验证以下能力：

- 双人账号与绑定关系管理
- 图片、视频、文字记录的统一归档
- 延时共享的时间锁机制
- 评论、归档与情侣空间查看
- 冻结期、导出与数据销毁流程

## 快速开始

安装依赖：

```bash
uv sync
```

启动应用：

```bash
uv run streamlit run main.py
```

常用开发命令：

```bash
uv run ruff check .
uv run pytest
```

## 文档导航

- 产品需求文档：[docs/PRD.md](./docs/PRD.md)
- 开发者技术报告：[docs/technical-report.md](./docs/technical-report.md)
- API 与模块边界：[docs/api-contracts.md](./docs/api-contracts.md)
- 数据模型：[docs/data-model.md](./docs/data-model.md)
- 扩展指南：[docs/extension-guide.md](./docs/extension-guide.md)
- 用户使用文档：[docs/user-guide.md](./docs/user-guide.md)
- 版本记录：[CHANGELOG.md](./CHANGELOG.md)

## 项目结构

```text
OurPresent/
├── main.py
├── backend/
│   ├── api/
│   ├── application/
│   │   ├── auth/
│   │   ├── couples/
│   │   ├── maintenance/
│   │   └── sessions/
│   ├── config/
│   ├── domain/
│   │   └── models/
│   └── infrastructure/
│       ├── ai/
│       ├── database/
│       └── media/
├── frontend/
│   └── streamlit_app/
├── docs/
├── data/
├── Assets/
├── pyproject.toml
└── uv.lock
```

## 当前状态

- 阶段：Alpha 本地 Demo
- 运行方式：Streamlit 前端壳 + Python 本地业务模块
- 数据存储：`data/db.json` + `Assets/`
- 后端边界：`application / domain / infrastructure / config`
- AI 能力：第二阶段预留，当前未正式接入
