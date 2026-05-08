# Raw Asset Pointers

Large raw assets are intentionally not duplicated in `benchmark_clean_v0/`.

Use these source directories when geometry or multimodal extension work needs raw SceneFun3D assets:

```text
SceneFun3D_Graph/SceneFun3D_Graph/dev/
SceneFun3D_Graph/SceneFun3D_Graph/test/
```

Currently visible local assets include:

```text
*_laser_scan.ply
metadata.csv
```

The project README says SceneFun3D can also provide RGB images, depth, intrinsics, trajectories, and transforms, but those files may not all be present in the local package. Verify availability before starting any RGB crop or 3DGraphLLM-style preprocessing work.

