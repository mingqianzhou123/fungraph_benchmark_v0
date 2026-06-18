# Official Relation Crop Status

This is the frozen relation-conditioned crop metadata layer for the FunGraph 3DGraphLLM export. It scans each scene's full RGB-D frame pool with a fast geometric prefilter, then applies depth z-test to the top candidates. It does not run baselines or learned feature extraction.

## Result

- Status: `official_relation_crop_metadata_ready`
- Selection rule: `covisible_depth_ztest_v1_20260618_full_frame_mining`
- Frame source: `all_scene_rgbd_frames`
- Relations crop-ready: 240 / 683
- Co-visible depth-tested frame rows: 1526 / 14267
- Depth z-test tolerance: 0.15 m

## Failure Reasons

For the 443 relations without a selected crop under the frozen rule:

- target_not_depth_visible: 418
- no_prefiltered_frames: 16
- target_anchor_not_covisible_same_frame: 7
- anchor_not_depth_visible: 2

## Boundary

Crop metadata is frozen and depth-tested. Crop images are generated locally under ignored crops_local/ and are not committed; QC overlays are diagnostic spot-check artifacts.

Large crop images live under ignored `crops_local/` when generated and are not committed.
