# 微信小程序 crypto smoke test 实测记录

最后更新：2026-05-17

## 当前结论

- 已在代码层补齐 `pages/smoke/smoke` 与 `crypto` 分包，页面会执行三项 smoke test：
  - X25519 + HKDF-SHA256
  - XChaCha20-Poly1305 AEAD（1KB 明文）
  - Argon2id（`t=3`, `m=64MB`）
- 当前这轮实现是在代码工作区内完成的，已经完成代码落地与本地 Node 侧连通性验证，但**没有直接完成微信开发者工具 / 真机微信实测**。
- 原因不是缺少代码，而是当前执行环境默认只能改代码、跑终端命令；微信开发者工具页面打开、扫码登录、预览到手机、iPhone / Android 真机微信运行，都依赖宿主机 GUI、登录态、AppID 和外部设备，不能当作纯终端自测自动完成。
- 本次实现使用官方 `libsodium.js` browser build 的本地 vendored 产物；该构建将 WASM 内嵌进 `sodium.js`，并非独立 `.wasm` 文件。这与 `docs/research/wechat-miniprogram-crypto.md` 中“WASM 可单独落盘”的预期不完全一致，后续如需严格分离 `.wasm`，需要继续验证 upstream 其他构建路径。

## 架构师需知

- 当前代码层已具备进入微信开发者工具验证的条件，但验收仍缺最后一跳人工 / GUI / 真机验证。
- 当前文档里所有“待实测”并不表示实现未落地，而是表示尚未在以下外部环境完成确认：
  - 微信开发者工具模拟器
  - iOS 微信真机
  - Android 微信真机
  - 微信开发者工具代码依赖分析
- 若后续由架构师或用户继续验收，请优先关注两类风险：
  - `Argon2id (t=3, m=64MB)` 在低端 Android 上可能明显变慢，甚至出现内存/性能问题
  - 当前 vendored `libsodium` 采用单文件内嵌 WASM 的 browser build，源码文件尺寸较大，最终是否满足分包预算必须以微信开发者工具实际构建结果为准

## 待补录耗时

| 环境 | X25519 + HKDF-SHA256 | XChaCha20-Poly1305 AEAD | Argon2id (`t=3`, `m=64MB`) | 备注 |
| --- | --- | --- | --- | --- |
| 微信开发者工具模拟器 | 待实测 | 待实测 | 待实测 | 打开 `pages/smoke/smoke` 后记录页面显示结果 |
| iOS 微信真机 | 待实测 | 待实测 | 待实测 | 需要有效 AppID |
| Android 微信真机 | 待实测 | 待实测 | 待实测 | 需要有效 AppID |

## 分包体积记录

- 当前 vendored `sodium.js` 原始文件体积：`1,320,762 bytes`（约 `1290 KB`）
- 当前 vendored `sodium.js` gzip 压缩体积：`408,635 bytes`（约 `399 KB`）
- 微信开发者工具“代码依赖分析”中的 `crypto` 分包增量：待实测

## 开发者工具与真机实测步骤

1. 在微信开发者工具中导入项目目录 `miniprogram/`
2. 将 `project.config.json` 中的 `appid` 替换为可用的接口测试号或正式 AppID，不能保留 `touristappid`
3. 编译项目后进入首页，点击“打开 crypto smoke test”
4. 记录页面上三项测试的显示结果与耗时
5. 在微信开发者工具中执行“预览”或“真机调试”
6. 使用 iPhone 微信扫码打开同一 smoke 页面，记录三项结果
7. 使用 Android 微信扫码打开同一 smoke 页面，记录三项结果
8. 打开微信开发者工具的“代码依赖分析”，记录 `crypto` 分包体积增量
9. 将三组耗时和分包体积回填到本文档

## 实测注意事项

- `wx.scanCode` 在 smoke 页面里只做 API availability 检测，不代表开发者工具模拟器能完整模拟扫码行为。
- 当前页面的核心目的是验证加密库与平台环境的兼容性，而不是验证真实配对流程。
- 如果真机上只有 Argon2id 失败，而 X25519 / AEAD 通过，应优先记录机型、系统版本、微信版本和失败文案，再评估是否需要回退到更轻的 KDF 实现或更低参数。

## 与调研结论的偏差

- 调研文档假设可以把 libsodium 的 WASM 作为单独文件落入分包；当前落地使用的官方 browser build 实际是单文件内嵌 WASM。
- 因此，`< 500KB（libsodium.js WASM）` 这条验收仍需以微信开发者工具的实际打包结果为准，不能仅凭源码目录大小下结论。
