# Memory Sync - Mnemosyne Pro 1.1

**版本**: 1.1  
**用途**: OpenClaw 记忆系统自动化同步技能包  
**依赖**: OpenClaw + Node.js

---

## 功能简介

- **自动 intake**: 每次 heartbeat 时读取当日会话摘要
- **写入 inbox**: 生成结构化 inbox 文件供 Mnemosyne 处理
- **状态管理**: 自动更新 intake-state、staged-candidates、publish-registry
- **无缝集成**: 与 OpenClaw HEARTBEAT 机制原生集成

---

## 安装步骤

### 1. 安装脚本

将 `scripts/memory-sync.js` 复制到工作区的 `scripts/` 目录：

```
workspace/
└── scripts/
    └── memory-sync.js  ← 复制到此
```

### 2. 配置 HEARTBEAT.md

在工作区根目录的 `HEARTBEAT.md` 中添加以下指令：

```markdown
- Run `node scripts/memory-sync.js` to sync daily session stats to Mnemosyne inbox.
```

### 3. 配置 .mnemosyne

确保 `.mnemosyne/config.jsonc` 存在且配置正确（见下文）

---

## 文件结构

```
workspace/
├── .mnemosyne/
│   ├── config.jsonc          # Pro 1.1 配置文件
│   ├── state/
│   │   ├── intake-state.json
│   │   └── publish-registry.json
│   ├── cache/
│   │   ├── staged-candidates.json
│   │   └── reconciled-proposals.json
│   └── inbox/feishu/         # 自动生成
├── scripts/
│   └── memory-sync.js        # 同步脚本
├── memory/
│   ├── YYYY-MM-DD.md         # 每日记忆
│   └── global/
│       └── preferences.md    # 长期偏好
└── HEARTBEAT.md              # 需添加调用指令
```

---

## 配置说明 (.mnemosyne/config.jsonc)

```jsonc
{
  "version": "1.1",
  // 作用域策略
  "sharing_mode": "scoped",
  "scope_resolution": "narrowest-first",
  
  // 晋升条件
  "global_promotion": {
    "enabled": true,
    "require_explicit": true,
    "min_repeat_count": 2
  },
  
  // 调度（需外部触发）
  "schedule": {
    "enabled": true,
    "frequency": "daily",
    "time": "03:00"
  },
  
  // 发布目标
  "publish": {
    "global_target": "memory/global/preferences.md"
  }
}
```

---

## 触发方式

### 方式 1: Heartbeat 自动触发（推荐）

修改 `HEARTBEAT.md` 后，每次 heartbeat (默认 4h) 会自动运行脚本

### 方式 2: 手动运行

```bash
cd /path/to/workspace
node scripts/memory-sync.js
```

---

## 输出示例

运行后生成的 inbox 文件：

```markdown
---
source: heartbeat
topic: Daily Session Summary
created_at: 2026-04-15T15:51:18.810Z
confidence: medium
explicitness: explicit
---

今日会话摘要:
- 活跃会话: 3 个 (running: 2, done: 1)
- Input Tokens: 93247
- Output Tokens: 9806
- 总 Token: 175460

关键事件: Daily memory sync via heartbeat - Mnemosyne Pro 1.1 wrapper
```

---

## 卸载

1. 删除 `scripts/memory-sync.js`
2. 从 `HEARTBEAT.md` 移除调用指令
3. `rm -rf .mnemosyne/` (可选)

---

## 更新日志

### 1.1 (当前)
- 修复路径 bug（OPENCLAW_DIR 相对路径）
- 修复文件名重复 bug
- 优化 inbox 内容格式

### 1.0
- 初始版本
- 支持 heartbeat 自动同步