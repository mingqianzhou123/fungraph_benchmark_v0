# FunTHOR v1 External Extension

This folder stores compact FunTHOR metadata used to generate external functional-query coverage for the FunGraph full-modality release.

Files:

- `funthor_manifest.json`: compact scene/node/edge metadata, raw HF asset pointers, and counts.
- `../../splits/funthor_functional_queries_v1.jsonl`: protocol-generated functional queries.
- `../../splits/funthor_minimal_pairs_v1.jsonl`: same-label functional-element diagnostic pairs.
- `../../query_protocol_v1.md`: shared multi-dataset query protocol.

Generated queries: 805
Generated minimal pairs: 200

The generated rows are paper-disabled until human wording review, visual/evidence spot-check, and Dennis signoff.


Factorized v2 queries: 1655

`../../splits/funthor_functional_queries_factorized_v2.jsonl` is the newer controlled split. It keeps v1's grounded functional edges but varies `functional_query_type`, `spatial_scope`, and `anchor_visibility` so we can measure which factor drives model performance.
