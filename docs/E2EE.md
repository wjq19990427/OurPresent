# OurPresent E2EE 协议设计

**最后更新**：2026-05-15
**性质**：架构设计决策。本文档是技术决策的"已定档"形态，不再回到 PM / 用户层讨论。后续如需调整由架构师评估并更新本文档。
**前置文档**：`docs/DIRECTION.md`（产品方向与隐私要求）·`docs/research/wechat-miniprogram-crypto.md`（小程序事实边界）

## 决策范围

**在本文档范围内**：

- 配对协议（双方设备如何建立共享密钥，含 MITM 防御）
- 密钥拓扑（每对情侣 / 每台设备需要什么密钥、生命周期）
- 备份与恢复机制（伴侣协助 + 用户口令两路）
- 加密原语与库选型
- 元数据最小化原则

**不在本文档范围内**：

- 服务端 schema / 存储引擎（待 mini-program 项目启动时另开设计）
- 具体 UI 设计 / 文案（产品 / 设计师层面）
- 时间锁的服务端派送实现细节（独立的后端契约任务）

## 1. 密钥拓扑

每对情侣（couple）持有的密钥材料：

| 密钥 | 类型 | 在哪 | 生命周期 |
|------|------|------|---------|
| `K_couple` | 256-bit 对称密钥 | 双方设备 `wx.setStorage` | 整个关系生命周期（一旦丢失走恢复流程重得） |
| `K_backup`（可选） | 由用户口令 + Argon2id 派生 | 不存储，每次解封时即时派生 | 即时使用 |
| `IdentityKey_dev` | X25519 设备级长期密钥对 | 本设备 `wx.setStorage` | 设备级，吊销时作废 |

**说明**：

- `K_couple` 是唯一**用来加密内容**的密钥。所有 sessions / comments / 媒体都用它派生的子密钥 AEAD 加密
- `IdentityKey_dev` 只在两种场景被用到：配对时的 ECDH、恢复时作为新设备的接收公钥
- 服务端**永远只看到**：`IdentityKey_dev` 的公钥、每个用户 / 每对情侣的元数据（couple_id / 时间戳 / unlock_at），以及所有内容的密文

## 2. 配对协议

### 2.1 流程

A 是发起方，B 是被邀请方。两人**必须物理在场或电话在线**完成短码核对。

1. **A 设备生成会话**：
   - 生成临时 X25519 密钥对 `(a_eph_priv, a_eph_pub)`
   - 向服务端创建一个 `pairing_session_id`（10 分钟有效）
   - 屏幕显示二维码，内容：`{ pairing_session_id, a_eph_pub, A_identity_pub }`

2. **B 扫码**（`wx.scanCode`）：
   - 解析二维码
   - 生成临时 X25519 密钥对 `(b_eph_priv, b_eph_pub)`
   - 算共享密钥 `ss = X25519(b_eph_priv, a_eph_pub)`
   - 通过服务端把 `{ b_eph_pub, B_identity_pub }` 提交到 `pairing_session_id`

3. **A 设备接收 B 的公钥**：
   - 服务端推送 `b_eph_pub` 到 A
   - A 算 `ss = X25519(a_eph_priv, b_eph_pub)`
   - 双方此时已经协商出相同的 `ss`

4. **K_couple 派生**：
   - `K_couple = HKDF-SHA256(ss, salt=pairing_session_id, info="ourpresent-couple-key-v1", L=32)`

5. **短码（SAS）核对——MITM 防御核心**：
   - 双方各自计算 `verify_code = HKDF-SHA256(ss, salt=pairing_session_id, info="ourpresent-pairing-verify-v1", L=4)` → 转十进制 → 取后 6 位
   - 双方屏幕显示同一个 6 位数字
   - **用户必须当面 / 电话口头核对**："你看到的是 318472 对吗？"
   - 匹配 → 各自点"确认"按钮 → 配对完成
   - 不匹配 → 立即终止 + 警告用户"有人在中间攻击，重试或换网络"

