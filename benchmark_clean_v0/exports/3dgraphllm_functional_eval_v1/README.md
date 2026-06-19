# 3DGraphLLM Functional Eval Export v1

This export is the clean interface between FunGraph / SceneFun3D functional
queries and native 3DGraphLLM evaluation.

It is an adapter layer, not a new benchmark source of truth. Rebuild it with:

```bash
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_export.py
/home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_native_3dgraphllm_packet.py
/home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_real_scene3d_modalities.py
/home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_full_multimodal_index.py
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_relation_conditioned_evidence.py
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_projection_dryrun.py
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_full_frame_crop_qc.py --write-local-crops
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_full_perception_evidence.py --write-images
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_expansion_v1.py --pair-cap 200
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_freeze_candidates_v1.py
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_expansion_perception_evidence_v1.py --write-images
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_ai_prereview_v1.py
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_funthor_style_quality_layer.py
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
| `BENCHMARK_CLAIM_AUDIT.md` | Claim guardrail for what the current and expansion benchmark can/cannot support |
| `native_3dgraphllm/` | 3DGraphLLM `ValDataset`-readable packet for loader/model smoke tests |
| `native_3dgraphllm_asset_manifest.csv` | Scene-level native feature alignment audit |
| `asset_alignment_report.md` | Human-readable report on real native features vs fallback packet |
| `native_3dgraphllm_asset_schema.json` | Torch feature schema snapshot for adapter debugging |
| `object_modality_manifest.csv` | Object-level point/color/camera coverage and feature keys |
| `scene_rgbd_manifest.csv` | Scene-level RGB/depth/frame/trajectory coverage |
| `full_scene_capture_manifest.csv` | Capture-level RGB/depth/intrinsics/trajectory/laser-scan readiness |
| `full_scene_frame_index.jsonl` | Frame-level RGB/depth/intrinsics path index for all exported scenes |
| `full_object_modality_manifest.csv` | Object-level full-modality readiness for every exported candidate object |
| `full_multimodal_readiness.json` | Machine-readable full benchmark readiness summary |
| `FULL_MULTIMODAL_BENCHMARK_STATUS.md` | Human-readable full multimodal benchmark status |
| `relation_conditioned_evidence/` | Query-level target-anchor multimodal evidence manifests keyed by `relation_key` |
| `expansion_v1/` | Clean expansion workspace: manifest, final candidates, AI pre-review views, expansion evidence cards, and Dennis signoff packet; process drafts are regenerated under ignored `_intermediate/` |
| `benchmark_quality_v2/` | FunTHOR-style full-modality and relation-taxonomy quality layer: RGB-D-camera/pointcloud readiness, query relation categories, minimal-pair ambiguity tags, and remaining parity gaps |
| `SMOKE_TEST.md` | Completed one-query full-model smoke test command and result |
| `FULL_EVAL_20260618.md` | Full 500-query original 3DGraphLLM run note and FunGraph metrics |
| `OBJECT_SELECTION_EVAL_20260618.md` | Controlled object-selection 3DGraphLLM eval note and metrics |
| `scripts/evaluate_fungraph_predictions.py` | FunGraph functional evaluator for 3DGraphLLM `preds_*.json` files |
| `scripts/build_object_selection_splits.py` | Builds native prompt variants that ask for exactly one `<OBJxxx>` answer |
| `scripts/build_full_multimodal_index.py` | Builds full raw-modality indexes and readiness gates |
| `scripts/build_relation_conditioned_evidence.py` | Builds query-level target-anchor evidence manifests |
| `scripts/build_projection_dryrun.py` | Builds placeholder target/anchor projection metadata for candidate RGB-D frames |
| `scripts/build_full_frame_crop_qc.py` | Mines all scene RGB-D frames, applies depth z-test, and builds frozen crop metadata/QC |
| `scripts/build_full_perception_evidence.py` | Builds 683/683 full-coverage perception evidence cards with RGB-D crop when available and pointcloud-render fallback otherwise |
| `scripts/build_expansion_v1.py` | Builds expansion_v1 distribution audit, all-source unique-relation drafts, review queues, and auto-mined minimal-pair candidates |
| `scripts/build_freeze_candidates_v1.py` | Builds conservative paper-disabled freeze-candidate functional and minimal-pair splits from expansion_v1 |
| `scripts/build_expansion_perception_evidence_v1.py` | Builds pointcloud-render evidence cards for the expansion functional freeze candidates |
| `scripts/build_ai_prereview_v1.py` | Builds AI pre-review triage files and `DENNIS_BENCHMARK_SIGNOFF_PACKET.md` without enabling paper use |
| `scripts/build_funthor_style_quality_layer.py` | Builds the FunTHOR-style benchmark quality layer and relation/minimal-pair taxonomy indexes |
| `scripts/export_relation_point_segments.py` | Optional local exporter for target/anchor PLY point segments; outputs should not be committed |

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
- The export now has a full raw-multimodal benchmark index: each exported scene
  is linked to laser scan, RGB frames, depth frames, intrinsics, trajectory, and
  each exported candidate object is linked to point indices, geometry, camera
  metadata, and native feature keys.
- `relation_conditioned_evidence/` maps every functional query to a stable
  `relation_key = query_id|target_node_id|anchor_node_id`, target/anchor point
  sidecars, native feature keys, supporting edges, RGB-D-camera frame
  candidates, placeholder projection dry-run metadata, and frozen full-frame
  mined depth-tested crop metadata/QC artifacts.
- `relation_conditioned_evidence/full_perception_evidence_index.jsonl` is the
  current full-coverage perception layer: all 683 / 683 functional relations
  have one inspectable visual evidence card. Rows with real co-visible RGB-D
  evidence keep their strict `official_crop_*` crop metadata; rows without such
  views use a GT pointcloud-render fallback and must not be described as
  depth-tested camera crops.
- `benchmark_quality_v2/` is the FunTHOR-style quality layer. It makes explicit
  which scenes meet full raw RGB-D-camera-pointcloud readiness, which queries are
  part-object operations versus proximity-dependent relations, which minimal pairs
  require same-label or global one-to-one reasoning, and which semantic gaps remain
  relative to FunTHOR-style parity: first-class object-part hierarchy and explicit
  visible subset tables.
- `expansion_v1/` is a draft expansion layer, not a frozen eval split. It audits
  the current 683 rows, exposes the true 160 unique scene-target-anchor-relation
  units, covers all 195 unique OpenFunGraph source relations with 585
  template-generated query drafts, creates human-review queues, builds a
  116-query balanced candidate split with max 15 examples per exact relation,
  builds paper-disabled freeze-candidate splits, adds 116 / 116 expansion
  perception evidence cards, runs AI pre-review triage, prepares a Dennis
  signoff packet, and mines 105 minimal-pair candidates. The canonical tracked
  expansion files are consolidated under `expansion_manifest_v1.json`,
  `final_candidates/`, `ai_prereview_v1/`, and `perception_evidence/`;
  process drafts are regenerated under ignored `_intermediate/`. The generated
  query wording and pair candidates need human review before paper use.
- `native_3dgraphllm/` also includes object-selection prompt variants for
  `functional_500`, `human_133`, `long_range_50`, and a one-query smoke split.
  These preserve the original target objects and query ids while forcing a
  stricter `<OBJxxx>` answer protocol.
- These are not pretrained Uni3D/video-network embeddings. Gate 1 scientific
  reporting must use `asset_alignment_report.md` and describe them as
  SceneFun3D adapter features unless encoder-specific Uni3D/video features are
  regenerated later.
- `BENCHMARK_CLAIM_AUDIT.md` is the current claim guardrail. Paper text should
  follow its allowed/forbidden claim list until Dennis approves a new frozen
  split and claim update.

## Validation Invariants

`validate_export.py` checks that:

- all query ids are unique inside each export file;
- every target node appears in that scene's candidate list;
- every answer key references an exported query;
- every exported query has a scene, target, source, and difficulty tags;
- the frozen generated eval has exactly 500 rows;
- human/minimal-pair/long-range counts match the expected local files;
- the native 3DGraphLLM packet contains the base and object-selection eval
  annotation files;
- the full multimodal readiness summary exists and every exported scene/object
  passes the raw-modality readiness gate;
- the relation-conditioned evidence layer exists and covers every exported
  functional relation plus all minimal-pair links;
- the full perception evidence layer covers all 683 relations and records which
  rows have strict RGB-D crop evidence versus pointcloud-render fallback;
- the expansion draft exists, has 195 unique source relations, 585 template query
  drafts, 195 unique-relation review rows, 585 query-review rows, 105
  minimal-pair review rows, a 116-query balanced freeze-candidate split, 60
  expanded minimal-pair freeze candidates, 116 / 116 expansion evidence cards,
  AI pre-review counts, a Dennis signoff packet, and a benchmark claim audit;
- the FunTHOR-style quality layer exists, covers all 20 scenes, indexes 799
  functional/query rows and 88 minimal-pair rows, and records relation taxonomy,
  ambiguity, and remaining object-part/visible-subset parity gaps.

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

The original free-form `functional_500` run and controlled object-selection
variant are recorded in `FULL_EVAL_20260618.md` and
`OBJECT_SELECTION_EVAL_20260618.md`.
