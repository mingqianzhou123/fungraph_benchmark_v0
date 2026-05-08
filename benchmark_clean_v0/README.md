# Benchmark Clean v0

Frozen benchmark interface for CoRL 2026 FunRAG / FCGP experiments.

Created: 2026-05-08

This folder is a clean entry point for two parallel work streams:

- Mingqian continues the text-level FCGP / L-FCGP / LLM grounding experiments.
- The intern builds additive geometry or multimodal sidecar files without changing the benchmark.

## Rule

Do not modify the files in `queries/`, `graphs/`, `geometry/`, or `annotations/` in place.

All extensions should be written under:

```text
multimodal_extension/
```

If the benchmark interface needs to change, create a new folder such as `benchmark_clean_v1/` rather than silently editing v0.

## Canonical Files

For quick audits that do not need full scene graphs, use the lightweight query indices:

```text
queries/all_queries_index.jsonl
queries/train_queries_index.jsonl
queries/val_queries_index.jsonl
queries/test_queries_index.jsonl
```

These contain only query-level fields such as `scene_id`, `target_node_ids`, `anchor_node_id`, and `supporting_edge_ids`.

### SceneFun3D / OpenFunGraph

Use this file for SceneFun3D functional grounding queries:

```text
queries/scenefun3d_funrag_benchmark_enriched.json
```

This is copied from:

```text
SceneFun3D_Graph/SceneFun3D_Graph/benchmark/funrag_benchmark_enriched.json
```

It contains query text, split, target node ids, supporting functional edge ids, action verbs, and an embedded scene graph for each query.

SceneFun3D node geometry is here:

```text
geometry/scenefun3d_node_geom.json
```

It maps:

```text
scene_id -> node_id -> bbox_center / bbox_min / bbox_max
```

### 3DSSG

Use this file for 3DSSG spatial, semantic, and compositional queries:

```text
queries/3dssg_benchmark_enriched.json
```

Use this file for the corresponding 3DSSG scene graphs:

```text
graphs/3dssg_scene_graphs_enriched.json
```

These are copied from:

```text
3dssg/processed/3dssg_benchmark_enriched.json
3dssg/processed/scene_graphs_enriched.json
```

## Unified Loader Compatibility

The current project loader is:

```text
funrag/unified_dataset.py
```

Its canonical item schema is:

```text
query_id
dataset
scene_id
split
query
query_type
annotation_source
target_node_ids
target_labels
anchor_node_id
supporting_edge_id
supporting_edge_ids
action_verb
scene_graph.nodes
scene_graph.edges
_extra
```

The clean files preserve the enriched fields used by that loader, including `edge_id`, `edge_family`, `supporting_edge_id`, `supporting_edge_ids`, and SceneFun3D bbox fields where available.

## Folder Guide

```text
queries/
  Canonical benchmark query files.

graphs/
  External graph store needed by 3DSSG.
  SceneFun3D graphs are embedded in the query file.

geometry/
  Object-level geometry side information already available for SceneFun3D nodes.

annotations/
  Source OpenFunGraph annotations and labels, for auditing and multimodal alignment.

raw_assets/
  Pointers to raw SceneFun3D assets. Large point clouds are not copied here.

manifests/
  File inventory, audit outputs, and summary metadata.

multimodal_extension/
  Only place where new intern outputs should be written.
```

## Intern Starting Point

Start from:

```text
README.md
manifests/benchmark_file_manifest.md
manifests/benchmark_summary.json
multimodal_extension/README.md
```

Then use:

```text
queries/all_queries_index.jsonl
queries/scenefun3d_funrag_benchmark_enriched.json
geometry/scenefun3d_node_geom.json
annotations/openfungraph/SceneFun3D.annotations.json
annotations/openfungraph/SceneFun3D.relations.json
```

Write all new outputs to:

```text
multimodal_extension/
```

The first deliverables should be coverage and feature-bank files, not a full RGB or Uni3D pipeline.
