# 微信小程序作为 E2EE 客户端的事实边界调研

调研时间：2026-05-15  
范围：只回答微信小程序作为 OurPresent Tier 1 E2EE 客户端的能力边界，不设计配对协议、备份协议或产品取舍。

## 1. 加密 API 可用范围

**结论**

小程序端可以使用 `wx.getRandomValues` 取得密码学随机数，但微信小程序公开 API 没有完整 WebCrypto `SubtleCrypto` 等价物。AES-GCM、ECDH、HKDF、Argon2 不能依赖平台内建统一实现，实际需要自带 JS/WASM 加密库或自带薄封装。可行组合是：`wx.getRandomValues` 供熵源；AES-GCM / ChaCha20-Poly1305、X25519 / P-256、HKDF、Argon2id 由 libsodium.js、Noble、hash-wasm / argon2-browser 等库承担。未验证点是这些库在微信 JSCore / X5 / Skyline 运行时和真机分包加载下的完整兼容性。

**证据来源**

- 微信开放文档 `wx.getRandomValues`：官方 API 路径为 `https://developers.weixin.qq.com/miniprogram/dev/api/base/crypto/wx.getRandomValues.html`，Taro 对应 API 标注支持微信小程序。
- `polyfill-crypto-methods` README 明确说明该库最初用于微信小程序，因为小程序不支持 Web Crypto API，导致 `crypto-js`、`jsencrypt`、`@noble/curves` 等库不能直接使用完整浏览器 crypto。
- libsodium.js README：提供 WebAssembly + pure JS 版本，支持浏览器与 Node，覆盖 XChaCha20-Poly1305、X25519、Argon2 等常用原语。
- @noble/curves README / npm：覆盖 P-256、X25519、Ed25519 等曲线；@noble/hashes 可提供 HKDF/SHA-256。
- WebCrypto 本身支持 AES-GCM、ECDH、HKDF 等，但微信小程序环境不能按普通浏览器假定 `crypto.subtle` 存在。

**2026-05 状态有效性**

公开文档与库 README 支撑“随机数 API 可用、完整加密栈需自带库”的结论。AES-GCM / ECDH / HKDF / Argon2 在目标微信真机上的细节仍未验证，需要最小小程序项目在 iOS 微信、Android 微信、开发者工具分别跑导入、加解密和 KDF smoke test 才能定论。

**分级标签：需妥协**

## 2. `wx.setStorage` 语义

**结论**

`wx.setStorage` 是每个小程序自己的本地缓存，数据生命周期跟小程序本身一致：用户主动删除或超过一定时间被自动清理时会丢失。公开文档/镜像给出的容量边界是单个 key 最大 1MB、总容量 10MB。它不是公开承诺的 secure storage：没有证据显示系统层对每个小程序密钥做 Keychain/Keystore 级保护；root / 越狱或设备级取证场景下不能承诺本地明文密钥不可读。不同微信版本、iOS vs Android 的落盘格式与系统备份行为未被官方安全边界文档完整说明。

**证据来源**

- 微信开放文档 `wx.setStorage` 官方路径：`https://developers.weixin.qq.com/miniprogram/dev/api/storage/wx.setStorage.html`。
- wxadev 文档镜像记录：数据存储生命周期跟小程序本身一致，除用户主动删除或超过一定时间被自动清理外可用；单 key 1MB，总上限 10MB。
- 多个小程序缓存教程引用同一官方语义：每个小程序有自己的本地缓存，可通过 `wx.setStorage` / `wx.getStorage` / `wx.clearStorage` 读写与清理；存储空间不足时会清空最近最久未使用小程序的本地缓存。
- 微信开放文档未在 `wx.setStorage` API 中声明 Keychain / Keystore、硬件密钥、系统加密、root/越狱保护等安全属性。

**2026-05 状态有效性**

容量、生命周期和自动清理语义有稳定公开资料。系统层加密、跨版本落盘差异、root/越狱可读性没有官方可引用保证，必须按“不可作为高安全密钥保险箱”处理；需要真机取证或微信官方安全说明才能进一步定论。

**分级标签：需妥协**

## 3. 更安全的本地钥匙位置

**结论**

微信小程序公开能力里没有面向普通业务密钥的 iOS Keychain / Android Keystore 等价持久化接口。云开发 `wx.cloud` 可以存放“用户口令派生密钥加密后的密钥密文”，但它是云端容器，不是本地 secure enclave；服务端/云平台能看到密文、元数据和访问行为，看不到口令，前提是口令只在客户端输入且 KDF / 解密只在客户端完成。因此本地长期保存 `K_couple` 的现实位置仍主要是 `wx.setStorage`，或每次通过用户口令 / 伴侣设备恢复。

