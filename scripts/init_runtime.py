#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import detect_environment, ensure_text

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / 'assets' / 'mnemosyne.config.jsonc'
SIDE_DIRS = [
    '.mnemosyne',
    '.mnemosyne/inbox',
    '.mnemosyne/inbox/feishu',
    '.mnemosyne/inbox/tasks',
    '.mnemosyne/inbox/feedback',
    '.mnemosyne/review',
    '.mnemosyne/audit',
    '.mnemosyne/cache',
    '.mnemosyne/state',
    '.mnemosyne/archive',
]
CURATED_DIRS = [
    'memory',
    'memory/global',
    'memory/agents',
    'memory/projects',
    'memory/channels',
]
STATE_FILES = {
    '.mnemosyne/state/intake-state.json': '{"files": {}}\n',
    '.mnemosyne/state/publish-registry.json': '{"keys": {}}\n',
}
REVIEW_STUBS = {
    '.mnemosyne/review/proposed-memory-update.md': '# Proposed memory update\n\n',
    '.mnemosyne/review/conflict-report.md': '# Conflict report\n\n',
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace')
    parser.add_argument('--create-memory-md', action='store_true')
    args = parser.parse_args()

    root = Path(args.workspace).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    env = detect_environment(root)

    for rel in SIDE_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)
    for rel in CURATED_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)
    ensure_text(root / '.mnemosyne' / 'config.jsonc', DEFAULT_CONFIG.read_text(encoding='utf-8'))
    for rel, content in STATE_FILES.items():
        ensure_text(root / rel, content)
    for rel, content in REVIEW_STUBS.items():
        ensure_text(root / rel, content)
    if args.create_memory_md:
        ensure_text(root / 'MEMORY.md', '# MEMORY\n\n## durable memory\n\n')

    audit = root / '.mnemosyne' / 'audit' / 'install-audit.md'
    audit.write_text(
        '\n'.join([
            '# Mnemosyne Pro Install Audit',
            '',
            f'Workspace: {root}',
            f"Detected environment class: {env['class']}",
            'Actions:',
            '- ensured sidecar runtime structure exists',
            '- ensured review, audit, cache, and state files exist',
            '- preserved existing native memory files',
            '- created scoped memory directories if missing',
            ('- created MEMORY.md because --create-memory-md was requested' if args.create_memory_md else '- left MEMORY.md unchanged unless it already existed'),
        ]) + '\n',
        encoding='utf-8',
    )
    print(f'Initialized Mnemosyne Pro runtime at: {root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
