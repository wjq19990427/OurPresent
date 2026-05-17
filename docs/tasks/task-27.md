# task-27 · M1：小程序客户端加密 smoke test

## 变更说明

**类型**：新功能

在微信小程序环境中验证 libsodium.js 加密库的可行性——用户能看到一个 smoke test 页面，显示 X25519 密钥协商、AEAD 加解密、Argon2id 三项测试的耗时与通过/失败状态。这是 Phase 2 E2EE 端到端链路的客户端基础。

---

## 前置条件

- **AppID**：需要微信小程序接口测试号才能在真机上运行（开发者工具模拟器不需要）
- 基础骨架已在 `miniprogram/` 目录就位（M0 已完成）
- 参考：`docs/E2EE.md`（加密 API 约束）·`docs/research/wechat-miniprogram-crypto.md`（调研报告）

## 工作范围

涉及目录：`miniprogram/`

**加密分包**：在 `miniprogram/subpackages/crypto/` 创建分包，引入 libsodium.js。
- 分包需独立声明在 `app.json` 的 `subpackages` 数组
- libsodium.js 的 WASM 文件放入分包，主包不引用

**Smoke test 页面**：新增 `pages/smoke/smoke` 页面，展示三项测试结果：
1. X25519 + HKDF-SHA256：生成临时密钥对 → ECDH → HKDF 派生 32-byte 密钥；展示耗时（ms）
2. XChaCha20-Poly1305 AEAD：加密随机 1KB 明文 → 解密 → 对比原文；展示耗时（ms）
3. Argon2id（t=3, m=64MB）：对随机 16-byte 盐 + 固定密码派生密钥；展示耗时（ms）

每项测试显示：`✓ 通过 · Xms` 或 `✗ 失败 · 错误信息`。

**wx API 验证**：在同一页面补充 `wx.getRandomValues` / `wx.setStorage & getStorage` / `wx.scanCode` 的可用性检测（仅 available/unavailable 两态，不测功能细节）。

**`app.json` 更新**：把 `pages/smoke/smoke` 加入 pages 列表；声明 crypto 分包。

**约束**：
- 不实现真正的配对逻辑，仅 smoke test
- 不引入任何网络请求
- libsodium.js 必须来自可在小程序环境加载的构建产物（CDN 在小程序不可用，需本地打包）

## 产出文档

完成后更新 `docs/research/wechat-miniprogram-crypto-verified.md`（若文件不存在则新建），记录：
- 三项测试在开发者工具模拟器 + iOS 微信 + Android 微信（各一台）的实测耗时
- libsodium.js 引入后分包体积增量（KB）
- 任何与 `docs/research/wechat-miniprogram-crypto.md` 调研结论不符的发现

## 验收

- [ ] 微信开发者工具模拟器中打开 smoke 页面，三项加密测试全部显示 `✓ 通过`
- [ ] iOS 真机微信中打开 smoke 页面，三项加密测试全部 `✓ 通过`（**需要 AppID**）
- [ ] Android 真机微信中打开 smoke 页面，三项加密测试全部 `✓ 通过`（**需要 AppID**）
- [ ] crypto 分包体积 < 500KB（libsodium.js WASM）
- [ ] `docs/research/wechat-miniprogram-crypto-verified.md` 落盘，含实测耗时数据

## 并行约束

- **Wave 1**（与 task-28 并行）：核心文件不重叠（miniprogram/ vs server/）
- 依赖 task-28 完成才能进入 M3