**证据来源**

- 微信开放文档公开 API 分类有 storage、crypto random、cloud、device 等能力，但没有暴露 Keychain / Keystore / Secure Enclave 通用密钥保存接口。
- 云开发文档公开能力包括云函数、云数据库、云存储；开发者可在云端保存文件/文档并配置权限，但这不改变“密文在云端、口令不上传”的 E2EE 语义。
- 公开云开发教程和文档说明云数据库常用 `_openid` / 权限规则控制访问，云存储提供上传下载能力；这些是访问控制，不是客户端硬件安全存储。

**2026-05 状态有效性**

截至 2026-05 未找到官方 secure key storage API。结论可用于架构边界，但仍建议在小程序开发者工具 API 面板和真机能力列表中再确认是否有新增的安全存储能力。

**分级标签：需妥协**

## 4. 钥匙丢失触发条件

**结论**

凡是会清空微信小程序本地缓存或让原设备不可访问的场景，都会导致只存在 `wx.setStorage` 的本地密钥丢失。可列触发条件如下：

| 场景 | 是否会影响本地钥匙 | 常见度 | 证据/说明 |
| --- | --- | --- | --- |
| 用户在微信或系统里主动清理缓存/小程序数据 | 会 | 常见 | storage API 支持 `clearStorage`；微信存储空间清理是常见用户操作 |
| 微信因存储空间不足清理最久未使用小程序缓存 | 会 | 中等 | 官方语义/镜像说明“超过一定时间被自动清理”；教程补充存储不足时清理最久未使用小程序缓存 |
| 长期未使用后小程序缓存被自动清理 | 会 | 中等，频率未知 | 官方语义确认可能发生，但未公开阈值 |
| 卸载/重装微信 | 会 | 中等 | 本地数据随宿主 App 数据被移除是移动端基本行为；小程序文档未承诺跨重装保留 |
| 换手机/跨设备登录微信 | 新设备不可访问旧设备本地钥匙 | 常见 | `wx.setStorage` 是本机小程序缓存，不是账号级同步存储 |
| iOS/Android 隐私清理、系统存储优化、厂商清理工具 | 可能会 | 中等 | 取决于微信数据是否被清理；未找到微信官方逐项保证 |
| 系统更新 | 通常不应清空，但可能触发存储异常 | 低 | 没有官方承诺；需要真机回归验证 |
| 小程序删除/从最近使用移除 | 不等于必然清缓存 | 低到中 | 仅移除入口不一定删除缓存；具体清理策略未公开 |

**证据来源**

- `wx.setStorage` 文档镜像：数据生命周期跟小程序本身一致，用户主动删除或超过一定时间自动清理会失效。
- 小程序缓存教程：每个小程序有自己的缓存；用户存储空间不足时会清空最近最久未使用小程序缓存。
- `wx.setStorage` / `wx.clearStorage` / `wx.removeStorage` API 共同说明缓存可被程序或用户清除。

**2026-05 状态有效性**

“会丢”的大类明确；“多久未用会被清”“各系统版本是否保留”的概率与阈值未验证，需要在 iOS/Android 真机做长期闲置、系统清理、微信清理、重装/迁移测试才能定论。

**分级标签：需妥协**

## 5. 打包体积约束

**结论**

小程序主包仍应按 2MB 上限设计；分包可缓解体积，但加密启动路径如果在首屏/配对/解密都需要，实际很难全部放到冷分包。公开资料显示常见总包上限已从早期 8MB 演进到 20MB，但主包 2MB 是核心约束。加密库体积大致如下：libsodium.js 完整包约 188KB min+gzip；@noble/curves npm unpacked 约 MB 级，但按子模块 tree-shaking 后曲线代码可明显下降；node-forge 功能很宽，浏览器 bundle 偏重，不适合作为只做 E2EE 的首选；argon2-browser WASM 文件公开表格约 25KB，实际还要加 JS glue；hash-wasm 的 Argon2 gzipped 约 11KB。业务主包剩余空间取决于是否启用 npm 构建、tree-shaking、WASM 放置和分包策略。

**证据来源**

