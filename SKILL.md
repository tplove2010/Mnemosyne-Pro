---
name: mnemosyne-pro
description: OpenClaw durable memory governance system - manages cross-session memory including intake, reconcile, publish, recall, and archive. Includes semantic enhancement via embedding.
---

# Mnemosyne Pro 1.3

**Version**: 1.3  
**Platform**: OpenClaw  
**Author**: William

## Overview

Mnemosyne Pro is the **durable memory governance system** for OpenClaw. It ensures AI remembers user preferences and conversation context across sessions.

This is the **complete Mnemosyne Pro skill package** (not just a sync submodule).

## Core Components (Full Core Chain)

| Component | Path | Description |
|-----------|------|-------------|
| Init Runtime | `scripts/init_runtime.py` | Initialize complete runtime structure |
| Stage Intake | `scripts/stage_intake.py` | Process inbox events to staged candidates |
| Reconcile | `scripts/reconcile.py` | Conflict detection and resolution |
| Publish | `scripts/publish.py` | Write approved memory to durable storage |
| Report Status | `scripts/report_status.py` | Runtime status and statistics |
| Export Recall | `scripts/export_recall.py` | Export recall packs for context |
| Archive Inbox | `scripts/archive_inbox.py` | Archive processed inbox items |
| Memory Sync | `scripts/memory-sync.js` | Heartbeat sync wrapper (Node.js) |

### Enhanced Components (Optional)

| Component | Path | Description |
|-----------|------|-------------|
| Embedding Client | `scripts/embedding_client.py` | BGE-M3 embedding integration |
| Semantic Utils | `scripts/semantic_utils.py` | Semantic similarity and clustering |

## Installation

### Quick Install (Full Pro)

```bash
# 1. Copy entire repository to workspace
cp -r mnemosyne-pro/ ~/.openclaw/workspace/

# 2. Initialize runtime
python ~/.openclaw/workspace/scripts/init_runtime.py ~/.openclaw/workspace

# 3. Add to HEARTBEAT.md (optional, for auto-sync)
# Run `node scripts/memory-sync.js` to sync daily session stats
```

### Manual Install (Script by Script)

1. Copy required scripts to `scripts/`
2. Copy `.mnemosyne/config.jsonc` to workspace `.mnemosyne/`
3. Run `python scripts/init_runtime.py <workspace> --create-memory-md`

## Core Workflow

```
                    ┌─────────────────┐
                    │  HEARTBEAT      │
                    │  (external)     │
                    └────────┬────────┘
                             │ triggers
                             ▼
              ┌──────────────────────────┐
              │ memory-sync.js (Node.js) │
              │ - reads sessions.json    │
              │ - writes inbox/*.md      │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ stage_intake.py          │
              │ - processes inbox files  │
              │ - creates staged cand.   │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ reconcile.py             │
              │ - detects conflicts      │
              │ - generates proposals    │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ publish.py               │
              │ - writes to memory/      │
              │ - updates registry       │
              └────────────┬─────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
    ┌──────────────────┐     ┌──────────────────┐
    │ export_recall.py │     │ archive_inbox.py │
    │ (query memory)   │     │ (cleanup)        │
    └──────────────────┘     └──────────────────┘
```

## Runtime Structure

```
workspace/
├── .mnemosyne/
│   ├── config.jsonc              # Main config
│   ├── inbox/
│   │   ├── feishu/               # Channel inputs
│   │   ├── tasks/
│   │   └── feedback/
│   ├── cache/
│   │   ├── staged-candidates.json
│   │   ├── reconciled-proposals.json
│   │   └── embeddings/           # Semantic cache
│   ├── review/
│   │   ├── proposed-memory-update.md
│   │   └── conflict-report.md
│   ├── state/
│   │   ├── intake-state.json
│   │   └── publish-registry.json
│   ├── archive/                  # Processed items
│   └── audit/
├── memory/                       # Durable memory
│   ├── global/
│   │   └── preferences.md        # Global preferences
│   ├── agents/
│   ├── projects/
│   └── channels/
└── scripts/
    ├── init_runtime.py           # Core: init
    ├── stage_intake.py           # Core: intake
    ├── reconcile.py              # Core: reconcile
    ├── publish.py                # Core: publish
    ├── report_status.py          # Core: report
    ├── export_recall.py          # Core: recall
    ├── archive_inbox.py          # Core: archive
    ├── memory-sync.js            # Sync wrapper
    ├── embedding_client.py       # Enhanced: embedding
    └── semantic_utils.py         # Enhanced: semantic
```

## Commands

```bash
# Initialize (first time)
python scripts/init_runtime.py <workspace> --create-memory-md

# Process daily sync (after heartbeat)
node scripts/memory-sync.js

# Manual workflow
python scripts/stage_intake.py <workspace>          # Process inbox
python scripts/reconcile.py <workspace>             # Resolve conflicts
python scripts/publish.py <workspace>               # Write memory
python scripts/report_status.py <workspace>         # Show status
python scripts/export_recall.py <workspace> --query "..."
python scripts/archive_inbox.py <workspace>         # Cleanup
```

## Configuration

See `.mnemosyne/config.jsonc` or `assets/mnemosyne.config.jsonc` for:
- Scope and promotion rules
- Intake sources (feishu, tasks, feedback)
- Publish targets
- Semantic enhancement options

## Version History

- **1.3** (current): Semantic recall, deduplication, clustering + full Core chain
- **1.1**: Initial release with heartbeat sync

## Files

```
mnemosyne-pro/
├── scripts/                     # Core + Enhanced scripts
│   ├── init_runtime.py
│   ├── stage_intake.py
│   ├── reconcile.py
│   ├── publish.py
│   ├── report_status.py
│   ├── export_recall.py
│   ├── archive_inbox.py
│   ├── memory-sync.js
│   ├── embedding_client.py
│   ├── semantic_utils.py
│   └── common.py
├── assets/
│   └── mnemosyne.config.jsonc  # Config template
├── .mnemosyne/
│   └── config.jsonc            # Runtime config
├── memory-sync/                # (legacy, removed)
├── SKILL.md                    # This file
├── README.md                   # Full documentation
├── VERSION                     # 1.3
└── LICENSE                     # MIT
```