# 3DGraphLLM Functional Eval Export v1

This export is the clean interface between FunGraph / SceneFun3D functional
queries and native 3DGraphLLM evaluation.

It is an adapter layer, not a new benchmark source of truth. Rebuild it with:

```bash
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_export.py
/home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_native_3dgraphllm_packet.py
/home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_real_scene3d_modalities.py
/home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/audit_native_3dgraphllm_assets.py --graphllm-root "/home/mz560/3D scene graph project/3DGraphLLM"
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
| `native_3dgraphllm/` | 3DGraphLLM `ValDataset`-readable packet for loader/model smoke tests |
| `native_3dgraphllm_asset_manifest.csv` | Scene-level native feature alignment audit |
| `asset_alignment_report.md` | Human-readable report on real native features vs fallback packet |
| `native_3dgraphllm_asset_schema.json` | Torch feature schema snapshot for adapter debugging |
| `object_modality_manifest.csv` | Object-level point/color/camera coverage and feature keys |
| `scene_rgbd_manifest.csv` | Scene-level RGB/depth/frame/trajectory coverage |
| `SMOKE_TEST.md` | Completed one-query full-model smoke test command and result |
| `FULL_EVAL_20260618.md` | Full 500-query original 3DGraphLLM run note and FunGraph metrics |
| `scripts/evaluate_fungraph_predictions.py` | FunGraph functional evaluator for 3DGraphLLM `preds_*.json` files |

## Current Policy

- `functional_500_eval.jsonl` is selected deterministically from SceneFun3D
  functional test queries sorted by `query_id`, first 500 rows.
- Human 133, minimal pairs, and long-range stress queries are evaluation-only by
  default. Do not train or tune thresholds on them.
- This export does not modify native 3DGraphLLM. It adapts benchmark format,
  candidate sets, answer keys, slice metadata, and a loader-ready native packet.
- `native_3dgraphllm/` now contains nonzero real SceneFun3D modality adapter
  features: point/color object features from PLY+indices, RGB-D/camera features
  from frame coverage and annotation camera metadata, and relative-geometry GNN
  features.
- These are not pretrained Uni3D/video-network embeddings. Gate 1 scientific
  reporting must use `asset_alignment_report.md` and describe them as
  SceneFun3D adapter features unless encoder-specific Uni3D/video features are
  regenerated later.

## Validation Invariants

`validate_export.py` checks that:

- all query ids are unique inside each export file;
- every target node appears in that scene's candidate list;
- every answer key references an exported query;
- every exported query has a scene, target, source, and difficulty tags;
- the frozen generated eval has exactly 500 rows;
- human/minimal-pair/long-range counts match the expected local files.

## Native 3DGraphLLM Smoke Test

After copying or keeping this export accessible from the 3DGraphLLM machine, run
from the 3DGraphLLM repository root:

```bash
PYTHONPATH=. CUDA_VISIBLE_DEVICES=7 python tasks/train.py /home/mz560/fungraph_benchmark_v0/benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/native_3dgraphllm/config_fungraph_eval.py \
  evaluate True \
  pretrained_path ./demo/3dgraphllm.pth \
  val_tag fungraph_smoke_1 \
  output_dir /home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1
```

This has been run successfully on 2026-06-18 with both the original fallback
packet and the real SceneFun3D modality adapter packet; see `SMOKE_TEST.md`.
Treat the predictions as integration outputs, not final benchmark evidence,
until Dennis/Mingqian approve the adapter-feature protocol or replace these
features with encoder-specific Uni3D/video embeddings.

## FunGraph Metrics

3DGraphLLM's native `scores_*.json` is a language-generation score, not the
functional localization metric. After each run, evaluate the predictions with:

```bash
/home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python \
  benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/evaluate_fungraph_predictions.py \
  --preds /home/mz560/3dgraphllm_plus_data/eval_out/<run_dir>/preds_<tag>.json
```

The primary metric requires an explicit `<OBJxxx>` token matching the target
object id. Free-text label overlap is written as a diagnostic only and is not
counted as accuracy.
