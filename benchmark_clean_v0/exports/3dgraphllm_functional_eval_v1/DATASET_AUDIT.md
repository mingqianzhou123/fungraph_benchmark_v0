# Dataset Audit for 3DGraphLLM Export v1

Date: 2026-06-18

## Why This Export Exists

The benchmark now has several historical sidecars: frozen functional queries,
geometry features, human hard queries, raw modality availability, and perception
planning. To keep the 3DGraphLLM reproduction clean, this export creates a
single model-facing interface.

## Source-of-Truth Policy

Do not edit frozen source files:

```text
queries/
graphs/
geometry/
annotations/
```

Use these as sources:

```text
queries/all_queries_index.jsonl
multimodal_extension/feature_index.json
multimodal_extension/node_geometry_features.csv
raw_assets/scenefun3d_raw_asset_manifest.csv
human_annotations/functional_queries_v1/*.jsonl
multimodal_extension/perception/p0_raw_modality_availability.csv
```

## Current Cleanup Decisions

- P0 raw modality files belong under `multimodal_extension/perception/`, matching
  `INTERN_PERCEPTION_TASK_PLAN_v2.md`.
- The current mainline benchmark task is native 3DGraphLLM functional evaluation,
  not full RGB-D perception benchmark construction.
- Full perception assets remain a sidecar/pilot until 20/20 scene availability
  and projection QC are complete.
- Human-authored queries are held out as hard evaluation by default.

## Known Limitations

- Candidate labels are not yet fully exported for every scene candidate. The
  current candidate list is node-id based using `feature_index.json`.
- `functional_500_eval.jsonl` uses a deterministic first-500 selection from the
  test split. This is frozen for Gate 1 unless Mingqian/Dennis choose a different
  sampling policy before running the confirmatory experiment.
- Native 3DGraphLLM object-id mapping is now generated in `node_id_mapping.json`
  by `scripts/build_native_3dgraphllm_packet.py` using stable native ids of the
  form `sf3d{scene_id}_00`.
- The generated native packet is loader/model smoke-test ready, but not
  full-modality ready: Uni3D, video, and GNN feature files are zero fallbacks
  until replaced by real SceneFun3D-native 3DGraphLLM features.
- Original downloaded 3DGraphLLM features are ScanNet keyed (`sceneXXXX_YY`) and
  do not directly cover SceneFun3D numeric scene ids. This is audited in
  `asset_alignment_report.md`.
