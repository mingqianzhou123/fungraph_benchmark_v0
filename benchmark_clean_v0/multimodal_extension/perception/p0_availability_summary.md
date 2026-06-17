# Phase 0 Raw Modality Availability Summary

Generated at: `2026-06-17T03:50:49`

## Inputs

- `queries/all_queries_index.jsonl`
- `raw_assets/scenefun3d_raw_asset_manifest.csv`
- `geometry/scenefun3d_node_geom.json`
- `multimodal_extension/node_geometry_features.csv`
- `multimodal_extension/feature_index.json`
- `annotations/openfungraph/SceneFun3D.annotations.json`
- `multimodal_extension/perception/p0_pilot_raw_asset_remap.csv`

## Scope

- SceneFun3D functional queries: 870
- Functional scenes: 20
- Unique target nodes: 190
- Unique anchor nodes: 90
- Split counts: {'test': 591, 'train': 198, 'val': 81}

## Availability Counts

- image_projection_ready: 6 / 20
- point_segment_ready: 6 / 20
- bbox_only: 14 / 20
- bbox_fallback_exists: 20 / 20

## Missing Breakdown

- missing_depth: 14 scenes
- missing_intrinsics: 14 scenes
- missing_laser_to_camera: 14 scenes
- missing_poses: 14 scenes
- missing_rgb: 14 scenes
- raw_path_not_found: 14 scenes

## Interpretation

- Crop pipeline status: partially ready.
- Pointcloud segment status: partially ready.
- The frozen raw asset manifest is unchanged; downloaded pilot assets are tracked only through `p0_pilot_raw_asset_remap.csv`.
- `lowres_poses` is treated as the official SceneFun3D camera trajectory asset.
- `SceneFun3D.annotations.json` contains point indices for all audited target and anchor nodes, so part/anchor point-index availability is not the current blocker.
- Existing geometry sidecars cover the audited functional nodes, so bbox-only fallback is available for Phase 1 geometry filtering.

## Gate

Phase 0 is complete, but Phase 1 should not start until Mingqian confirms whether the raw asset paths should be remapped, the missing RGB-D/camera assets should be downloaded, or the current package should be treated as bbox-only for perception planning.

## Output Files

- `perception/p0_raw_modality_availability.csv`
- `perception/p0_availability_summary.md`

## Scene IDs

```text
420683
421013
421015
421063
421254
421267
421380
421602
422007
422391
422813
422826
460417
460419
466183
466192
466803
467293
468076
469011
```
