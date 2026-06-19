# FunGraph Full-Modality Release v1

This is the human-facing benchmark package for the 3DGraphLLM+ multimodal functional-reasoning work.
It is organized after the FunTHOR release pattern, but uses compact metadata and relative raw-asset pointers instead of duplicating large files.

## Structure

```text
fungraph_full_modality_release_v1/
  dataset_manifest.json
  dataset_unique_labels.json
  dataset_functional_labels.json
  dataset_unique_relations.json
  annotation_rules/functional_relation_taxonomy.json
  splits/*.jsonl
  scenes/<scene_id>/
    scene.json
    frames.jsonl
```

## Current Counts

- Scenes: 20
- Candidate nodes: 317
- Functional part-like nodes: 209
- Functional relations: 195
- RGB-D-camera frame rows: 13039
- Unique labels: 54
- Unique relation strings: 21

## What To Read First

1. `dataset_manifest.json` for global counts, scene paths, split paths, and remaining semantic gaps.
2. `scenes/<scene_id>/scene.json` for one scene's nodes, functional relations, modality readiness, and visible subset analogue.
3. `splits/functional_500.jsonl` and `splits/human_133.jsonl` for current frozen eval queries.
4. `splits/expansion_functional_116_candidates.jsonl` only as paper-disabled candidates requiring human/Dennis signoff.

## Boundary

This package is a clean release view over the existing export. It does not move or copy raw RGB-D images, depth frames, laser scans, or the full OpenFunGraph point-index arrays. Those are referenced by relative paths and source pointers.