- 微信分包加载官方路径：`https://developers.weixin.qq.com/miniprogram/dev/framework/subpackages/basic.html`；公开引用普遍给出主包/单分包 2MB、总包 20MB 的当前约束，也有旧资料记录总包 8MB，说明历史上发生过调整。
- libsodium.js README：完整库 188KB minified + gzipped，包含 pure JS + WebAssembly。
- @noble/curves npm：包覆盖多曲线，npm 页面显示 unpacked size 约 1.25MB；README 支持按具体曲线导入。
- node-forge npm：提供 `forge.min.js` / `forge.all.min.js` 等浏览器 bundle，功能覆盖 TLS/PKI 等大量非本项目必需能力。
- argon2-browser npm：文档表格列出 `argon2.wasm` 约 25KB。
- hash-wasm npm 资料：Argon2 gzipped bundle 约 11KB。

**2026-05 状态有效性**

体积数字用于选型初筛有效，不能替代最终小程序构建产物。需要用微信开发者工具“代码依赖分析”对实际 bundle、压缩、分包后的主包大小做定论。

**分级标签：可承受**

## 6. 加密性能基准

**结论**

1KB 文本 AEAD 加解密和一次 ECDH 在现代手机上大概率不是瓶颈，预期量级通常在亚毫秒到数毫秒；Argon2id 才是需要 UX 预算的操作，按安全参数可能从数百毫秒到 1 秒以上，低端 Android 更慢。微信小程序真机未跑 benchmark，因此不能把社区/桌面/浏览器结果直接当验收数字。

| 操作 | 可引用量级 | 对 OurPresent 的含义 |
| --- | --- | --- |
| 1KB AES-GCM / AEAD | WebCrypto/原生常见 <1ms；JS/WASM AEAD 也通常远低于网络与 UI 延迟 | 单条记录加解密可承受 |
| P-256 / X25519 ECDH | Noble 在 Apple M4 上 p256 / x25519 约 1ms/0.5ms；移动端会更慢但通常仍是数 ms 级 | 配对时一次或少量协商可承受 |
| HKDF-SHA256 | SHA-256/HMAC 量级通常低于 ECDH | 不构成主要瓶颈 |
| Argon2id | 移动端口令 KDF 常见需要显式等待；Bitwarden 社区反馈移动端可到约 1s 或低端 Android 更慢 | 适合备份/恢复，不适合高频每条消息解锁 |

**证据来源**

- Noble curves benchmark：Apple M4 上 p256 ECDH 约 705 ops/s（约 1ms/op），x25519 约 1981 ops/s（约 0.5ms/op），且初始化会有 10ms+ 预计算成本。
- libsodium.js README：提供浏览器/WASM/pure JS 运行形态；libsodium 文档列出 AEAD 原语能力与约束。
- 社区与产品实践：Bitwarden Argon2 移动端讨论显示 Argon2 在移动端会明显慢于普通加密操作，低端 Android 可能更慢。
- 未在微信开发者工具和真机跑最小 benchmark。

**2026-05 状态有效性**

这里只能作为“风险排序”：AEAD/ECDH 可承受，Argon2 需 UX 预算。需要最小小程序 benchmark 在典型中端 Android 和主流 iPhone 上跑 1000 次 AES/AEAD、100 次 ECDH、3 档 Argon2 参数，记录 P50/P95 才能定论。

**分级标签：需妥协**

## 7. 用户自控备份载体

**结论**

把 `K_couple` 用用户口令派生密钥加密后导出，有三类可行载体：微信云、用户自己的网盘/文件、剪贴板/文本自存。它们的共同点是服务端或第三方只能看到密文和元数据，不能看到口令，前提是口令不上传、KDF 和解密只在客户端完成。区别是操作成本和元数据暴露不同：微信云路径最顺滑但平台可见访问与密文；用户网盘/文件自主性更强但导入导出复杂；剪贴板最轻但最容易被误粘贴、被系统/其他 App 暂存或丢失。

| 载体 | 服务端/平台能看到 | 看不到 | 用户成本 | 备注 |
| --- | --- | --- | --- | --- |
| 微信云 `wx.cloud` 云存储/云数据库 | 密文、文件名/记录名、访问时间、openid 相关元数据、权限配置 | 口令、明文 `K_couple` | 低 | 适合默认备份容器，但不等于本地 secure storage |
| 用户自己的网盘/文件 | 第三方平台看到密文文件和元数据 | 口令、明文钥匙 | 中到高 | 自主性强，恢复时要文件选择/导入 |
| 剪贴板/手动复制 | 剪贴板内容可被系统/输入法/其他 App 暂存或读取，取决于系统权限 | 若只复制密文则看不到口令 | 低到中 | 适合应急导出，不适合作长期唯一备份 |

