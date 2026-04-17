#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import dump_json, load_config, load_json, marker_for_key, now_iso


def target_path(workspace: Path, config: dict, proposal: dict) -> Path:
    memory_root = workspace / 'memory'
    scope_type = proposal['target_scope_type']
    scope_key = proposal['target_scope_key']
    if scope_type == 'global':
        target = workspace / config.get('publish', {}).get('global_target', 'memory/global/preferences.md')
        return target if target.is_absolute() else workspace / target
    if scope_type == 'agent':
        return memory_root / 'agents' / scope_key / 'memory.md'
    if scope_type == 'project':
        return memory_root / 'projects' / scope_key / 'memory.md'
    if scope_type == 'channel':
        return memory_root / 'channels' / scope_key / 'memory.md'
    fallback = config.get('publish', {}).get('fallback_global_target', 'MEMORY.md')
    return workspace / fallback


def block_for(proposal: dict) -> str:
    marker = marker_for_key(proposal['logical_key'])
    lines = [
        marker,
        f"## {proposal['record_type']} · {proposal['topic']}",
        '',
        '- status: active',
        f"- confidence: {proposal['confidence']}",
        f"- explicitness: {proposal['explicitness']}",
        f"- repeat_count: {proposal.get('repeat_count', 1)}",
        f"- updated_at: {now_iso()}",
        f"- evidence_files: {', '.join(proposal.get('evidence_files', []))}",
    ]
    if proposal.get('supersedes'):
        lines.append(f"- supersedes: {', '.join(proposal['supersedes'])}")
    lines += ['', proposal['statement'].strip(), '']
    return '\n'.join(lines)


def upsert_block(path: Path, logical_key: str, block: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = marker_for_key(logical_key)
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    if not text:
        title = f"# {path.stem.replace('-', ' ').title()}\n\n"
        path.write_text(title + block + '\n', encoding='utf-8')
        return 'created'
    escaped = re.escape(marker)
    pattern = re.compile(rf'{escaped}.*?(?=\n<!-- mnemosyne:key:|\Z)', re.DOTALL)
    if pattern.search(text):
        new_text = pattern.sub(block + '\n', text, count=1)
        path.write_text(new_text, encoding='utf-8')
        return 'updated'
    if not text.endswith('\n'):
        text += '\n'
    path.write_text(text + '\n' + block + '\n', encoding='utf-8')
    return 'appended'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    config = load_config(workspace)
    sidecar = workspace / '.mnemosyne'
    proposals = load_json(sidecar / 'cache' / 'reconciled-proposals.json', [])
    if not proposals:
        print('No reconciled proposals. Run reconcile.py first.')
        return 1
    if config.get('review_mode', True) and not args.apply:
        print('Review mode enabled. No publish performed. Use --apply after approval.')
        return 0

    registry_path = sidecar / 'state' / 'publish-registry.json'
    registry = load_json(registry_path, {'keys': {}})
    published = []
    for proposal in proposals:
        target = target_path(workspace, config, proposal)
        outcome = upsert_block(target, proposal['logical_key'], block_for(proposal))
        registry['keys'][proposal['logical_key']] = {
            'target': str(target.relative_to(workspace)),
            'updated_at': now_iso(),
            'outcome': outcome,
        }
        published.append(f"{proposal['logical_key']} -> {target.relative_to(workspace)} ({outcome})")

    dump_json(registry_path, registry)
    audit = sidecar / 'audit' / f"publish-log-{now_iso().replace(':', '').replace('+', '_')}.md"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text('# Publish log\n\n' + '\n'.join(f'- {item}' for item in published) + '\n', encoding='utf-8')
    print(f'Published {len(published)} proposal(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
