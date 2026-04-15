# Mnemosyne Pro 1.1 - OpenClaw 记忆系统技能包

> 完全自动化OpenClaw的记忆同步系统，让AI持续"记住"你的偏好和对话

## 特性

- ✅ **自动同步**: 与 OpenClaw Heartbeat 无缝集成
- ✅ **结构化存储**: 每日会话摘要 → Inbox → Mnemosyne 处理
- ✅ **零维护**: 配置一次，长期自动运行
- ✅ **跨会话记忆**: 解决 AI 遗忘问题

## 快速开始

### 前置要求

- OpenClaw 已安装并运行
- Node.js 可用 (OpenClaw 自带)

### 安装

1. **复制脚本**
   ```bash
   # 将 scripts/memory-sync.js 复制到你的 workspace/scripts/
   ```

2. **修改 HEARTBEAT.md**
   ```markdown
   # 在最后添加:
   - Run `node scripts/memory-sync.js` to sync daily session stats to Mnemosyne inbox.
   ```

3. **验证**
   ```bash
   node scripts/memory-sync.js
   # 应输出:
   # [MemorySync] ✅ Daily memory sync complete
   ```

## 工作原理

```
Heartbeat (每4h)
    ↓
memory-sync.js 读取 sessions.json
    ↓
生成 inbox 文件 (.mnemosyne/inbox/feishu/)
    ↓
更新 intake-state.json
    ↓
Mnemosyne 处理 (reconcile + publish)
    ↓
记忆持久化到 memory/global/preferences.md
```

## 文件说明

| 文件 | 作用 |
|------|------|
| `memory-sync.js` | 核心同步脚本 |
| `config.jsonc` | Mnemosyne 配置 |
| `SKILL.md` | 技能定义（可选） |

## 配置

无需修改，脚本开箱即用。可选配置见 `.mnemosyne/config.jsonc`

## 卸载

```bash
# 删除脚本
rm scripts/memory-sync.js

# 移除 HEARTBEAT.md 中的调用指令
```

## 开源协议

MIT License

---

Built for OpenClaw + William's Memory Optimization 🌷