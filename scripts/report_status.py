#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import detect_environment, load_json, now_iso


def count_md(path: Path) -> int:
    return sum(1 for _ in path.rglob('*.md')) if path.exists() else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace')
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    sidecar = workspace / '.mnemosyne'
    env = detect_environment(workspace)
    staged = load_json(sidecar / 'cache' / 'staged-candidates.json', [])
    proposals = load_json(sidecar / 'cache' / 'reconciled-proposals.json', [])
    conflicts = load_json(sidecar / 'cache' / 'conflicts.json', [])
    registry = load_json(sidecar / 'state' / 'publish-registry.json', {'keys': {}})
    recall_pack = sidecar / 'review' / 'recall-pack.md'
    archive_dir = sidecar / 'archive'

    missing = []
    for rel in [
        '.mnemosyne/config.jsonc',
        '.mnemosyne/inbox/feishu',
        '.mnemosyne/inbox/tasks',
        '.mnemosyne/inbox/feedback',
        '.mnemosyne/review',
        '.mnemosyne/audit',
        '.mnemosyne/cache',
        '.mnemosyne/state',
    ]:
        if not (workspace / rel).exists():
            missing.append(rel)

    lines = [
        '# Runtime status',
        '',
        f'Generated: {now_iso()}',
        f"Workspace: {workspace}",
        f"Environment class: {env['class']}",
        '',
        '## Counts',
        f"- native memory markdown files: {count_md(workspace / 'memory') + (1 if (workspace / 'MEMORY.md').exists() else 0)}",
        f"- sidecar markdown files: {count_md(sidecar)}",
        f"- staged candidates: {len(staged)}",
        f"- reconciled proposals: {len(proposals)}",
        f"- conflicts: {len(conflicts)}",
        f"- published keys: {len(registry.get('keys', {}))}",
        f"- archived files: {sum(1 for _ in archive_dir.rglob('*') if _.is_file()) if archive_dir.exists() else 0}",
        '',
        '## Missing paths',
    ]
    lines += [f'- {rel}' for rel in missing] or ['- none']
    lines += ['', '## Last artifacts']
    for rel in [
        '.mnemosyne/review/mnemosyne-install-report.md',
        '.mnemosyne/review/proposed-memory-update.md',
        '.mnemosyne/review/conflict-report.md',
        '.mnemosyne/review/recall-pack.md',
    ]:
        lines.append(f"- {rel}: {'present' if (workspace / rel).exists() else 'missing'}")

    report = sidecar / 'audit' / 'runtime-status.md'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
