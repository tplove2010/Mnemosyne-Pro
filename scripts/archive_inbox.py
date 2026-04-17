#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import load_config, load_json, now_iso


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    config = load_config(workspace)
    archive_cfg = config.get('archive', {})
    sidecar = workspace / '.mnemosyne'
    proposals = load_json(sidecar / 'cache' / 'reconciled-proposals.json', [])
    registry = load_json(sidecar / 'state' / 'publish-registry.json', {'keys': {}})
    published_keys = set(registry.get('keys', {}).keys())

    if not archive_cfg.get('enabled', False) and args.apply:
        print('Archive is disabled in config. Refusing apply.')
        return 1

    evidence = []
    for proposal in proposals:
        if proposal.get('logical_key') not in published_keys:
            continue
        for rel in proposal.get('evidence_files', []):
            src = workspace / rel
            if src.exists() and src.is_file():
                evidence.append(src)

    seen = set()
    ops = []
    ts = now_iso().replace(':', '').replace('+', '_')
    for src in evidence:
        if src in seen:
            continue
        seen.add(src)
        rel = src.relative_to(sidecar / 'inbox') if (sidecar / 'inbox') in src.parents else src.name
        dst = sidecar / 'archive' / rel
        if archive_cfg.get('preserve_source_tree', True):
            dst = dst.with_suffix(dst.suffix + f'.published.{ts}')
        else:
            dst = sidecar / 'archive' / f"{src.name}.published.{ts}"
        ops.append((src, dst))

    if not args.apply:
        print('Dry run archive operations:')
        for src, dst in ops:
            print(f'- {src.relative_to(workspace)} -> {dst.relative_to(workspace)}')
        print(f'Total: {len(ops)}')
        return 0

    for src, dst in ops:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    audit = sidecar / 'audit' / f"archive-log-{ts}.md"
    audit.write_text('# Archive log\n\n' + '\n'.join(f'- {s.relative_to(workspace)} -> {d.relative_to(workspace)}' for s, d in ops) + '\n', encoding='utf-8')
    print(f'Archived {len(ops)} file(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
