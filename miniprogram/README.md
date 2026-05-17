# OurPresent · miniprogram

Phase 2 微信小程序客户端。TypeScript + libsodium.js + 分包架构。

**现状**：M0 骨架，M1 实现工将在此目录补全加密 smoke test。

详见 [`docs/PHASE2.md`](../docs/PHASE2.md) · [`docs/E2EE.md`](../docs/E2EE.md)。

## 开发环境

1. 安装[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 导入本目录（`miniprogram/`）为项目
3. AppID：接口测试号或正式 AppID（填入 `project.config.json`）

## 加密栈

- `libsodium.js`（`sodium-native`-based WASM 分包）
- X25519 ECDH + HKDF-SHA256 派生 `K_couple`
- XChaCha20-Poly1305 AEAD 加解密内容 / 媒体
- Argon2id（t=3, m=64MB）派生口令恢复密钥

## 目录结构（规划中）

```
miniprogram/
├── miniprogram/        # 小程序源码
│   ├── app.json
│   ├── app.ts
│   ├── app.wxss
│   ├── pages/
│   │   └── index/
│   └── subpackages/    # M1 加密分包
│       └── crypto/
├── project.config.json
└── typings/
```
