# Perception Extension Workspace

The old intern perception task plan has been removed. This directory now keeps
only the legacy P0 raw-modality availability audit.

The current relation-conditioned perceptual evidence lives in:

```text
../../exports/3dgraphllm_functional_eval_v1/relation_conditioned_evidence/
```

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

This P0 report is retained for provenance. It has been superseded by the full
raw-modality manifests and official crop/QC metadata in the 3DGraphLLM export.

## Relationship to 3DGraphLLM Export

Native 3DGraphLLM functional evaluation should use:

```text
../../exports/3dgraphllm_functional_eval_v1/
```

Do not block native 3DGraphLLM reproduction or Gate 1 on full perception asset
completion.

## Rule

Do not add new outputs here. Use the 3DGraphLLM export relation-conditioned
evidence directory for current multimodal benchmark work.
