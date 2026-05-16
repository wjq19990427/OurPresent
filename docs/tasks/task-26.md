# Task 26: Phase 1 W3 · 三视图信息架构 + 新手引导

## 变更说明

类型：Bug修复 + 优化（用户可见）

Phase 1 收尾卡。W1 打磨了写-锁-解锁旅程，W2 完整了冻结期链路。W3 解决三件事：**告别页 bug 修复**（W2 后续补丁引入的 URL query param 持久化有安全 / 状态同步问题）；**信息架构**——让用户在三个 tab 之间切换时不迷失方向，尤其是"哪些记录正在等、哪些已经到了"一眼可辨；**新手引导**——从"绑定成功"到"第一次解锁"的魔法时刻，让两个人第一次用就能感受到产品灵魂。

**语气基调**（延续 W2 约定）：温柔但清醒。功能性引导不要啰嗦，第一次解锁的魔法时刻不要浮夸。

---

## 背景

`docs/ROADMAP.md` Phase 1 候选第 5~6 项落地。本卡是 Phase 1 三张串行卡（W1/W2/W3）的第三张，在 task-25 合并后执行。

**W1/W2 后的现状**（实现工可读代码确认，以下是已知的）：

- 「我的」tab：过滤掉 shared，只展示 private + pending_unlock 两类，**但两类混排**，用户无法快速找到"哪几条正在等"
- 「我们」tab：顶部有伴侣端"有记录正在路上"预告区块（W1 产物）；共享记录按 shared_at 倒序；冻结期 banner（W2 产物）
- 新手路径：未绑定时「我们」tab 显示"先去设置里绑定伴侣"；绑定成功后无任何引导，直接进入空列表；首条记录入口在 W1 已改为默认展开
- 首次解锁：只有 24h 内的"新近解锁"绿色标签（W1 产物），无特殊庆祝时刻

## 要做的改动

0. **告别页 farewell URL bug 修复**（先做，其余项不依赖它但它依赖干净的状态逻辑）：
   - **症状**：当前 `_open_farewell_page()` 在 `main.py` 同时写 `session_state["farewell_state"]` 和 `st.query_params["farewell"]`；`_init_state()` 在每次页面加载时从 URL 读回 `farewell_state`。后果：① URL 中的 `?farewell=destroy_now` 可由任何人手动输入，绕过关系解散检测直接看告别页；② 浏览器后退键可重新触发告别页；③ URL 暴露关系状态到浏览器历史记录；④ session_state 与 query_params 两份状态随时可 desync
   - **修法**：移除所有 `st.query_params["farewell"]` 读写，告别状态只存 `session_state`。用户刷新浏览器后直接回到登录页（user 已清空），这是可接受的行为——告别页是一次性情感瞬间，不需要跨刷新持久化
   - **涉及文件**：`main.py`（`_open_farewell_page` 去掉 query_params 写入；`_init_state` 去掉 URL 读取）、`frontend/streamlit_app/pages/farewell.py`（"返回首页"按钮去掉 `del st.query_params["farewell"]`）

