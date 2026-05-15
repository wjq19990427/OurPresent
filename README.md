# OurPresent

> 不要以遗憾为代价去学会爱，愿我们能保留每一份感情中的美好。

OurPresent 是一个面向情侣的私密双人记录空间，承载两人的日常影像与文字，也为难以当面开口的心意留出沉淀的余地。

生活中不论是男生还是女生，我们都会有一种矛盾的心理：**不敢在当下直截了当的表达出自己的想法**，因为担心表达出来的后果自己无法承受，可能是恋爱初期过于草率的表达容易分手，或者是害怕让对方讨厌自己的某些方面所以选择隐藏，又或者是吵架上头时因为害怕冲突选择回避等等。但是另一方面，我们都希望恋爱的双方能够相互坦诚，相互信任，希望对方能够接纳**真实的完整的自己**。

我们通过OurPresent，提出一种沟通的方式，让使用者可以选择“延时发布”，即此时此刻上传一条记录，但是可以设定在一段时间过后才向对方开放访问，这样就可以**把当下的情绪和心理负担平摊到未来的一段时间**。对于表达者来说，不是“我还不想面对”，而是“我已经面对了，只是等一阵子再告诉你”；对于另一方来说，不是“我不懂你的心思“，而是“我愿意用更多的时间去理解你“。

> 在保护双方绝对个人隐私的前提下，通过"延时共享"机制让感情沉淀，并在合适的时机以温柔的方式让彼此看见对方的心意。

## “Present” 的三层含义

1. **我们的当下（Our Present）**：记录此刻的真实状态，无论喜悦还是难以直言的委屈。
2. **共同的馈赠（The Gift of Today）**：两人相遇本是礼物，提醒珍惜当下的陪伴。
3. **温柔地表达（Present to You）**：每一条记录经时间沉淀后，化作一份延迟解锁的情感礼物。

## 当前能力（Alpha Demo）

当前仓库提供的是一个本地运行的 Streamlit Alpha Demo，重点验证以下能力：

- **双人账号与绑定**：邀请制配对，记录默认仅本人可见，绑定后才能按规则向对方开放
- **图文影像统一归档**：把散落在各自手机的照片、视频、文字按时间和情感线索沉淀在同一空间
- **延时共享时间锁**：本项目的核心机制，详见上文；开放时间可自定义，亦可中途追加、改时、立即解锁、撤回
- **评论与情侣空间**：对方可见后支持互动留言，让"看见"变成"回应"
- **冻结期、导出与销毁**：关系结束时提供有尊严的退出流程，避免数据成为后续负担
- **情感周报（NVC 视角）**：基于双方共享内容生成结构化周报，含「关系足迹 / 情绪气象 / 同频共鸣 / 未尽悬念」四模块；只读 shared 不读私密，温和陈述不评判，双方都开启服务后才生成

## 快速开始

情感周报生成需要在项目根目录 `.env` 中配置 `DEEPSEEK_API_KEY`。

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

- 文档总索引：[docs/README.md](./docs/README.md)
- 产品需求文档：[docs/PRD.md](./docs/PRD.md)
- 架构索引（L1）：[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- 战略方向与隐私底线：[docs/DIRECTION.md](./docs/DIRECTION.md)
- 上线路线图：[docs/ROADMAP.md](./docs/ROADMAP.md)
- 模块公开接口（L2 契约）：[docs/api/](./docs/api/)
- 扩展指南：[docs/notes/extension-guide.md](./docs/notes/extension-guide.md)
- 用户使用文档：[docs/guide/user-guide.md](./docs/guide/user-guide.md)
- 项目状态快照：[docs/STATUS.md](./docs/STATUS.md)
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

- 阶段：Alpha 本地 Demo · Phase 2 情感周报 v1 已上线
- 运行方式：Streamlit 前端壳 + Python 本地业务模块
- 数据存储：`data/database.db` + `Assets/`
- 后端边界：`application / domain / infrastructure / config`
- AI 能力：情感周报基于 DeepSeek V4 Flash，输入字段白名单 + 反原文引用兜底；NVC 润色器 / 安全着陆舱 / 专属词典等待开设计稿
