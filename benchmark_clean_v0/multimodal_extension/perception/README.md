# Perception Extension Workspace

Current task plan:

```text
../../INTERN_PERCEPTION_TASK_PLAN_v2.md
```

This directory is reserved for relation-conditioned perceptual evidence: target
part plus its query-specific anchor, not generic instance-level crops.

## Current Status

P0 raw-modality availability audit has been delivered here:

```text
p0_raw_modality_availability.csv
p0_availability_summary.md
```

Current P0 counts:

```text
image_projection_ready: 6 / 20 scenes
point_segment_ready: 6 / 20 scenes
bbox_only: 14 / 20 scenes
```

This is enough for a small perception pilot, but not enough to claim a complete
20-scene RGB-D perception benchmark.

## Relationship to 3DGraphLLM Export

Native 3DGraphLLM functional evaluation should use:

```text
../../exports/3dgraphllm_functional_eval_v1/
```

Do not block native 3DGraphLLM reproduction or Gate 1 on full perception asset
completion.

## Stop Rule

After P0, stop and sync with Mingqian before starting Phase 1. Do not write
large image crops or point-cloud assets to git; `crops/` and `pointclouds/` are
ignored here.
