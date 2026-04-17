# Mnemosyne Pro 1.3

> OpenClaw 记忆系统自动化同步技能包 - 让 AI 持续"记住"你的偏好和对话

## 特性

- ✅ **自动同步**: 与 OpenClaw Heartbeat 无缝集成
- ✅ **结构化存储**: 每日会话摘要 → Inbox → Mnemosyne 处理
- ✅ **零维护**: 配置一次，长期自动运行
- ✅ **跨会话记忆**: 解决 AI 遗忘问题
- ✅ **全平台支持**: Windows / macOS / Linux

---

## 快速开始

### 前置要求

- OpenClaw 已安装并运行
- Node.js 可用 (OpenClaw 自带)

---

## 安装

### 通用步骤（所有系统）

1. **复制完整 Pro 技能包到工作区**
   
   复制整个 mnemosyne-pro 目录到你的 OpenClaw 工作区：
   ```
   mnemosyne-pro/ → {workspace}/
   ```

2. **初始化运行时结构**
   ```bash
   cd {workspace}
   python scripts/init_runtime.py . --create-memory-md
   ```

3. **（可选）配置 Heartbeat 自动同步**
   
   在工作区根目录的 `HEARTBEAT.md` 最后添加：
   ```markdown
   - Run `node scripts/memory-sync.js` to sync daily session stats to Mnemosyne inbox.
   ```

4. **验证安装**
   - 方式 1（手动同步）：
     ```bash
     node scripts/memory-sync.js
     ```
   - 方式 2（初始状态检查）：
     ```bash
     python scripts/report_status.py .
     ```

---

### Core vs Enhanced 模式

**Core 模式（默认）**
- 无需外部依赖，完整主链开箱即用
- 脚本：init_runtime.py → stage_intake.py → reconcile.py → publish.py → recall → report
- 包含文件：memory-sync.js (Heartbeat wrapper)

**Enhanced 模式**
- 当前状态：**未连接到主链**
- 预留文件：embedding_client.py, semantic_utils.py
- 配置项：semantic_recall, semantic_dedupe（当前为注释状态）
- 未来可能通过外部 embedding 服务启用

---

### Windows 安装

#### 使用 PowerShell

```powershell
# 1. 创建 scripts 目录（如果不存在）
New-Item -ItemType Directory -Path "$env:USERPROFILE\.openclaw\workspace\scripts" -Force

# 2. 复制脚本
Copy-Item -Path ".\scripts\memory-sync.js" -Destination "$env:USERPROFILE\.openclaw\workspace\scripts\"

# 3. 创建 .mnemosyne 目录（如果不存在）
New-Item -ItemType Directory -Path "$env:USERPROFILE\.openclaw\workspace\.mnemosyne" -Force

# 4. 复制配置
Copy-Item -Path ".\.mnemosyne\config.jsonc" -Destination "$env:USERPROFILE\.openclaw\workspace\.mnemosyne\"

# 5. 验证
node "$env:USERPROFILE\.openclaw\workspace\scripts\memory-sync.js"
```

#### Windows 路径占位符

| 占位符 | 实际路径示例 |
|--------|--------------|
| `{workspace}` | `C:\Users\你的用户名\.openclaw\workspace` |

---

### macOS 安装

#### 使用终端

```bash
# 1. 创建 scripts 目录
mkdir -p ~/.openclaw/workspace/scripts

# 2. 复制脚本
cp ./scripts/memory-sync.js ~/.openclaw/workspace/scripts/

# 3. 创建 .mnemosyne 目录
mkdir -p ~/.openclaw/workspace/.mnemosyne

# 4. 复制配置
cp ./.mnemosyne/config.jsonc ~/.openclaw/workspace/.mnemosyne/

# 5. 验证
cd ~/.openclaw/workspace
node scripts/memory-sync.js
```

#### macOS 路径占位符

| 占位符 | 实际路径示例 |
|--------|--------------|
| `{workspace}` | `/Users/你的用户名/.openclaw/workspace` |
| `~` | `/Users/你的用户名` |

---

### Linux 安装

#### 使用终端

```bash
# 1. 创建 scripts 目录
mkdir -p ~/.openclaw/workspace/scripts

# 2. 复制脚本
cp ./scripts/memory-sync.js ~/.openclaw/workspace/scripts/

# 3. 创建 .mnemosyne 目录
mkdir -p ~/.openclaw/workspace/.mnemosyne

# 4. 复制配置
cp ./.mnemosyne/config.jsonc ~/.openclaw/workspace/.mnemosyne/

# 5. 验证
cd ~/.openclaw/workspace
node scripts/memory-sync.js
```

