# OurPresent 文档索引

本文档是 `docs/` 的总入口，帮助快速找到当前有效文档，避免继续引用已经迁移的旧路径。

当前目录规则：

- `docs/` 第一层只保留**最重要的主文档**，统一使用**大写文件名**
- 其余说明性、专题性、操作性文档全部下沉到子目录

## 1. 先看哪些

- 产品目标与功能边界：[`PRD.md`](./PRD.md)
- 架构入口与 L2 契约导航：[`ARCHITECTURE.md`](./ARCHITECTURE.md)
- 项目当前状态：[`STATUS.md`](./STATUS.md)
- 商业化方向与隐私底线：[`DIRECTION.md`](./DIRECTION.md)
- 上线路线图：[`ROADMAP.md`](./ROADMAP.md)
- E2EE 协议设计：[`E2EE.md`](./E2EE.md)

## 2. 按主题查找

### 产品 / 架构

- [`PRD.md`](./PRD.md)
- [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- [`STATUS.md`](./STATUS.md)
- [`DIRECTION.md`](./DIRECTION.md)
- [`ROADMAP.md`](./ROADMAP.md)
- [`AUDIT.md`](./AUDIT.md)

### 设计稿 / 专题文档

- 情感周报设计：[`notes/weekly_report.md`](./notes/weekly_report.md)
- E2EE 协议：[`E2EE.md`](./E2EE.md)
- 微信小程序 E2EE 可行性调研：[`research/wechat-miniprogram-crypto.md`](./research/wechat-miniprogram-crypto.md)

### 使用说明

- 最终用户使用文档：[`guide/user-guide.md`](./guide/user-guide.md)
- 合成数据工具说明：[`guide/synth-user-guide.md`](./guide/synth-user-guide.md)

### 设计备注 / 扩展说明

- AI 产品定调：[`notes/AI.md`](./notes/AI.md)
- 扩展开发指南：[`notes/extension-guide.md`](./notes/extension-guide.md)

### 模块契约（L2）

- 模块接口与行为约定统一放在 [`api/`](./api/)

### 任务卡

- 实现任务统一放在 [`tasks/`](./tasks/)

## 3. 目录约定

- `docs/` 根目录只放大写命名的高层主文档
- `docs/guide/` 放面向使用者或操作流程的说明
- `docs/notes/` 放补充性的设计备注、扩展说明和背景材料
- `docs/research/` 放外部事实调研
- `docs/api/` 放 L2 契约
- `docs/tasks/` 放任务卡

## 4. 迁移说明

以下旧路径已经迁移，不应再继续新增引用：

- `docs/user-guide.md` → [`docs/guide/user-guide.md`](./guide/user-guide.md)
- `docs/synth-user-guide.md` → [`docs/guide/synth-user-guide.md`](./guide/synth-user-guide.md)
- `docs/AI.md` → [`docs/notes/AI.md`](./notes/AI.md)
- `docs/extension-guide.md` → [`docs/notes/extension-guide.md`](./notes/extension-guide.md)
- `docs/product-direction.md` → [`docs/DIRECTION.md`](./DIRECTION.md)
- `docs/phase2_audit.md` → [`docs/AUDIT.md`](./AUDIT.md)
- `docs/weekly_report.md` → [`docs/notes/weekly_report.md`](./notes/weekly_report.md)
