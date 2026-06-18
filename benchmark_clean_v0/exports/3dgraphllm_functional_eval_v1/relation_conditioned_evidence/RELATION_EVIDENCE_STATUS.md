# Relation-Conditioned Evidence Status

This directory connects each functional query to target-anchor multimodal evidence. It does not run baselines or model inference.

## Result

- Status: `relation_conditioned_evidence_index_ready_not_projected`
- Relations indexed: 683
- Relations with target/anchor point and feature sidecars ready: 683 / 683
- Frame candidates: 4089
- Minimal pairs linked: 28 / 28

## Boundary

Frame candidates are RGB-D-camera triplets from the same scene, not yet projection-certified co-visible crops. Use them as projector/crop inputs, not final crop evidence.

The next data-only step is a projection/crop pass that writes co-visible crop metadata under the same `relation_key` values.
