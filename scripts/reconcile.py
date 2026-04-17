#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from common import CONFIDENCE_RANK, EXPLICITNESS_RANK, dump_json, load_config, load_json, now_iso


def parse_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.min


def winner(items: list[dict]) -> dict:
    explicit_items = [i for i in items if i.get('explicitness') == 'explicit']
    pool = explicit_items or items
    if explicit_items:
        return sorted(pool, key=lambda x: (parse_dt(x['created_at']), CONFIDENCE_RANK.get(x.get('confidence', 'medium'), 2), x.get('repeat_count', 1)))[-1]
    return sorted(pool, key=lambda x: (x.get('repeat_count', 1), CONFIDENCE_RANK.get(x.get('confidence', 'medium'), 2), parse_dt(x['created_at'])))[-1]


def should_promote_global(item: dict, config: dict) -> bool:
    gp = config.get('global_promotion', {})
    if not gp.get('enabled', True):
        return False
    if item.get('scope_type') == 'global':
        return True
    if item.get('promote_global'):
        return True
    if gp.get('require_explicit', True) and item.get('explicitness') != 'explicit':
        return False
    return int(item.get('repeat_count', 1)) >= int(gp.get('min_repeat_count', 2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace')
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    sidecar = workspace / '.mnemosyne'
    staged_path = sidecar / 'cache' / 'staged-candidates.json'
    if not staged_path.exists():
        print('No staged candidates. Run stage_intake.py first.')
        return 1
    staged = load_json(staged_path, [])
    config = load_config(workspace)

    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for item in staged:
        grouped[(item['scope_type'], item['scope_key'], item['record_type'], item['topic'].lower())].append(item)

    proposals: list[dict] = []
    conflicts: list[dict] = []

    for _, items in grouped.items():
        statement_groups: dict[str, list[dict]] = defaultdict(list)
        for item in items:
            statement_groups[item['statement'].strip()].append(item)

        merged_items = []
        for _, dupes in statement_groups.items():
            base = sorted(dupes, key=lambda x: parse_dt(x['created_at']))[-1].copy()
            base['repeat_count'] = len(dupes)
            base['source_count'] = len({d['source_type'] for d in dupes})
            base['evidence_files'] = sorted({e for d in dupes for e in d['evidence_files']})
            merged_items.append(base)

        chosen = winner(merged_items).copy()
        chosen['supersedes'] = [i['id'] for i in merged_items if i['id'] != chosen['id']]
        chosen['reason'] = 'merged repeated evidence' if len(merged_items) == 1 else 'selected best durable candidate after conflict checks'
        chosen['target_scope_type'] = chosen['scope_type']
        chosen['target_scope_key'] = chosen['scope_key']

        if config.get('sharing_mode', 'scoped') == 'global' and should_promote_global(chosen, config):
            chosen['target_scope_type'] = 'global'
            chosen['target_scope_key'] = 'global'
            if chosen['scope_type'] != 'global':
                chosen['reason'] += '; promoted to global by policy'

        if len(merged_items) > 1:
            conflicts.append({
                'scope_type': chosen['scope_type'],
                'scope_key': chosen['scope_key'],
                'record_type': chosen['record_type'],
                'topic': chosen['topic'],
                'items': merged_items,
                'recommended': 'review winner and superseded statements before publish',
            })
        proposals.append(chosen)

    dump_json(sidecar / 'cache' / 'reconciled-proposals.json', proposals)
    dump_json(sidecar / 'cache' / 'conflicts.json', conflicts)

    review_dir = sidecar / 'review'
    review_dir.mkdir(parents=True, exist_ok=True)
    proposed_md = review_dir / 'proposed-memory-update.md'
    conflict_md = review_dir / 'conflict-report.md'

    lines = [f'# Proposed memory update\n\nGenerated: {now_iso()}\n']
    for p in proposals:
        target = f"{p['target_scope_type']}:{p['target_scope_key']}"
        lines += [
            f"## {p['record_type']} · {p['topic']}",
            f"- target: {target}",
            f"- confidence: {p['confidence']}",
            f"- explicitness: {p['explicitness']}",
            f"- repeat_count: {p.get('repeat_count', 1)}",
            f"- evidence: {', '.join(p['evidence_files'])}",
            f"- reason: {p['reason']}",
            '',
            p['statement'],
            '',
        ]
    proposed_md.write_text('\n'.join(lines), encoding='utf-8')

    c_lines = [f'# Conflict report\n\nGenerated: {now_iso()}\n']
    if conflicts:
        for c in conflicts:
            c_lines += [
                f"## {c['record_type']} · {c['topic']}",
                f"- scope: {c['scope_type']}:{c['scope_key']}",
                f"- recommended: {c['recommended']}",
            ]
            for item in c['items']:
                c_lines += [f"  - [{item['created_at']}] {item['explicitness']} / {item['confidence']} / repeat={item.get('repeat_count', 1)} :: {item['statement'][:160]}"]
            c_lines += ['']
    else:
        c_lines += ['No unresolved conflicts.', '']
    conflict_md.write_text('\n'.join(c_lines), encoding='utf-8')

    print(f'Proposals: {len(proposals)} | Conflicts: {len(conflicts)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
