# task-29 · M3：配对协议端到端

## 变更说明

**类型**：新功能

两台手机通过扫码 + 短码核对完成密钥协商，各自设备上的 `K_couple` 完全一致，且服务端中间人攻击（伪造公钥）时短码不匹配可被用户发现。这是 Phase 2 E2EE 链路的第一个端到端里程碑。

---

## 前置条件

- M1（`miniprogram/` 加密栈 `@noble/*` 已就位）和 M2（`server/` Docker Compose 本地跑通）均已完成
- 协议细节见 `docs/E2EE.md` 第 2 节（配对协议），下面只写实现约束，不重复协议描述
- **需要 AppID**：`wx.scanCode` 和真机预览必须有有效 AppID，填入 `miniprogram/project.config.json`

## 工作范围

涉及目录：`server/` + `miniprogram/`

---

### 服务端（`server/`）

**DB schema**（在 `server/app/` 新建 migration 或 startup 建表，无需 Alembic，`CREATE TABLE IF NOT EXISTS` 即可）：

```
pairing_sessions(
  id TEXT PRIMARY KEY,          -- UUID
  a_eph_pub BYTEA NOT NULL,     -- A 的临时公钥（32 bytes）
  a_identity_pub BYTEA NOT NULL,-- A 的 identity 公钥
  b_eph_pub BYTEA,              -- B 扫码后填入
  b_identity_pub BYTEA,
  status TEXT NOT NULL DEFAULT 'waiting', -- waiting / peered / complete
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL         -- created_at + 10min
)

users(
  id TEXT PRIMARY KEY,
  identity_pub BYTEA NOT NULL UNIQUE
)

couples(
  id TEXT PRIMARY KEY,
  user_a_id TEXT NOT NULL REFERENCES users(id),
  user_b_id TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

**REST endpoints**（新建 `server/app/routers/pairing.py`）：

- `POST /pairing/sessions`  
  Body: `{ a_eph_pub: hex, a_identity_pub: hex }`  
  Action: 写入 pairing_sessions，返回 `{ session_id, expires_at }`

- `PUT /pairing/sessions/{session_id}/peer`  
  Body: `{ b_eph_pub: hex, b_identity_pub: hex }`  
  Action: 填入 b 侧公钥，status → `peered`，通过 WebSocket 推送给 A；如会话已过期或状态不是 `waiting` 则 400

- `POST /pairing/sessions/{session_id}/complete`  
  Body: `{ identity_pub: hex, signature: hex }`  
  Action: 校验 signature（用 identity_pub 签 session_id 的 Ed25519 签名，或简化为 HMAC-SHA256）；双方都提交后 status → `complete`，写入 users + couples 表，返回 `{ couple_id }`

**WebSocket**（在 `server/app/routers/pairing.py` 或独立 `ws.py`）：

- `WS /pairing/sessions/{session_id}/watch`  
  A 发起配对后连接此 WebSocket 等待 B 加入  
  B 调用 PUT peer 接口后，服务端向此连接推送 `{ event: "peer_joined", b_eph_pub: hex, b_identity_pub: hex }`  
  完成后推送 `{ event: "complete", couple_id }`

**约束**：
- 过期的会话拒绝所有写操作（PUT / POST complete）
- 服务端不做 X25519 / HKDF 计算，不持有 K_couple
- `POST /pairing/sessions/{session_id}/complete` 的签名验证：M3 先用 HMAC-SHA256(session_id, identity_pub) 做简化版校验，正式 Ed25519 签名留 M4

---

### 客户端（`miniprogram/`）

**加密分包 `subpackages/crypto/index.js`**：

用 `@noble/curves/x25519`（`npm install @noble/curves`）替换现有手写 BigInt X25519 实现，对外接口保持不变（`x25519ScalarMult(secret, point)` 签名或直接暴露 `X25519` 对象）。其余 `@noble/hashes` / `@noble/ciphers` 用法不变。

新增导出：
- `generateX25519Keypair()` → `{ privateKey: Uint8Array, publicKey: Uint8Array }`，内部用 `wx.getRandomValues` 生成随机私钥
- `deriveKCouple(sharedSecret, sessionId)` → 32-byte `K_couple`，调用 `HKDF-SHA256(ss, salt=sessionId, info="ourpresent-couple-key-v1")`
- `deriveSasCode(sharedSecret, sessionId)` → 6 位字符串，调用 `HKDF-SHA256(ss, salt=sessionId, info="ourpresent-pairing-verify-v1", L=4)` → 十进制取后 6 位

**配对页面**（新建 `pages/pair/pair`，加入主包 pages）：

A 侧流程：
1. 调用 `generateX25519Keypair()` 生成临时密钥对
2. 调用 `POST /pairing/sessions`，获取 `session_id`
3. 将 `{ session_id, a_eph_pub, a_identity_pub }` 编码为 JSON 字符串后用 `wx.createQRCode`（或展示文本供测试）渲染二维码
4. 连接 `WS /pairing/sessions/{session_id}/watch`，等待 peer_joined 事件
5. 收到事件后计算 `K_couple` 和 SAS 短码，展示短码，等用户点"核对通过"
6. 点击后调用 `POST complete`，把 K_couple 写入 `wx.setStorage('k_couple')`，跳转首页

B 侧流程：
1. 点击"扫码配对"，调用 `wx.scanCode`
2. 解析二维码 JSON，生成临时密钥对
3. 计算 `K_couple` 和 SAS 短码
4. 展示短码，等用户核对后点"确认"
5. 调用 `PUT /pairing/sessions/{session_id}/peer`，再调用 `POST complete`
6. 写 K_couple 到 `wx.setStorage`，跳转首页

服务端 API 地址从 `wx.getStorageSync('api_base_url')` 读取，首次启动时从 app.ts 里的环境常量写入（硬编码 cloudflared 临时域名即可，M4 再做配置页面）。

**约束**：
- 短码核对失败（用户点"不一致"）：清除所有临时密钥，提示"重试或换网络"，不跳转
- K_couple 写 storage 前必须已完成短码核对确认
- 不实现多设备（一人一台手机），不实现账号密码，用 identity_pub 作为用户身份即可

---

## 验收

- [ ] A 设备显示配对二维码，B 扫码后双方都显示 **相同的** 6 位短码
- [ ] 双方各自点"核对通过"后，`wx.getStorageSync('k_couple')` 在两台设备上返回的字节序列完全相同（可在 smoke/debug 页面打印 hex 比对）
- [ ] 服务端 DB 中 `couples` 表写入一条记录
- [ ] 手动修改服务端中转的 `b_eph_pub`（伪造 MITM）后，双方短码 **不一致**，用户拒绝，配对不完成
- [ ] 10 分钟内不操作，会话超时，双方无法继续（服务端返回 4xx）

## 并行约束

- 依赖 task-27（M1）+ task-28（M2）完成 ✅
- 单张卡不可拆分（server/ + miniprogram/ 耦合，接口必须同步）
- 完成后进入 M4（延时写入 + 派送门禁）
