# 3DGraphLLM Functional Eval Export v1

This export is the clean interface between FunGraph / SceneFun3D functional
queries and native 3DGraphLLM evaluation.

It is an adapter layer, not a new benchmark source of truth. Rebuild it with:

```bash
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_export.py
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/validate_export.py
```

## Files

| File | Purpose |
|---|---|
| `functional_500_eval.jsonl` | Frozen 500-query generated functional eval set for Gate 1 |
| `human_133_eval.jsonl` | Human-authored hard functional eval set; hold out from training |
| `minimal_pairs_28_eval.jsonl` | Pairwise consistency / anchor-sensitivity eval |
| `long_range_50_eval.jsonl` | Long-range stress eval |
| `answer_key.json` | `query_id -> target_node_ids` |
| `candidate_objects.jsonl` | Candidate node ids per scene |
| `node_id_mapping.json` | Node id mapping and geometry feature row pointers |
| `scene_asset_manifest.csv` | Scene-level asset pointers for 3DGraphLLM adapter |
| `slice_metadata.json` | Counts and slice definitions for reporting |
| `export_summary.json` | Build metadata and high-level counts |
| `DATASET_AUDIT.md` | Cleanup/audit notes and current decisions |

## Current Policy

- `functional_500_eval.jsonl` is selected deterministically from SceneFun3D
  functional test queries sorted by `query_id`, first 500 rows.
- Human 133, minimal pairs, and long-range stress queries are evaluation-only by
  default. Do not train or tune thresholds on them.
- This export does not modify native 3DGraphLLM. It only adapts benchmark format,
  candidate sets, answer keys, and slice metadata.
- Perception assets are optional sidecars. Native Gate 1 should not wait for a
  full RGB-D perception benchmark.

## Validation Invariants

`validate_export.py` checks that:

- all query ids are unique inside each export file;
- every target node appears in that scene's candidate list;
- every answer key references an exported query;
- every exported query has a scene, target, source, and difficulty tags;
- the frozen generated eval has exactly 500 rows;
- human/minimal-pair/long-range counts match the expected local files.
