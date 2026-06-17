# Multimodal Extension Workspace

Write all geometry or multimodal extension outputs here.

## Current Mainline Task

The current mainline task for the 3DGraphLLM+ project is:

```text
../INTERN_3DGRAPHLLM_EXPORT_TASK_PLAN.md
```

That task builds the clean model-facing export under:

```text
../exports/3dgraphllm_functional_eval_v1/
```

This `multimodal_extension/` directory is now a sidecar workspace. The geometry
and perception files here remain useful inputs, but they are not the primary
entry point for native 3DGraphLLM evaluation.

The perception task plan remains valid only for P0 availability/remap/QC and
small pilots:

```text
../INTERN_PERCEPTION_TASK_PLAN_v2.md
```

Do not edit the frozen benchmark files in:

```text
../queries/
../graphs/
../geometry/
../annotations/
```

## Legacy Geometry Deliverables

```text
geometry_coverage_report.csv
target_anchor_geometry_coverage.csv
coverage_summary.json
node_geometry_features.csv
node_geometry_features.pt
feature_index.json
geometry_feature_readme.md
geometry_sanity_examples.html
manual_check_report.csv
ablation_results.csv
```

## Legacy Geometry Task

Audit geometry coverage using:

```text
../queries/scenefun3d_funrag_benchmark_enriched.json
../geometry/scenefun3d_node_geom.json
```

Report coverage for:

```text
target nodes
anchor nodes
supporting-edge endpoints
functional queries
same-label distractor cases
```

## Perception Sidecar Task

Follow `../INTERN_PERCEPTION_TASK_PLAN_v2.md` only after confirming it does not
block the 3DGraphLLM export. The required first step is the raw modality
availability audit:

```text
perception/p0_raw_modality_availability.csv
perception/p0_availability_summary.md
```

Do not start crop generation, point-cloud export, DINOv2, CLIP, Uni3D, or
3DGraphLLM preprocessing until P0 has been reviewed by Mingqian. Native
3DGraphLLM evaluation should use `../exports/3dgraphllm_functional_eval_v1/`.