#### Linux 路径占位符

| 占位符 | 实际路径示例 |
|--------|--------------|
| `{workspace}` | `/home/你的用户名/.openclaw/workspace` |
| `~` | `/home/你的用户名` |

---

## 查找你的 OpenClaw 工作区

```bash
# 命令行快速定位
# Windows
dir "%USERPROFILE%\.openclaw\workspace"

# macOS / Linux
ls -la ~/.openclaw/workspace
```

如果工作区在自定义位置，使用你自己的路径。

---

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

---

## 文件结构

```
mnemosyne-pro/                          # 完整的 Mnemosyne Pro 技能包
├── scripts/                            # 核心主链脚本
│   ├── init_runtime.py                 # 初始化运行时结构
│   ├── stage_intake.py                 # 处理 inbox → staged
│   ├── reconcile.py                    # 冲突检测与解决
│   ├── publish.py                      # 写入持久化 memory
│   ├── report_status.py                # 运行时状态报告
│   ├── export_recall.py                # 导出 recall 包
│   ├── archive_inbox.py                # 归档已处理 inbox
│   ├── memory-sync.js                  # Heartbeat 同步封装
│   ├── common.py                       # 公共函数
│   ├── embedding_client.py             # 嵌入增强（可选）
│   └── semantic_utils.py               # 语义工具（可选）
├── assets/
│   └── mnemosyne.config.jsonc         # 配置模板
├── .mnemosyne/
│   └── config.jsonc                    # 运行时配置
├── SKILL.md                            # 主技能定义
└── README.md                           # 本文件
```

---

## 配置

无需修改，脚本开箱即用。可选配置见 `.mnemosyne/config.jsonc`

---

## 主链命令

```bash
# 初始化（首次）
python scripts/init_runtime.py <workspace> --create-memory-md

# 每日同步（Heartbeat 触发）
node scripts/memory-sync.js

# 手动处理流程
python scripts/stage_intake.py <workspace>     # 处理 inbox
python scripts/reconcile.py <workspace>        # 冲突解决
python scripts/publish.py <workspace>          # 写入 memory
python scripts/report_status.py <workspace>    # 状态报告
python scripts/export_recall.py <workspace> --query "..."
python scripts/archive_inbox.py <workspace>    # 归档清理
```

---

## 卸载

```bash
# 删除脚本文件
# Windows
Remove-Item "$env:USERPROFILE\.openclaw\workspace\scripts\memory-sync.js"

# macOS / Linux
rm ~/.openclaw/workspace/scripts/memory-sync.js

# 移除 HEARTBEAT.md 中的调用指令
```

---

## 故障排除

### 问题：找不到 Node.js

**症状**: `node: command not found`

**解决**: OpenClaw 自带 Node.js，直接用完整路径：
```bash
# Windows (示例)
& "C:\Users\你的用户\AppData\Local\pnpm\node.exe" scripts/memory-sync.js

# macOS / Linux
# 通常无需额外配置
```

### 问题：路径错误

**症状**: `[MemorySync] Sessions read error`

**解决**: 确保 `.openclaw` 目录在 `workspace` 的上一级
```
你的工作区/
├── .openclaw/     ← 父目录
├── scripts/       ← 放这里
├── .mnemosyne/    ← 放这里
└── ...
```

---

## 已知兼容环境

| 操作系统 | 状态 | 测试版本 |
|----------|------|----------|
| Windows 10/11 | ✅ 已测试 | Windows_NT 10.0 |
| macOS | ✅ 兼容 | 所有现代版本 |
| Linux (Ubuntu/Debian) | ✅ 兼容 | 20.04+ |
| Linux (CentOS/RHEL) | ✅ 兼容 | 8+ |

---

## 更新日志

### 1.3 (2026-04-17)
- 语义 Recall 检索（embedding + keyword fallback）
- 语义去重提示（semantic_dedupe, 相似度 ≥ 0.80）
- 语义聚类归并（success/failure 事件自动合并）
- 事件语义分类（semantic_event_classification）

### 1.1 (2026-04-15)
- 首次发布
- 支持 heartbeat 自动同步
- 内置路径修复和错误处理
- 添加全平台安装文档（Windows/macOS/Linux）

---

## 开源协议

MIT License

---

Built for OpenClaw + William's Memory Optimization 🌷