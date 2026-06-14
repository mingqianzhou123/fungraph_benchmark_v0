# Multimodal Extension Workspace

Write all geometry or multimodal extension outputs here.

## Current Intern Task

The current intern task is:

```text
../INTERN_PERCEPTION_TASK_PLAN_v2.md
```

That task plan is authoritative for the next round of intern work. It starts a
new relation-conditioned perception extension under:

```text
perception/
```

The geometry deliverables below are legacy v1 sidecar outputs. They remain
useful inputs for Phase 1 stratification, but they are not the current first
task. The current first task is the P0 raw-modality availability audit.

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

## Current Perception Task

Follow `../INTERN_PERCEPTION_TASK_PLAN_v2.md`. The required first step is the
raw modality availability audit:

```text
perception/p0_raw_modality_availability.csv
perception/p0_availability_summary.md
```

Do not start crop generation, point-cloud export, DINOv2, CLIP, Uni3D, or
3DGraphLLM preprocessing until P0 has been reviewed by Mingqian.

