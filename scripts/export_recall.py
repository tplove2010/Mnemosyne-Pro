#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from common import load_config, load_json, now_iso


def tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9_\-]+", text.lower()) if len(t) > 1}


def extract_blocks(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding='utf-8')
    pattern = re.compile(r'(<!-- mnemosyne:key:[^\n]+-->.*?)(?=\n<!-- mnemosyne:key:|\Z)', re.DOTALL)
    blocks = []
    for raw in pattern.findall(text):
        key_match = re.search(r'<!-- mnemosyne:key:([^ ]+) ', raw)
        title_match = re.search(r'^##\s+(.+)$', raw, re.MULTILINE)
        updated_match = re.search(r'^- updated_at:\s+(.+)$', raw, re.MULTILINE)
        topic = title_match.group(1) if title_match else 'untitled'
        blocks.append({
            'logical_key': key_match.group(1) if key_match else '',
            'topic': topic,
            'updated_at': updated_match.group(1) if updated_match else '',
            'text': raw.strip(),
            'path': str(path),
        })
    return blocks


def score_block(block: dict, query_tokens: set[str]) -> tuple[int, str]:
    hay = tokenize(block['topic'] + '\n' + block['text'])
    overlap = len(query_tokens & hay)
    reason = f'overlap={overlap}' if query_tokens else 'recent durable item'
    return overlap, reason


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace')
    parser.add_argument('--query', default='')
    parser.add_argument('--limit', type=int, default=None)
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    config = load_config(workspace)
    recall_cfg = config.get('recall_export', {})
    limit = args.limit or int(recall_cfg.get('default_limit', 8))
    registry = load_json(workspace / '.mnemosyne' / 'state' / 'publish-registry.json', {'keys': {}})

    targets = defaultdict(list)
    for key, meta in registry.get('keys', {}).items():
        target = workspace / meta['target']
        targets[target].append(key)

    blocks = []
    for target in targets:
        blocks.extend(extract_blocks(target))

    query_tokens = tokenize(args.query)
    scored = []
    for block in blocks:
        score, reason = score_block(block, query_tokens)
        if query_tokens and score == 0:
            continue
        scored.append((score, block.get('updated_at', ''), reason, block))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    chosen = scored[:limit]

    review_dir = workspace / '.mnemosyne' / 'review'
    cache_dir = workspace / '.mnemosyne' / 'cache'
    review_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        'generated_at': now_iso(),
        'query': args.query,
        'items': [
            {
                'logical_key': item[3]['logical_key'],
                'topic': item[3]['topic'],
                'target_path': str(Path(item[3]['path']).relative_to(workspace)),
                'updated_at': item[3]['updated_at'],
                'reason': item[2],
                'score': item[0],
                'text': item[3]['text'],
            }
            for item in chosen
        ],
    }
    if recall_cfg.get('write_json', True):
        from common import dump_json
        dump_json(cache_dir / 'recall-pack.json', payload)
    if recall_cfg.get('write_markdown', True):
        lines = ['# Recall pack', '', f"Generated: {payload['generated_at']}", f"Query: {args.query or '(none)'}", '']
        if not payload['items']:
            lines += ['No matching durable items.', '']
        for item in payload['items']:
            lines += [
                f"## {item['topic']}",
                f"- target: {item['target_path']}",
                f"- updated_at: {item['updated_at']}",
                f"- reason: {item['reason']}",
                '',
                item['text'],
                '',
            ]
        (review_dir / 'recall-pack.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f"Recall items: {len(payload['items'])}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
