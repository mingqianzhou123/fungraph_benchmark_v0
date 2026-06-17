# Intern Task Plan: 3DGraphLLM Functional Eval Export

## 0. Task Positioning

This task replaces ad-hoc benchmark edits for the current 3DGraphLLM+ project
stage.

The intern should not modify the frozen benchmark core and should not continue
adding unrelated files under old sidecar directories. The task is to maintain a
clean, reproducible export layer that lets Mingqian run native 3DGraphLLM and
later 3DGraphLLM+ on functional queries.

## 1. Working Directory

Write only under:

```text
benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/
```

Do not modify:

```text
benchmark_clean_v0/queries/
benchmark_clean_v0/graphs/
benchmark_clean_v0/geometry/
benchmark_clean_v0/annotations/
```

Perception availability files belong under:

```text
benchmark_clean_v0/multimodal_extension/perception/
```

## 2. Current Export

The export is rebuilt by:

```bash
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_export.py
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/validate_export.py
```

Current generated files:

```text
functional_500_eval.jsonl
human_133_eval.jsonl
minimal_pairs_28_eval.jsonl
long_range_50_eval.jsonl
answer_key.json
candidate_objects.jsonl
node_id_mapping.json
scene_asset_manifest.csv
slice_metadata.json
export_summary.json
```

## 3. Intern Priorities

### Priority 1: Validate 3DGraphLLM Readiness

Check that each exported query has:

```text
query_id
scene_id
query_text / prompt
target_node_ids
anchor_node_id
supporting_edge_ids
candidate_node_ids
difficulty_tags
```

Run `validate_export.py` after every change.

### Priority 2: Fill Native 3DGraphLLM Object Mapping

Once Mingqian confirms the reproduced 3DGraphLLM asset format, extend
`node_id_mapping.json` with:

```text
3dgraphllm_scene_id
3dgraphllm_object_id
3dgraphllm_object_label
mapping_status
```

Do not guess these ids. If a mapping is uncertain, mark:

```text
mapping_status = "needs_review"
```

### Priority 3: Maintain Hard Eval Sidecars

The following files are evaluation-only by default:

```text
human_133_eval.jsonl
minimal_pairs_28_eval.jsonl
long_range_50_eval.jsonl
```

Do not use them for training or threshold tuning unless Mingqian explicitly
changes the policy.

### Priority 4: Keep Perception As a Sidecar

Raw RGB-D/camera/pointcloud completion is useful but not a prerequisite for Gate
1. Continue only availability/remap/QC work unless Mingqian asks for a perception
pilot.

Current P0 status:

```text
image_projection_ready: 6 / 20 scenes
point_segment_ready: 6 / 20 scenes
bbox_only: 14 / 20 scenes
```

Do not start full crop generation, DINO/CLIP/Uni3D extraction, or point-cloud
feature extraction.

## 4. Success Criteria

This task is successful when:

```text
1. Native 3DGraphLLM can load functional_500_eval.jsonl.
2. Each prediction can be scored against answer_key.json.
3. Slice metrics can be reported using slice_metadata.json.
4. Every target node is present in candidate_objects.jsonl.
5. node_id_mapping.json clearly says which ids are aligned and which need review.
6. validate_export.py passes.
```

## 5. Reporting Format

At the end of each work session, append a short note to the export README or a
separate progress note with:

```text
Did:
Blocked:
Files changed:
Validation result:
Question for Mingqian:
```