6. **服务端绑定**：
   - 两侧各自向服务端发送 "pairing_complete" 签名（用 IdentityKey 签 `pairing_session_id`）
   - 服务端记录 couple_id ↔ (A_identity_pub, B_identity_pub) 的绑定
   - 服务端**不持有 K_couple**

### 2.2 MITM 模型

- 攻击者控制服务端 / 网络 → 能交换公钥但**无法伪造 short code**（伪造 ss 就要破 X25519，伪造短码就要破 HKDF）
- 攻击者必须能让 A 和 B 看到不同的短码并各自相信对方核对过 → 短码不一致用户会发现
- **唯一防不住的场景**：攻击者同时控制了 A 和 B 的电话信道或物理见面（接力换设备屏幕）——这超出 E2EE 防御范围，属于人身威胁

### 2.3 失败处理

- `pairing_session_id` 10 分钟超时则作废，要求重来
- 短码不匹配：双方都终止，提示"换网络重试"
- 任一方网络异常：会话保留 10 分钟可恢复

## 3. 备份与恢复

### 3.1 默认：伴侣协助恢复

**适用**：A 丢手机 / 清缓存 / 换新机，B 设备仍有 `K_couple`

1. A 新设备登录账号，进入"恢复"流程
2. 新设备生成临时 X25519 密钥对 `(rec_priv, rec_pub)`，向服务端提交 `{rec_pub, recovery_request_id}`
3. 服务端推送通知到 B 的设备："A 申请恢复，请确认"
4. **B 与 A 必须物理在场或电话在线核对短码**：
   - 服务端把 `recovery_request_id` 和 `rec_pub` 送给 B
   - B 算 `verify_code = HKDF-SHA256(rec_pub, salt=recovery_request_id, info="ourpresent-recovery-verify-v1", L=4)` → 6 位
   - A 设备也独立算同一个 `verify_code`
   - 两人口头核对
5. B 确认后：
   - B 用 A 新设备的 `rec_pub` 做 X25519 → 派生 `K_wrap = HKDF(...)` → AEAD 加密 `K_couple`
   - 把密文通过服务端中转给 A 新设备
6. A 新设备解出 `K_couple`，存入本地 `wx.setStorage`
7. 服务端吊销 A 旧设备的 IdentityKey；A 新设备的 IdentityKey 注册为新设备

**服务端全程**：只看到公钥和密文，从不持有 `K_couple` 或解包过的 `K_wrap`。

### 3.2 增强：用户口令备份（强烈建议但不强制）

**适用**：A 和 B 都丢设备 / 都清掉小程序 / 都不可用

**设置时机**：配对完成后立刻引导，UX 文案——"这是我们对你隐私的承诺的代价：连我们也救不回。强烈建议你设一个**只有你自己记得**的口令做最后保险。"

**机制**：

1. 用户输入口令（最少 8 字符，强度提示）
2. 设备本地生成 `salt = random(16)`
3. 派生 `K_backup = Argon2id(passphrase, salt, t=3, m=64MB, p=1)`（参数固定为本协议常量，方便恢复）
4. `backup_blob = AEAD-Encrypt(K_backup, K_couple)`
5. 上传 `{ couple_id, backup_blob, salt, kdf_params }` 到 `wx.cloud`
6. 客户端**不保存口令**，每次恢复时让用户重新输入

**Argon2 参数选择理由**：
- `t=3, m=64MB, p=1`：task-23 报告里 Bitwarden 移动端实测大约 1 秒级
- 一次性 UX，可承受
- 后续如低端机投诉强烈，可降到 `m=32MB`（要写进协议常量历史记录）

**恢复**：

1. 用户在新设备输入账号 + 口令
2. 从 `wx.cloud` 拉 `backup_blob` + `salt`
3. 派生 `K_backup` → 解 AEAD → 得到 `K_couple`
4. 写入本地 `wx.setStorage`

**口令丢失 = 无法走此路径恢复**。继续往下走伴侣协助流程，或接受数据丢失。

### 3.3 兜底：双方设备 + 口令全失

- 服务端**技术上无能为力**
- UX 文案要正向表达："这是真 E2EE 的证据，不是我们的失职"
- 用户可以重新配对建立新的 couple_id，但旧密文永远不可解

