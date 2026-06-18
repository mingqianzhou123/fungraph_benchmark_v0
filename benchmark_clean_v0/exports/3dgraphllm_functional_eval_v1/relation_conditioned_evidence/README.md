# Relation-Conditioned Evidence

This directory is the query-conditioned multimodal layer for the FunGraph 3DGraphLLM export.

Primary key:

```text
relation_key = query_id|target_node_id|anchor_node_id
```

Files:

- `relation_evidence_index.jsonl`: one row per query relation, with target and anchor object sidecars, native 3DGraphLLM feature keys, supporting edges, and candidate frame references.
- `query_relation_index.jsonl`: query id to relation keys.
- `relation_frame_candidates.jsonl`: RGB-D-camera frame triplets selected as raw candidates for later projection/crop generation.
- `minimal_pair_relation_index.jsonl`: minimal-pair rows linked to relation keys.
- `relation_evidence_summary.json`: machine-readable coverage summary.
- `RELATION_EVIDENCE_STATUS.md`: human-readable status and boundary notes.
- `projection_dryrun_index.jsonl`: placeholder projection metadata for target/anchor point segments in candidate RGB-D frames.
- `projection_dryrun_summary.json`: projection dry-run coverage summary.
- `PROJECTION_DRYRUN_STATUS.md`: human-readable projection dry-run status and boundary notes.
- `sample_load_relation_evidence.py`: tiny loader for querying this layer.

Important boundary: projection dry-run rows are not official crop evidence. They use a placeholder ARKit pose convention, no depth z-test, and a provisional visible-point threshold. Large raw crops and exported pointclouds should remain local unless explicitly approved.