1. **「我的」tab 分组展示**：当前 private + pending_unlock 混排。改为两个**视觉分区**——「等待开放」区在上（突出展示正在倒计时的记录）、「私密记录」区在下。每个分区有区块标题 + 记录数；分区为空时不展示区块标题。不新增独立 tab，保持三 tab 结构
2. **「等待开放」区的额外信号**：这一区的卡片徽章已在 W1 更新为「等待开放 · 还要 N 天」；在分区标题旁也展示最近一条将要开放的时间（"最快 N 天后开放"），让用户一眼感知节奏
3. **三 tab 切换成本审查**：检查 tab 名称 + emoji 是否准确反映内容（`🏠 我们` / `📝 我的` / `⚙️ 设置`）；「我的」tab 子标题或 caption 简短说明"只显示你自己写的、还没开放的记录"，避免用户困惑"为什么看不到已共享的"
4. **绑定成功后的引导时刻**：`pending_bind → active` 之后（或接收方点了接受之后），「我的」tab 顶部展示一次性的"你们绑定了 · 写下第一条记录"引导——只在"active 且双方无任何 session"时出现，展示后用户写了第一条记录自动消失。不要弹窗，融入 tab 正文
5. **未绑定状态的「我们」tab 空状态优化**：当前只显示"先去设置里绑定伴侣"。改为更有温度的空状态文案 + 直接跳到设置绑定区的按钮（减少一步操作）
6. **首次解锁的魔法时刻**：在「我们」tab，当历史上**从未有过任何 shared 记录**的 couple 出现了第一条 shared 记录（新鲜解锁）时，展示一次性的特别文案区块（"你们的第一条共享记录来了"之类的温柔克制文案），不使用 emoji 堆砌或感叹号。条件：`shared_at` 在 24h 内 且 该 couple 历史上第一条 shared 记录。条件失效后（刷新后记录不再是"第一次"或超过 24h）自然消失，不需要持久化状态
7. **tab 间空状态一致性**：审查三个 tab 在各种空状态下的文案（无记录、无伴侣、冻结期、未开放记录为零等），统一克制基调，避免出现"还没有记录哦~" 这类二次元口吻
8. **L2 文档同步**：`docs/api/frontend_streamlit.md` 同步「我的」分组逻辑、绑定引导、魔法时刻、空状态变化
9. **`CHANGELOG.md` `[Unreleased]`**：1-2 句总结

## 涉及文件

- `main.py`（第 0 项 farewell 修复）
- `frontend/streamlit_app/pages/farewell.py`（第 0 项 farewell 修复）
- `frontend/streamlit_app/pages/tab_mine.py`（分组展示、绑定引导）
- `frontend/streamlit_app/pages/tab_us.py`（未绑定空状态、魔法时刻）
- `frontend/streamlit_app/components.py`（如需新增 helpers）
- `docs/api/frontend_streamlit.md`
- `CHANGELOG.md`

## 验收（用户可见行为）

- 直接在浏览器地址栏输入 `?farewell=destroy_now` 不能触发告别页（跳到登录或主页）；刷新浏览器后告别页消失、回到登录页；告别页"返回首页"按钮正常工作
- 「我的」tab 有两个视觉分区，「等待开放」在上；分区标题旁显示最快开放时间；每个分区为空时不展示标题
- 新用户绑定成功后，「我的」tab 顶部有一次性引导"写下第一条记录"，写了后自动消失
- 未绑定状态下「我们」tab 的空状态有直接跳转到设置绑定区的按钮
- 该 couple 第一条记录解锁后 24h 内，「我们」tab 顶部有克制的魔法时刻文案（只出现一次）
- 三个 tab 的空状态文案无二次元口吻，基调温柔克制统一
- `docs/api/frontend_streamlit.md` 同步以上行为

## 不要做

- **告别页不要引入服务端 session 或 cookie 来实现跨刷新持久化**——session_state 足够，刷新回登录页是正确行为
- **不要新增第四个 tab**（「待解锁」不做独立 tab）——在「我的」tab 内分组即可
- **不要引入持久化的"引导完成"状态到数据库**——用"条件推断"替代（active + 无 session = 首次引导；有 session = 消失），不加新字段
- **不要改 tab 数量或 tab 名称**——结构已在 W1 确定，W3 只改内容层
- **不要触碰 `docs/STATUS.md`、`docs/DIRECTION.md`、`docs/ROADMAP.md`、`docs/E2EE.md`、`docs/PRD.md`、`CLAUDE.md`**
- 不要做账号注册 / 配对 / 冻结链路（W2 范围）
- 不要引入自定义 CSS / 第三方依赖
- 不要改 settings tab 内容（设置布局不在 W3 范围）

## 提交规约

- `pytest backend/tests/` 整库通过（本卡无后端改动，回归即可）
- `ruff check .` 通过
- 自行启动 Streamlit 验收，**端口必须指定非默认值**，例如 `streamlit run main.py --server.port 8765`
- **用两个账号**验收新手路径：绑定 → 引导出现 → 写第一条记录 → 引导消失 → 申请共享 → 解锁 → 魔法时刻出现
- commit message 形如 `ux(nav): 三视图信息架构 + 新手引导 · 关联 #26`，可拆多个 commit
