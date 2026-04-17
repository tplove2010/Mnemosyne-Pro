---
name: mnemosyne-pro
description: OpenClaw memory system automation sync skill - solves AI cross-session forgetfulness by automatically syncing daily session stats to Mnemosyne inbox
---

# Mnemosyne Pro 1.3

**Version**: 1.3  
**Platform**: OpenClaw  
**Author**: William

## Overview

OpenClaw automated memory sync skill package - solves AI cross-session forgetfulness.

## Core Components

| Component | Path | Description |
|-----------|------|-------------|
| Sync Script | `scripts/memory-sync.js` | Heartbeat sync wrapper |
| Config | `.mnemosyne/config.jsonc` | Mnemosyne 1.3 config |
| Docs | (inline in this file) | Full installation guide |

## Installation

See [README.md](README.md)

## Quick Start

1. Copy `scripts/memory-sync.js` → `{workspace}/scripts/`
2. Copy `.mnemosyne/config.jsonc` → `{workspace}/.mnemosyne/`
3. Add to `HEARTBEAT.md`:
   ```markdown
   - Run `node scripts/memory-sync.js` to sync daily session stats to Mnemosyne inbox.
   ```
4. Verify:
   ```bash
   cd {workspace}
   node scripts/memory-sync.js
   ```

## Workflow

```
Heartbeat (every 4h)
    ↓
memory-sync.js reads sessions.json
    ↓
Generate inbox file (.mnemosyne/inbox/feishu/)
    ↓
Update intake-state.json
    ↓
Mnemosyne Process (reconcile + publish)
    ↓
Memory persisted to memory/global/preferences.md
```

## Dependencies

- OpenClaw (running)
- Node.js (comes with OpenClaw)
- Mnemosyne 1.3+

## Version History

- **1.3** (current): Semantic recall, deduplication, clustering, event classification
- **1.1**: Initial release, Heartbeat auto-sync support

## Files

```
mnemosyne-pro/
├── scripts/
│   └── memory-sync.js          # Core sync script
├── .mnemosyne/
│   └── config.jsonc            # Configuration
├── SKILL.md                    # This file
├── README.md                   # Full documentation
├── VERSION                     # 1.3
└── LICENSE                     # MIT
```