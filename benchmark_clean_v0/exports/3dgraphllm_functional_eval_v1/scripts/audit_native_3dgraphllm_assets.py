#!/usr/bin/env python3
"""Audit whether this export has real native 3DGraphLLM scene features."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import torch

EXPORT_DIR = Path(__file__).resolve().parents[1]
NATIVE_PACKET_DIR = EXPORT_DIR / "native_3dgraphllm"

NATIVE_FILENAMES = {
    "attributes": "scannet_mask3d_val_attributes.pt",
    "uni3d_feats": "scannet_mask3d_uni3d_feats.pt",
    "videofeats": "scannet_mask3d_videofeats.pt",
    "gnn_feats": "scannet_mask3d_val_gnn_feats_2.pt",
}

PACKET_FILENAMES = {
    "attributes": "fungraph_scene3d_attributes.pt",
    "uni3d_feats": "fungraph_scene3d_uni3d_feats.pt",
    "videofeats": "fungraph_scene3d_videofeats.pt",
    "gnn_feats": "fungraph_scene3d_gnn_feats.pt",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def scene_from_feature_key(key: str) -> str:
    parts = key.split("_")
    return "_".join(parts[:2]) if len(parts) >= 2 else key


def load_torch_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    obj = torch.load(path, map_location="cpu")
    return obj if isinstance(obj, dict) else {}


def tensor_shape(value: Any) -> list[int] | None:
    shape = getattr(value, "shape", None)
    return list(shape) if shape is not None else None


def inspect_dict(name: str, data: dict[str, Any]) -> dict[str, Any]:
    keys = list(data.keys())
    sample_key = keys[0] if keys else None
    sample_value = data[sample_key] if sample_key is not None else None
    return {
        "name": name,
        "n_keys": len(keys),
        "sample_keys": keys[:8],
        "sample_value_type": type(sample_value).__name__ if sample_key is not None else None,
        "sample_value_shape": tensor_shape(sample_value),
        "sample_value_keys": list(sample_value.keys()) if isinstance(sample_value, dict) else None,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "source_scene_id",
        "native_packet_scene_id",
        "n_export_candidates",
        "native_scannet_attributes",
        "native_scannet_uni3d",
        "native_scannet_video",
        "native_scannet_gnn",
        "packet_attributes",
        "packet_uni3d",
        "packet_video",
        "packet_gnn",
        "status",
        "note",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, Any]], schema: dict[str, Any]) -> None:
    n_scenes = len(rows)
    native_ready = sum(row["status"] == "native_feature_ready" for row in rows)
    packet_ready = sum(row["status"] in {"native_feature_ready", "adapter_packet_ready", "real_modality_adapter_ready"} for row in rows)
    missing_native = [row["source_scene_id"] for row in rows if row["status"] != "native_feature_ready"]

    text = f"""# Native 3DGraphLLM Asset Alignment Report

## Result

- Export scenes audited: {n_scenes}
- Scenes with real original 3DGraphLLM/ScanNet native features: {native_ready}/{n_scenes}
- Scenes with generated FunGraph adapter packet files: {packet_ready}/{n_scenes}

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

{chr(10).join(f"- `{scene_id}`" for scene_id in missing_native)}

## Required Real Feature Files

- `native_3dgraphllm/fungraph_scene3d_attributes.pt`
- `native_3dgraphllm/fungraph_scene3d_uni3d_feats.pt`
- `native_3dgraphllm/fungraph_scene3d_videofeats.pt`
- `native_3dgraphllm/fungraph_scene3d_gnn_feats.pt`

## Source Schema Snapshot

