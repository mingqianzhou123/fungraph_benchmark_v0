#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
def read_jsonl(path: Path):
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--query-id')
    parser.add_argument('--relation-key')
    args = parser.parse_args()
    relations = {row['relation_key']: row for row in read_jsonl(ROOT / 'relation_evidence_index.jsonl')}
    qrels = {row['query_id']: row for row in read_jsonl(ROOT / 'query_relation_index.jsonl')}
    frames_by_relation = {}
    for row in read_jsonl(ROOT / 'relation_frame_candidates.jsonl'):
        frames_by_relation.setdefault(row['relation_key'], []).append(row)
    if args.relation_key:
        keys = [args.relation_key]
    elif args.query_id:
        keys = qrels.get(args.query_id, {}).get('relation_keys', [])
    else:
        raise SystemExit('Pass --query-id or --relation-key')
    out = []
    for key in keys:
        item = dict(relations[key])
        item['frame_candidates'] = frames_by_relation.get(key, [])
        out.append(item)
    print(json.dumps(out, indent=2, ensure_ascii=False))
if __name__ == '__main__':
    main()
