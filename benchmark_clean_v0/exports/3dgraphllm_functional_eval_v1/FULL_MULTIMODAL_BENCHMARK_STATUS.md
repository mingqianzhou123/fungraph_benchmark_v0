# Full Multimodal Benchmark Status

This document describes the data side of the benchmark, not model baselines.

## Result

- Status: `full_raw_multimodal_benchmark_ready`
- Scenes full ready: 20 / 20
- Captures indexed: 55
- RGB-D-camera frame triplets indexed: 13039
- Export candidate objects full ready: 317 / 317

## What Full Means Here

- every exported SceneFun3D scene has a laser-scan point cloud;
- every capture has RGB frames, depth frames, camera intrinsics, and a trajectory file;
- every indexed frame triplet has RGB, depth, and intrinsics paths;
- every exported candidate object has annotation point indices, bbox geometry, record-camera metadata, and native 3DGraphLLM feature keys;
- raw assets are referenced by manifest paths and are not copied into the repository.

## Important Boundary

Raw modalities are complete and native packet feature keys are aligned. Existing 1024-D packet tensors are deterministic SceneFun3D adapter features, not pretrained Uni3D/DINO/VLSAT encoder embeddings.

To turn the native packet into original-3DGraphLLM-style pretrained features, run the chosen 3D/2D/relation encoders on these indexed raw assets and replace the adapter tensors while preserving the manifest keys.
