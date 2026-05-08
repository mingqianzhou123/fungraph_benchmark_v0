# Multimodal Extension Workspace

Write all geometry or multimodal extension outputs here.

Do not edit the frozen benchmark files in:

```text
../queries/
../graphs/
../geometry/
../annotations/
```

## Required First Deliverables

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

## First Task

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

## Optional Later Work

Only after the geometry extension is complete, check whether RGB/camera files exist locally. If they do, create a small RGB pilot under:

```text
rgb_pilot/
```

Do not start full DINOv2, CLIP, Uni3D, or 3DGraphLLM preprocessing until the geometry deliverables are finished.

