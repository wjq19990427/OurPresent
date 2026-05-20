# OurPresent · miniprogram

Phase 2 微信小程序客户端。TypeScript + 纯 JS crypto bundle + 分包架构。

**现状**：M1 加密 smoke test 已在微信开发者工具模拟器通过。

详见 [`docs/PHASE2.md`](../docs/PHASE2.md) · [`docs/E2EE.md`](../docs/E2EE.md)。

## 开发环境

1. 安装[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 在本目录执行 `npm install`
3. 执行 `npm run build`，把 `miniprogram/` 下的 TypeScript 源码编译到 `dist/`
4. 导入本目录（`miniprogram/`）为项目
5. AppID：接口测试号或正式 AppID（填入 `project.config.json`）

## 编译说明

- 源码目录：`miniprogram/miniprogram/`
- 编译产物：`miniprogram/dist/`
- 微信开发者工具读取：`dist/`（见 `project.config.json` 的 `miniprogramRoot`）

常用命令：

```bash
cd miniprogram
npm install
npm run build
```

只做类型检查：

```bash
cd miniprogram
npm run typecheck
```

## 加密栈

- 随机数唯一入口：`wx.getRandomValues`
- X25519 ECDH + HKDF-SHA256 派生 32-byte 测试密钥
- XChaCha20-Poly1305 AEAD 加解密内容 / 媒体
- Argon2id（t=3, m=64MB）派生口令恢复密钥
- 构建时通过 esbuild 把加密入口打包为小程序可加载的 CommonJS 文件

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