```json
{json.dumps(schema, indent=2, sort_keys=True)}
```
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphllm-root",
        type=Path,
        default=Path("/home/mz560/3D scene graph project/3DGraphLLM"),
        help="Path to the local 3DGraphLLM checkout.",
    )
    parser.add_argument("--packet-dir", type=Path, default=NATIVE_PACKET_DIR)
    args = parser.parse_args()

    candidate_rows = read_jsonl(EXPORT_DIR / "candidate_objects.jsonl")
    export_scene_to_candidates = {
        str(row["scene_id"]): list(row["candidate_node_ids"])
        for row in candidate_rows
    }

    native_data = {
        name: load_torch_dict(args.graphllm_root / "annotations" / filename)
        for name, filename in NATIVE_FILENAMES.items()
    }
    packet_data = {
        name: load_torch_dict(args.packet_dir / filename)
        for name, filename in PACKET_FILENAMES.items()
    }
    packet_manifest_path = args.packet_dir / "native_packet_manifest.json"
    packet_status = "unknown"
    if packet_manifest_path.exists():
        packet_status = json.loads(packet_manifest_path.read_text(encoding="utf-8")).get("status", "unknown")

    native_attr_scenes = set(native_data["attributes"])
    native_uni3d_scenes = {scene_from_feature_key(key) for key in native_data["uni3d_feats"]}
    native_video_scenes = {scene_from_feature_key(key) for key in native_data["videofeats"]}
    native_gnn_scenes = set(native_data["gnn_feats"])

    packet_attr_scenes = set(packet_data["attributes"])
    packet_uni3d_scenes = {scene_from_feature_key(key) for key in packet_data["uni3d_feats"]}
    packet_video_scenes = {scene_from_feature_key(key) for key in packet_data["videofeats"]}
    packet_gnn_scenes = set(packet_data["gnn_feats"])

    rows: list[dict[str, Any]] = []
    for source_scene_id, candidate_nodes in sorted(export_scene_to_candidates.items()):
        packet_scene_id = f"sf3d{source_scene_id}_00"
        native_flags = {
            "native_scannet_attributes": source_scene_id in native_attr_scenes,
            "native_scannet_uni3d": source_scene_id in native_uni3d_scenes,
            "native_scannet_video": source_scene_id in native_video_scenes,
            "native_scannet_gnn": source_scene_id in native_gnn_scenes,
        }
        packet_flags = {
            "packet_attributes": packet_scene_id in packet_attr_scenes,
            "packet_uni3d": packet_scene_id in packet_uni3d_scenes,
            "packet_video": packet_scene_id in packet_video_scenes,
            "packet_gnn": packet_scene_id in packet_gnn_scenes,
        }
        if all(native_flags.values()):
            status = "native_feature_ready"
            note = "Original native 3DGraphLLM feature bundle covers this scene."
        elif all(packet_flags.values()):
            if packet_status == "real_scene3d_modality_features_ready_not_pretrained_uni3d":
                status = "real_modality_adapter_ready"
                note = "Generated adapter packet exists with real SceneFun3D point/color/RGB-D/camera/geometry features; not original pretrained Uni3D/video embeddings."
            else:
                status = "adapter_packet_ready"
                note = "Generated adapter packet exists; feature tensors are fallback placeholders unless replaced."
        else:
            status = "blocked"
            note = "Missing both native ScanNet features and generated adapter packet files."
        rows.append(
            {
                "source_scene_id": source_scene_id,
                "native_packet_scene_id": packet_scene_id,
                "n_export_candidates": len(candidate_nodes),
                **native_flags,
                **packet_flags,
                "status": status,
                "note": note,
            }
        )

    schema = {
        "original_3dgraphllm": {name: inspect_dict(name, data) for name, data in native_data.items()},
        "fungraph_native_packet": {name: inspect_dict(name, data) for name, data in packet_data.items()},
    }
    write_csv(EXPORT_DIR / "native_3dgraphllm_asset_manifest.csv", rows)
    write_report(EXPORT_DIR / "asset_alignment_report.md", rows, schema)
    with (EXPORT_DIR / "native_3dgraphllm_asset_schema.json").open("w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print("Wrote native asset audit outputs")
    print(json.dumps({"scenes": len(rows), "statuses": {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})}}, indent=2))


if __name__ == "__main__":
    main()
