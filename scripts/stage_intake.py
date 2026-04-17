#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import choose_scope, dump_json, guess_type, hash_text, load_config, load_json, logical_key, now_iso, parse_frontmatter


def allowed_source(config: dict, source_type: str) -> bool:
    intake = config.get('intake', {})
    return {
        'feishu': intake.get('feishu_enabled', True),
        'tasks': intake.get('tasks_enabled', True),
        'feedback': intake.get('feedback_enabled', True),
    }.get(source_type, True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace')
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    sidecar = workspace / '.mnemosyne'
    inbox_root = sidecar / 'inbox'
    cache_path = sidecar / 'state' / 'intake-state.json'
    out_path = sidecar / 'cache' / 'staged-candidates.json'

    config = load_config(workspace)
    state = load_json(cache_path, {'files': {}})
    staged = []
    changed = 0

    for file_path in sorted(inbox_root.rglob('*.md')):
        source_type = file_path.parent.name
        if not allowed_source(config, source_type):
            continue
        text = file_path.read_text(encoding='utf-8')
        content_hash = hash_text(text)
        rel = str(file_path.relative_to(workspace))
        if config.get('incremental', {}).get('use_hash', True) and state['files'].get(rel) == content_hash:
            continue
        meta, body = parse_frontmatter(text)
        if not body.strip():
            state['files'][rel] = content_hash
            continue
        scope_type, scope_key = choose_scope(meta)
        topic = (meta.get('topic') or body.splitlines()[0][:80] or source_type).strip()
        explicitness = meta.get('explicitness', 'explicit' if meta.get('remember', '').lower() == 'true' else 'implied').lower()
        confidence = meta.get('confidence', 'medium').lower()
        remember = meta.get('remember', 'false').lower() == 'true'
        promote_global = meta.get('promote_global', 'false').lower() == 'true'
        record_type = meta.get('record_type') or guess_type(body, source_type)
        if meta.get('record_type') is None and remember and record_type == 'fact':
            record_type = 'preference' if source_type in {'feedback', 'feishu'} else 'rule'
        created_at = meta.get('created_at') or now_iso()
        staged.append({
            'id': hash_text(rel + content_hash),
            'logical_key': logical_key(scope_type, scope_key, record_type, topic),
            'source_type': meta.get('source', source_type),
            'scope_type': scope_type,
            'scope_key': scope_key,
            'record_type': record_type,
            'topic': topic,
            'statement': body.strip(),
            'confidence': confidence if confidence in {'low', 'medium', 'high'} else 'medium',
            'explicitness': explicitness if explicitness in {'explicit', 'implied'} else 'implied',
            'remember': remember,
            'promote_global': promote_global,
            'created_at': created_at,
            'last_seen_at': now_iso(),
            'status': 'proposed',
            'evidence_files': [rel],
        })
        state['files'][rel] = content_hash
        changed += 1

    dump_json(out_path, staged)
    dump_json(cache_path, state)
    print(f'Staged {len(staged)} candidate(s) from {changed} changed inbox file(s) -> {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
