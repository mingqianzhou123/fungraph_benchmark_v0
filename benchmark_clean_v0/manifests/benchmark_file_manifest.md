# Benchmark File Manifest

Created: 2026-05-08

This manifest lists the stable inputs copied into `benchmark_clean_v0/`.

| Clean path | Source path | Purpose |
|---|---|---|
| `queries/scenefun3d_funrag_benchmark_enriched.json` | `SceneFun3D_Graph/SceneFun3D_Graph/benchmark/funrag_benchmark_enriched.json` | Canonical SceneFun3D / OpenFunGraph benchmark used by FCGP. Includes query text, split, target nodes, supporting edges, action verbs, embedded graph, enriched edge ids/families, and bbox fields. |
| `queries/3dssg_benchmark_enriched.json` | `3dssg/processed/3dssg_benchmark_enriched.json` | Canonical 3DSSG benchmark used by the unified loader. Includes spatial, semantic, and compositional queries with enriched supporting edge fields. |
| `queries/all_queries_index.jsonl` | generated from clean query JSONs | Lightweight combined query index. Does not embed scene graphs; useful for coverage audits. |
| `queries/train_queries_index.jsonl` | generated from clean query JSONs | Lightweight train split query index. |
| `queries/val_queries_index.jsonl` | generated from clean query JSONs | Lightweight val split query index. |
| `queries/test_queries_index.jsonl` | generated from clean query JSONs | Lightweight test split query index. |
| `graphs/3dssg_scene_graphs_enriched.json` | `3dssg/processed/scene_graphs_enriched.json` | Canonical 3DSSG scene graph store. Required because 3DSSG query entries reference scene graphs by scene id. |
| `geometry/scenefun3d_node_geom.json` | `SceneFun3D_Graph/SceneFun3D_Graph/benchmark/scenefun3d_node_geom.json` | SceneFun3D node geometry: bbox center/min/max by scene id and node id. This is the starting point for geometry-grounded extension. |
| `annotations/openfungraph/SceneFun3D.annotations.json` | `SceneFun3D_Graph/SceneFun3D_Graph/annotations/openfungraph/SceneFun3D.annotations.json` | OpenFunGraph object and interactive-element annotations. Useful for auditing original node/object alignment. |
| `annotations/openfungraph/SceneFun3D.relations.json` | `SceneFun3D_Graph/SceneFun3D_Graph/annotations/openfungraph/SceneFun3D.relations.json` | OpenFunGraph functional relation annotations. Useful for supporting-edge audit. |
| `annotations/openfungraph/OpenFunGraph_split.txt` | `SceneFun3D_Graph/SceneFun3D_Graph/annotations/openfungraph/OpenFunGraph_split.txt` | Original OpenFunGraph split file. |
| `annotations/openfungraph/all_labels.json` | `SceneFun3D_Graph/SceneFun3D_Graph/annotations/openfungraph/all_labels.json` | OpenFunGraph label vocabulary. |
| `annotations/openfungraph/all_edges.json` | `SceneFun3D_Graph/SceneFun3D_Graph/annotations/openfungraph/all_edges.json` | OpenFunGraph relation vocabulary. |
| `manifests/scenefun3d_benchmark_audit.json` | `SceneFun3D_Graph/SceneFun3D_Graph/benchmark/benchmark_audit.json` | Existing SceneFun3D benchmark audit output. |
| `manifests/3dssg_dataset_stats.json` | `3dssg/processed/dataset_stats.json` | Existing 3DSSG processed dataset statistics. |
| `manifests/benchmark_summary.json` | generated from clean files | Counts by dataset, split, query type, geometry scenes/nodes, and 3DSSG scene graphs. |
| `raw_assets/scenefun3d_raw_asset_manifest.csv` | generated from local SceneFun3D package | Pointer list for local SceneFun3D point clouds and metadata files. |

## Raw Asset Policy

Large raw point clouds and any future RGB/depth assets are not copied into this clean folder. Keep those in their source directories and reference them through manifests.

Current SceneFun3D raw point clouds are under:

```text
SceneFun3D_Graph/SceneFun3D_Graph/dev/
SceneFun3D_Graph/SceneFun3D_Graph/test/
```

The intern should not move or rename raw assets.
