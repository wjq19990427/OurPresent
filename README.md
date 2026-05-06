# OurPresent

> 不要以遗憾为代价去学会爱，愿我们能保留每一份感情中的美好。

OurPresent 是一个面向情侣的私密双人记录空间。内容默认仅自己可见，在满足规则后才能对伴侣共享；关系结束时，系统也提供冻结、导出和销毁机制来保护双方隐私。

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

项目已在 [pyproject.toml](./pyproject.toml) 中预置 `uv` 国内镜像配置，默认使用清华源解析依赖。

启动应用：

```bash
uv run streamlit run main.py
```

浏览器访问 `http://localhost:8511`，内网其他设备可访问 `http://<本机IP>:8511`。

常用开发命令：

```bash
uv run ruff check .
uv run pytest
```

## 文档导航

- 产品需求文档：[docs/PRD.md](./docs/PRD.md)
- 开发者技术报告：[docs/technical-report.md](./docs/technical-report.md)
- 用户使用文档：[docs/user-guide.md](./docs/user-guide.md)
- 文档索引：[docs/README.md](./docs/README.md)
- 版本记录：[CHANGELOG.md](./CHANGELOG.md)

## 项目结构

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
├── uv.lock
├── PRD.md
└── CHANGELOG.md
```

## 当前状态

- 阶段：Alpha 本地 Demo
- 运行方式：本地或局域网内运行
- 数据存储：`data/db.json` + `Assets/`
- AI 能力：第二阶段预留，当前未正式接入

## 说明

`README` 只保留项目总览、快速开始和文档入口。更具体的技术实现细节请看技术报告，更具体的操作步骤请看用户使用文档。