**证据来源**

- 云开发文档/教程：云数据库、云存储、云函数是云端能力，可上传/下载文件和保存文档，并可用权限规则控制访问。
- 微信小程序剪贴板 API 官方路径：`https://developers.weixin.qq.com/miniprogram/dev/api/device/clipboard/wx.setClipboardData.html`；公开文档说明可设置系统剪贴板内容。
- 口令派生密钥本地解密的安全语义来自 E2EE 常规模型：服务端只拿密文，安全性取决于 KDF 参数、口令强度、客户端实现与备份文件认证。

**2026-05 状态有效性**

载体能力明确；隐私语义成立的前提是客户端实现不上传口令、不把明文钥匙写入云端/日志/剪贴板。文件选择、导入导出 UX 和微信云权限细节需要原型验证。

**分级标签：可承受**

## 8. 带外（OOB）配对通道

**结论**

小程序可以支持扫码、屏幕显示短码、复制短码、BLE 和部分 NFC 能力。对“两人物理在场”的配对，最可靠、用户成本最低的是“一方显示二维码/短码，另一方扫码并口头核对短码”。NFC/BLE 可作为增强通道，但不能作为唯一方案：设备支持、权限、系统版本、微信版本、稳定性和调试成本都会增加。小程序不能证明两人真实身份，只能证明双方设备参与了同一轮带外校验；MITM 防御仍依赖短码/二维码内容绑定和用户实际核对。

**证据来源**

- 微信开放文档 `wx.scanCode` 官方路径：`https://developers.weixin.qq.com/miniprogram/dev/api/device/scan/wx.scanCode.html`，用于调起扫码。
- 蓝牙 API `wx.openBluetoothAdapter` 文档镜像：初始化蓝牙模块后才能调用相关 API；错误码包含系统不支持、蓝牙不可用、连接失败、超时等。
- 微信开放文档 NFC 官方路径：`https://developers.weixin.qq.com/miniprogram/dev/api/device/nfc/wx.getNFCAdapter.html`；Taro 文档标注 `getNFCAdapter` 支持微信小程序。
- 短码/二维码显示只依赖普通 UI 渲染；不需要特殊系统能力。

**2026-05 状态有效性**

扫码和屏幕短码可作为稳定 OOB 基础。BLE/NFC 能力存在，但配对可靠性需要真机矩阵验证，尤其是 iOS/Android、权限弹窗、后台/前台生命周期与失败恢复。

**分级标签：可承受**

## 对配对协议设计的硬约束

- 配对设计不能假定微信小程序有完整 WebCrypto；必须允许 JS/WASM 加密库作为核心实现，并对微信真机兼容性做版本门槛。
- 熵源可以使用 `wx.getRandomValues`，但其他原语需要库内实现或封装。
- 本地长期密钥不能只因为放进 `wx.setStorage` 就被视为硬件保护；root/越狱/设备取证场景下不能承诺不可读。
- 配对必须有轻量重新配对路径，因为本地缓存可能被用户或微信清理。
- MITM 防御必须依赖扫码/短码等 OOB 用户核对；小程序平台本身不提供“对方真人身份”证明。
- BLE/NFC 只能作为增强体验，不能作为唯一 OOB 通道，除非真机矩阵验证通过并有扫码/短码 fallback。
- 加密库体积必须纳入首屏/配对路径预算；主包 2MB 是硬约束，WASM/大库应尽量懒加载或分包。

## 对设备丢失恢复 UX 的硬约束

- 只存 `wx.setStorage` 的 `K_couple` 会在清缓存、长期未用被清理、卸载重装、换机等场景丢失；恢复 UX 必须把“钥匙可能丢”当常态处理。
- 平台没有公开 Keychain/Keystore 等价接口时，不能承诺“换机后自动恢复端到端密钥”。
- 云开发只能保存被用户口令加密后的密钥密文；不能把它描述成本地安全保险箱。
- 用户口令备份需要 KDF 参数和等待时间预算；Argon2id 可能明显影响低端机体验。
- 同时丢失双方设备且没有用户自控备份时，服务端无法恢复 `K_couple`；这是 E2EE 事实边界。
- 剪贴板备份只适合作为临时导出/转移载体，不能作为默认唯一长期备份。
- 每次恢复都应假设旧设备公钥/本地缓存状态不可依赖，需要重新建立当前设备的密钥材料。
