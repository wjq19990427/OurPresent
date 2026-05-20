# 微信小程序 crypto smoke test 实测记录

最后更新：2026-05-20

## 最终结论

- task-27 的微信开发者工具模拟器验收已通过：smoke 页面能正常渲染，三项加密测试全部显示通过。
- 当前实现不再使用 `libsodium.js`。开发者工具基础库 `3.16.0` 的 service runtime 中，vendored `libsodium.js` 暴露了三层兼容性问题：
  - 官方 browser build 默认随机源探测不识别 `wx.getRandomValues`，会报 `No secure random number generator found`。
  - UMD 入口以 `this` 作为全局对象，在小程序模块环境中不可靠，可能导致 `Cannot read property 'sodium' of undefined`。
  - 运行时无 `WebAssembly` 时，内置 asm backup 路径仍会失败，错误为 `Both wasm and asm failed to loadTypeError: A.memcmp is not a function`。
- 为避免继续堆叠平台 fallback，最终修复改为单一路径：
  - 随机数唯一入口为 `wx.getRandomValues`。
  - X25519 使用本地 RFC7748 BigInt ladder。
  - HKDF-SHA256、XChaCha20-Poly1305、Argon2id 使用 `@noble/hashes` / `@noble/ciphers` 的纯 JS 实现。
  - 构建时用 esbuild 把 crypto 入口打包为小程序可 `require()` 的 CommonJS 文件。
- 开发者工具控制台仍会出现 `Error: timeout`，堆栈来源为 `WAServiceMainContext.js?t=wechat&v=3.16.0`，未指向项目代码；页面测试已完成并展示通过，因此当前判断为微信开发者工具 / 基础库内部调试噪音，不阻塞 task-27 crypto 验收。

## 开发者工具实测结果

实测环境：

- 时间：2026-05-20 10:52 左右
- 工具：微信开发者工具 Stable `2.01.2510290`
- 基础库：`3.16.0`
- 运行环境：macOS 模拟器，小程序模式，项目读取 `miniprogram/dist/`

页面结果：

| 环境 | X25519 + HKDF-SHA256 | XChaCha20-Poly1305 AEAD | Argon2id (`t=3`, `m=64MB`) | 备注 |
| --- | ---: | ---: | ---: | --- |
| 微信开发者工具模拟器 | 5ms，通过 | 1ms，通过 | 3361ms，通过 | 控制台仍有 `WAServiceMainContext` timeout；页面结果正常 |
| iOS 微信真机 | 待实测 | 待实测 | 待实测 | 需要有效 AppID / 真机预览 |
| Android 微信真机 | 待实测 | 待实测 | 待实测 | 需要有效 AppID / 真机预览 |

同页 API availability：

| API | 开发者工具模拟器结果 |
| --- | --- |
| `wx.getRandomValues` | available |
| `wx.setStorage` / `wx.getStorage` | available |
| `wx.scanCode` | available |

## 本地验证

终端侧验证覆盖两类边界：

```bash
cd miniprogram
npm run build
npm run typecheck
```

- `npm run build` 通过，生成 `dist/subpackages/crypto/index.js`。
- `npm run typecheck` 通过。
- 在 Node mock 中主动设置 `global.WebAssembly = undefined` 后，三项 smoke test 仍通过，说明当前实现不依赖 WASM。
- 删除 `global.wx` 后执行 smoke test，会明确失败为 `wx.getRandomValues is unavailable`，说明随机数入口没有回落到 browser `crypto.getRandomValues` 或 Node `crypto`。

## 分包体积记录

当前构建产物：

| 项目 | 大小 |
| --- | ---: |
| `dist/subpackages/crypto/index.js` | 69,818 bytes（约 68.2 KB） |
| `dist/subpackages/crypto/` 目录 | 104 KB（`du -k`） |

task-27 原验收写的是 “crypto 分包体积 < 500KB（libsodium.js WASM）”。由于最终不再使用 `libsodium.js` / WASM，这条验收应按实际 crypto 分包产物理解：当前分包小于 500KB。

## 修复过程摘要

1. 最初失败为 `No secure random number generator found`。定位到 vendored `libsodium.js` 只探测 browser `crypto.getRandomValues` / Node `crypto`，不识别小程序 `wx.getRandomValues`。
2. 尝试将 `wx.getRandomValues` 注入给 sodium 后，开发者工具继续暴露 `Cannot read property 'sodium' of undefined`。定位到 vendor 末尾 UMD 使用 `}(this)`，在小程序 service 模块环境中全局绑定不可靠。
3. 将 UMD 入口改为 `globalThis` 后，本地进一步用 `WebAssembly = undefined` 复现到 `Both wasm and asm failed to loadTypeError: A.memcmp is not a function`。这说明该 vendor 的无 WASM 路径本身不可作为小程序唯一可靠通路。
4. 按“不要堆 fallback，只保留唯一通路”的约束，删除 `vendor/sodium.js`，改为纯 JS crypto bundle：
   - X25519：本地 RFC7748 ladder，不生成随机数，只消费 `wx.getRandomValues` 给出的 32-byte secret。
   - HKDF-SHA256：`@noble/hashes`。
   - XChaCha20-Poly1305：`@noble/ciphers`。
   - Argon2id：`@noble/hashes/argon2`。
5. 重新 build 到 `dist/` 后，开发者工具模拟器三项测试全部通过。

## 与调研结论的偏差

- `docs/research/wechat-miniprogram-crypto.md` 中提到 `libsodium.js` / WASM 可作为候选方案；task-27 实测表明，当前使用的官方 browser build 在微信开发者工具 service runtime 中不可靠。
- 调研中“WASM 可单独落盘进分包”的假设没有在本次 task-27 中成立；实际修复放弃 WASM，选择纯 JS bundle。
- Argon2id 在开发者工具模拟器耗时约 3.3s，明显慢于 X25519 / AEAD，符合调研中“Argon2 才是需要 UX 预算的操作”的风险判断。后续真机仍需分别记录 iOS / Android 耗时。

## 后续真机验收步骤

1. 使用有效 AppID 在微信开发者工具中预览或真机调试。
2. 分别用 iOS 微信与 Android 微信打开 smoke 页面。
3. 记录三项测试耗时、机型、系统版本、微信版本和基础库版本。
4. 若真机仅 Argon2id 慢或失败，优先调整 UX 预算或参数，不要回退到不可靠的多随机源 / 多运行时 fallback。
