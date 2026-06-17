# Native 3DGraphLLM Asset Alignment Report

## Result

- Export scenes audited: 20
- Scenes with real original 3DGraphLLM/ScanNet native features: 0/20
- Scenes with generated FunGraph adapter packet files: 0/20

## Interpretation

The current SceneFun3D benchmark scenes use numeric ids such as `421380`.
Original 3DGraphLLM assets use ScanNet ids such as `scene0011_00`, with object
feature keys such as `scene0011_00_00`. Therefore the original downloaded
3DGraphLLM feature bundle does not directly cover the FunGraph/SceneFun3D eval
scenes.

`native_3dgraphllm/` is loader-ready and can be used for 3DGraphLLM integration
runs. If the packet status is `real_scene3d_modality_features_ready_not_pretrained_uni3d`,
its tensors are real SceneFun3D point/color/RGB-D/camera/geometry features. They
are still not the original pretrained Uni3D/video-network embeddings, so results
should be reported as adapter-feature results unless those encoder-specific
features are later regenerated.

## Missing Real Native Features

- `420683`
- `421013`
- `421015`
- `421063`
- `421254`
- `421267`
- `421380`
- `421602`
- `422007`
- `422391`
- `422813`
- `422826`
- `460417`
- `460419`
- `466183`
- `466192`
- `466803`
- `467293`
- `468076`
- `469011`

## Required Real Feature Files

- `native_3dgraphllm/fungraph_scene3d_attributes.pt`
- `native_3dgraphllm/fungraph_scene3d_uni3d_feats.pt`
- `native_3dgraphllm/fungraph_scene3d_videofeats.pt`
- `native_3dgraphllm/fungraph_scene3d_gnn_feats.pt`

## Source Schema Snapshot

```json
{
  "fungraph_native_packet": {
    "attributes": {
      "n_keys": 20,
      "name": "attributes",
      "sample_keys": [
        "sf3d420683_00",
        "sf3d421013_00",
        "sf3d421015_00",
        "sf3d421063_00",
        "sf3d421254_00",
        "sf3d421267_00",
        "sf3d421380_00",
        "sf3d421602_00"
      ],
      "sample_value_keys": [
        "objects",
        "locs",
        "obj_ids",
        "source_scene_id",
        "node_ids"
      ],
      "sample_value_shape": null,
      "sample_value_type": "dict"
    },
    "gnn_feats": {
      "n_keys": 20,
      "name": "gnn_feats",
      "sample_keys": [
        "sf3d420683_00",
        "sf3d421013_00",
        "sf3d421015_00",
        "sf3d421063_00",
        "sf3d421254_00",
        "sf3d421267_00",
        "sf3d421380_00",
        "sf3d421602_00"
      ],
      "sample_value_keys": null,
      "sample_value_shape": [
        42,
        512
      ],
      "sample_value_type": "Tensor"
    },
    "uni3d_feats": {
      "n_keys": 317,
      "name": "uni3d_feats",
      "sample_keys": [
        "sf3d420683_00_00",
        "sf3d420683_00_01",
        "sf3d420683_00_02",
        "sf3d420683_00_03",
        "sf3d420683_00_04",
        "sf3d420683_00_05",
        "sf3d420683_00_06",
        "sf3d420683_00_07"
      ],
      "sample_value_keys": null,
      "sample_value_shape": [
        1024
      ],
      "sample_value_type": "Tensor"
    },
    "videofeats": {
      "n_keys": 317,
      "name": "videofeats",
      "sample_keys": [
        "sf3d420683_00_00",
        "sf3d420683_00_01",
        "sf3d420683_00_02",
        "sf3d420683_00_03",
        "sf3d420683_00_04",
        "sf3d420683_00_05",
        "sf3d420683_00_06",
        "sf3d420683_00_07"
      ],
      "sample_value_keys": null,
      "sample_value_shape": [
        1024
      ],
      "sample_value_type": "Tensor"
    }
  },
  "original_3dgraphllm": {
    "attributes": {
      "n_keys": 312,
      "name": "attributes",
      "sample_keys": [
        "scene0011_00",
        "scene0011_01",
        "scene0015_00",
        "scene0019_00",
        "scene0019_01",
        "scene0025_00",
        "scene0025_01",
        "scene0025_02"
      ],
      "sample_value_keys": [
        "objects",
        "locs"
      ],
      "sample_value_shape": null,
      "sample_value_type": "dict"
    },
    "gnn_feats": {
      "n_keys": 312,
      "name": "gnn_feats",
      "sample_keys": [
        "scene0430_00",
        "scene0100_02",
        "scene0357_01",
        "scene0329_01",
        "scene0552_01",
        "scene0609_03",
        "scene0496_00",
        "scene0645_01"
      ],
      "sample_value_keys": null,
      "sample_value_shape": [
        200,
        512
      ],
      "sample_value_type": "Tensor"
    },
    "uni3d_feats": {
      "n_keys": 226638,
      "name": "uni3d_feats",
      "sample_keys": [
        "scene0000_00_00",
        "scene0000_00_01",
        "scene0000_00_02",
        "scene0000_00_03",
        "scene0000_00_04",
        "scene0000_00_05",
        "scene0000_00_06",
        "scene0000_00_07"
      ],
      "sample_value_keys": null,
      "sample_value_shape": [
        1024
      ],
      "sample_value_type": "Tensor"
    },
    "videofeats": {
      "n_keys": 213319,
      "name": "videofeats",
      "sample_keys": [
        "scene0173_00_00",
        "scene0173_00_01",
        "scene0173_00_02",
        "scene0173_00_03",
        "scene0173_00_04",
        "scene0173_00_05",
        "scene0173_00_06",
        "scene0173_00_07"
      ],
      "sample_value_keys": null,
      "sample_value_shape": [
        1024
      ],
      "sample_value_type": "Tensor"
    }
  }
}
```