### 3.4 用户自控文件备份（高级选项）

- 把 `backup_blob` + `salt` + `kdf_params` 打包成单个 `.ourpresent-backup` 文件
- 调用小程序文件 API 让用户下载到本地 / 微信文件传输助手
- 隐私语义：和 wx.cloud 一致（服务端没看过明文），但用户可控性更强
- 视为高级选项，不放主流程

## 4. 加密原语与库选型

| 用途 | 算法 | 库 |
|------|------|-----|
| ECDH | X25519 | libsodium.js |
| AEAD | XChaCha20-Poly1305 | libsodium.js |
| 哈希 / HMAC | SHA-256 | libsodium.js（HKDF 自己组装） |
| 口令 KDF | Argon2id | hash-wasm 或 libsodium.js |
| 随机数 | `wx.getRandomValues` | 平台内建 |

**选型理由**：

- **libsodium.js**：task-23 报告确认体积约 188KB min+gzip，覆盖 X25519 + XChaCha20-Poly1305 + Argon2，**优先用它一个库覆盖大部分**
- **Argon2 单独考虑 hash-wasm**：如 libsodium.js 的 Argon2 实现在小程序运行时上有兼容性问题，回落到 hash-wasm（WASM 体积约 11KB gzip，更轻）
- **不选 AES-GCM**：XChaCha20-Poly1305 的 nonce 是 24 字节随机生成不怕碰撞，AES-GCM 12 字节 nonce 在密钥重用场景下风险更高。XChaCha 在 JS/WASM 上性能也好
- **不选 @noble/curves**：体积偏大（unpacked ~1.25MB），单一原语库的优势在 tree-shaking 后未必赢 libsodium，且签名风格不统一

**懒加载策略**（task-23 体积约束派生）：

- 配对 / 恢复路径上的库放主包
- Argon2 只在备份设置 / 恢复时用，放分包，按需加载
- 整体加密栈预算 ≤ 300KB（主包余量内）

## 5. 元数据最小化

服务端可见的元数据严格限定：

| 字段 | 可见 | 理由 |
|------|------|------|
| `couple_id` | 是 | 服务端必须知道这条数据属于哪对情侣才能路由 |
| `unlock_at` | 是 | 派送门禁需要 |
| `created_at` | 是 | 索引必需 |
| `author_user_id` | 是 | 派送门禁 + 区分撰写方与接收方 |
| `session_id` | 是 | 引用与索引 |
| `comment_count` / `is_pending` 等状态 | 是（保持明文） | UX 需要即时统计 |
| **内容 / 主题 / 感受 / 原因** | **否（必须密文）** | 隐私核心 |
| **媒体文件** | **否（必须密文）** | 隐私核心 |

**反模式**：不要在元数据里塞"标题"、"摘要"、"标签"这类暗中泄露内容的字段，无论 UX 看起来多便利。

## 6. 实现里程碑（无时间承诺，按依赖排序）

1. **小程序工程脚手架** + libsodium.js 跑通基本 AEAD / ECDH / Argon2 smoke test（验证 task-23 报告里所有"未验证"项）
2. **配对协议端到端实现** + 短码 SAS UX
3. **基本的延时记录写入流程**（客户端加密 → 服务端密文 + 元数据）
4. **延时派送门禁**（服务端对接收方延迟派送）
5. **伴侣协助恢复**
6. **用户口令备份 + 恢复**
7. **冻结期销毁**（服务端按命令删除密文 + 元数据）
8. **跨设备同步**（同一用户多设备共享 K_couple）

## 7. 与现有代码的关系

当前 Alpha Streamlit + SQLite 形态**不会引入 E2EE**——Streamlit 是服务端渲染，密钥放服务端本身不构成 Tier 1 承诺。Alpha 继续作为延时表达 UX 验证载体，E2EE 协议落地随 mini-program 工程一并启动。

`task-21`（PG 迁移）继续冷藏：未来的服务端形态是"密文 BLOB + 明文元数据索引"，与当前任务卡的"整库 dict 明文"假设不兼容，届时另写。
