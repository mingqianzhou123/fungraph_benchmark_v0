# Human Annotation Inputs

This folder contains human-authored functional query extensions used for
benchmark quality extension and for the perception pilot.

Key files:

```text
functional_queries_v1.jsonl
minimal_pairs_v1.jsonl
long_range_stress_queries_v1.jsonl
```

For the relation-conditioned perception task, use `minimal_pairs_v1.jsonl` as
the preferred Phase 2 pilot source after validating that each record aligns with
existing `query_id`, `scene_id`, `target_node_id`, and anchor/supporting-edge
fields. Do not modify these annotation files in place when producing perception
outputs; write new assets and manifests under:

```text
../../multimodal_extension/perception/
```
