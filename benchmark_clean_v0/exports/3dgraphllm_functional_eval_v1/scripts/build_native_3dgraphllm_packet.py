#!/usr/bin/env python3
"""Build a native 3DGraphLLM eval packet for the FunGraph export.

This produces files that 3DGraphLLM's ``ValDataset`` can read directly. The
packet is intentionally explicit about feature provenance:

- geometry attributes come from SceneFun3D node boxes;
- object/text/video/GNN feature tensors are deterministic zero fallbacks unless
  a real SceneFun3D-native feature extractor has produced replacements.

The fallback tensors make loader/model smoke tests possible, but they are not a
valid full-modality scientific evaluation.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import torch

EXPORT_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = EXPORT_DIR.parents[1]
PACKET_DIR = EXPORT_DIR / "native_3dgraphllm"

GEOMETRY_CSV = BENCHMARK_ROOT / "multimodal_extension" / "node_geometry_features.csv"
ANNOTATIONS_JSON = BENCHMARK_ROOT / "annotations" / "openfungraph" / "SceneFun3D.annotations.json"
NODE_MAPPING_JSON = EXPORT_DIR / "node_id_mapping.json"

QUERY_FILES = {
    "functional_500": EXPORT_DIR / "functional_500_eval.jsonl",
    "human_133": EXPORT_DIR / "human_133_eval.jsonl",
    "long_range_50": EXPORT_DIR / "long_range_50_eval.jsonl",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def native_scene_id(scene_id: str) -> str:
    return f"sf3d{scene_id}_00"


def load_labels() -> dict[str, str]:
    rows = json.loads(ANNOTATIONS_JSON.read_text(encoding="utf-8"))
    labels: dict[str, str] = {}
    for row in rows:
        scene_id = str(row.get("scene_id", ""))
        node_id = str(row.get("annot_id", ""))
        if scene_id and node_id:
            labels[f"{scene_id}/{node_id}"] = str(row.get("label") or "")
    return labels


def load_geometry() -> dict[str, dict[str, Any]]:
    labels = load_labels()
    by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with GEOMETRY_CSV.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if str(row.get("has_bbox", "")).lower() != "true":
                continue
            scene_id = str(row["scene_id"])
            node_id = str(row["node_id"])
            key = f"{scene_id}/{node_id}"
            by_scene[scene_id].append(
                {
                    "scene_id": scene_id,
                    "node_id": node_id,
                    "label": labels.get(key, ""),
                    "center_size": [
                        float(row["bbox_center_x"]),
                        float(row["bbox_center_y"]),
                        float(row["bbox_center_z"]),
                        float(row["bbox_size_x"]),
                        float(row["bbox_size_y"]),
                        float(row["bbox_size_z"]),
                    ],
                }
            )

    out: dict[str, dict[str, Any]] = {}
    for scene_id, items in by_scene.items():
        items = sorted(items, key=lambda item: item["node_id"])
        out[scene_id] = {
            "items": items,
            "node_to_obj": {item["node_id"]: idx for idx, item in enumerate(items)},
        }
    return out


def build_attributes_and_features(geometry: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, torch.Tensor], dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    attributes: dict[str, Any] = {}
    uni3d_feats: dict[str, torch.Tensor] = {}
    video_feats: dict[str, torch.Tensor] = {}
    gnn_feats: dict[str, torch.Tensor] = {}

    for source_scene_id, scene in sorted(geometry.items()):
        nscene = native_scene_id(source_scene_id)
        items = scene["items"]
        locs = torch.tensor([item["center_size"] for item in items], dtype=torch.float32)
        obj_ids = list(range(len(items)))
        attributes[nscene] = {
            "objects": [item["label"] for item in items],
            "locs": locs,
            "obj_ids": obj_ids,
            "source_scene_id": source_scene_id,
            "node_ids": [item["node_id"] for item in items],
        }
        for obj_id in obj_ids:
            key = f"{nscene}_{obj_id:02}"
            uni3d_feats[key] = torch.zeros(1024, dtype=torch.float32)
            video_feats[key] = torch.zeros(1024, dtype=torch.float32)
        gnn_feats[nscene] = torch.zeros((len(items) * 2, 512), dtype=torch.float32)

    return attributes, uni3d_feats, video_feats, gnn_feats


def build_native_annos(name: str, rows: list[dict[str, Any]], geometry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    annos: list[dict[str, Any]] = []
    skipped = 0
    for row in rows:
        scene_id = str(row["scene_id"])
        target_node_id = str(row["target_node_id"])
        scene = geometry.get(scene_id)
        if not scene or target_node_id not in scene["node_to_obj"]:
            skipped += 1
            continue
        obj_id = int(scene["node_to_obj"][target_node_id])
        annos.append(
            {
                "qid": str(row["query_id"]),
                "scene_id": native_scene_id(scene_id),
                "source_scene_id": scene_id,
                "obj_id": obj_id,
                "pred_id": obj_id,
                "prompt": str(row["prompt"]),
                "ref_captions": [f"<OBJ{obj_id:03}>."],
                "target_node_id": target_node_id,
                "source": row.get("source"),
                "eval_type": name,
            }
        )
    if skipped:
        print(f"{name}: skipped {skipped} rows without geometry target")
    return annos


def update_node_mapping(geometry: dict[str, dict[str, Any]]) -> None:
    mapping = json.loads(NODE_MAPPING_JSON.read_text(encoding="utf-8"))
    for key, item in mapping.items():
        scene_id = str(item["scene_id"])
        node_id = str(item["node_id"])
        obj_id = geometry.get(scene_id, {}).get("node_to_obj", {}).get(node_id)
        if obj_id is None:
            item["3dgraphllm_scene_id"] = None
            item["3dgraphllm_object_id"] = None
            item["mapping_status"] = "missing_geometry"
        else:
            item["3dgraphllm_scene_id"] = native_scene_id(scene_id)
            item["3dgraphllm_object_id"] = int(obj_id)
            item["mapping_status"] = "native_packet_geometry_aligned"
    write_json(NODE_MAPPING_JSON, mapping)


def write_config(packet_dir: Path) -> None:
    config_text = f'''# Auto-generated FunGraph native 3DGraphLLM eval config.
# This inherits the local reproduced 3DGraphLLM config and only overrides the
# dataset-facing fields. Use from the 3DGraphLLM repository root:
# python tasks/train.py {packet_dir / "config_fungraph_eval.py"} evaluate True pretrained_path ./demo/3dgraphllm.pth val_tag fungraph_functional_500

_base_ = "/home/mz560/3D scene graph project/3DGraphLLM/scripts/config.py"

anno_root = "{packet_dir}"
pc_encoder = "uni3d"
segmentor = "fungraph_geometry_fallback"
version = ""

seg_feat_file = f"{{anno_root}}/fungraph_scene3d_uni3d_feats.pt"
seg_img_feat_file = f"{{anno_root}}/fungraph_scene3d_videofeats.pt"
seg_val_attr_file = f"{{anno_root}}/fungraph_scene3d_attributes.pt"
seg_val_gnn_file = f"{{anno_root}}/fungraph_scene3d_gnn_feats.pt"

train_tag = "fungraph_functional_500"
val_tag = "fungraph_functional_500"

train_file_dict = {{}}
val_file_dict = {{
    "fungraph_functional_500": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{{anno_root}}/fungraph_functional_500_val.json", seg_val_gnn_file, "gt"],
    "fungraph_human_133": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{{anno_root}}/fungraph_human_133_val.json", seg_val_gnn_file, "gt"],
    "fungraph_long_range_50": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{{anno_root}}/fungraph_long_range_50_val.json", seg_val_gnn_file, "gt"],
    "fungraph_smoke_1": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{{anno_root}}/fungraph_smoke_1_val.json", seg_val_gnn_file, "gt"],
}}

num_workers = 0
batch_size = 4
evaluate = True
wandb = dict(enable=False)
do_save = False
model = dict(knn=2, max_knn=2)
'''
    (packet_dir / "config_fungraph_eval.py").write_text(config_text, encoding="utf-8")


def write_manifest(packet_dir: Path, counts: dict[str, int]) -> None:
    manifest = {
        "status": "loader_smoke_test_ready_not_full_modality",
        "feature_provenance": {
            "attributes": "SceneFun3D graph node 3D bounding boxes",
            "uni3d_feats": "zero fallback tensors; replace with real SceneFun3D Uni3D object features before scientific evaluation",
            "videofeats": "zero fallback tensors; replace with real RGB-D/video object features before scientific evaluation",
            "gnn_feats": "zero fallback tensors; replace with extracted graph-neighborhood features before scientific evaluation",
        },
        "native_scene_id_rule": "sf3d{source_scene_id}_00",
        "annotation_counts": counts,
        "required_replacement_files_for_full_modality": [
            "fungraph_scene3d_uni3d_feats.pt",
            "fungraph_scene3d_videofeats.pt",
            "fungraph_scene3d_gnn_feats.pt",
        ],
    }
    write_json(packet_dir / "native_packet_manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-dir", type=Path, default=PACKET_DIR)
    args = parser.parse_args()

    packet_dir = args.packet_dir
    packet_dir.mkdir(parents=True, exist_ok=True)

    geometry = load_geometry()
    attributes, uni3d_feats, video_feats, gnn_feats = build_attributes_and_features(geometry)

    torch.save(attributes, packet_dir / "fungraph_scene3d_attributes.pt")
    torch.save(uni3d_feats, packet_dir / "fungraph_scene3d_uni3d_feats.pt")
    torch.save(video_feats, packet_dir / "fungraph_scene3d_videofeats.pt")
    torch.save(gnn_feats, packet_dir / "fungraph_scene3d_gnn_feats.pt")

    counts: dict[str, int] = {}
    built_annos: dict[str, list[dict[str, Any]]] = {}
    for name, path in QUERY_FILES.items():
        annos = build_native_annos(name, read_jsonl(path), geometry)
        built_annos[name] = annos
        write_json(packet_dir / f"fungraph_{name}_val.json", annos)
        counts[name] = len(annos)

    smoke_annos = built_annos["functional_500"][:1]
    write_json(packet_dir / "fungraph_smoke_1_val.json", smoke_annos)
    counts["smoke_1"] = len(smoke_annos)

    update_node_mapping(geometry)
    write_config(packet_dir)
    write_manifest(packet_dir, counts)
    print(f"Wrote native 3DGraphLLM packet to {packet_dir}")
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
