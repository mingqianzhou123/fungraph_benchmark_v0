# Projection Dry-Run Status

This directory records placeholder projection metadata for relation-conditioned evidence. It does not run baselines, does not extract encoder features, and does not create official benchmark crops.

## Result

- Status: `projection_dryrun_placeholder_ready`
- Relations checked: 683
- Projection rows: 4089
- Relations with placeholder co-visible frame: 331 / 683
- Frame rows with placeholder co-visibility: 355

## Boundary

This is a placeholder dry-run projection index, not official crop evidence. Pose convention and visibility thresholds must be audited before using crops as benchmark evidence.

Depth z-test is not applied. The rule is explicitly marked `is_placeholder_rule = true` in every row.
