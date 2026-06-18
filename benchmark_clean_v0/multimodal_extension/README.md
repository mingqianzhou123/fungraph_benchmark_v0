# Multimodal Extension Workspace

Write all geometry or multimodal extension outputs here.

## Current Mainline

The current 3DGraphLLM+ mainline is the clean model-facing export under:

```text
../exports/3dgraphllm_functional_eval_v1/
```

This `multimodal_extension/` directory is now a legacy sidecar workspace. The geometry
and P0 perception files here remain useful inputs, but they are not the primary
entry point for native 3DGraphLLM evaluation or relation-conditioned crop QC.

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

## Perception Sidecar Status

The old perception task plan has been removed. This directory only retains the
raw modality availability audit:

```text
perception/p0_raw_modality_availability.csv
perception/p0_availability_summary.md
```

Do not add new crop generation or 3DGraphLLM preprocessing here. Native
3DGraphLLM evaluation and official crop/QC metadata should use
`../exports/3dgraphllm_functional_eval_v1/`.

