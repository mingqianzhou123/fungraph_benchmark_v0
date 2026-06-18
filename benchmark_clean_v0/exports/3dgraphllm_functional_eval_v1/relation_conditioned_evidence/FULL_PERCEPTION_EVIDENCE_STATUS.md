# Full Perception Evidence Status

This layer provides one inspectable visual evidence card for every relation in the 3DGraphLLM functional export.

## Result

- Status: `full_perception_evidence_ready`
- Selection rule: `full_perception_evidence_v1_20260618_rgbd_or_pointcloud`
- Visual evidence ready: 683 / 683
- Depth-tested RGB-D crop relations: 240 / 683
- Pointcloud-render fallback relations: 443 / 683
- Pointcloud-render images: 683
- Image root: `relation_conditioned_evidence/full_perception_evidence/images`

## Boundary

Full coverage is achieved with a tiered evidence policy: strict RGB-D crop when available, otherwise a GT pointcloud-render fallback. Do not report the fallback rows as depth-tested camera evidence.

The strict RGB-D crop layer remains `official_crop_*`. This full-coverage layer is the benchmark-facing perception evidence layer when every relation needs an inspectable visual artifact.
