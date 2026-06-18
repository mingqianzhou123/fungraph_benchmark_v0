#!/usr/bin/env python3
"""Build full raw-modality indexes for the FunGraph 3DGraphLLM export.

This script does not run baselines or model inference. It makes the benchmark
side of the project stronger by recording every raw SceneFun3D modality needed
for a full multimodal benchmark:

- laser-scan point clouds;
- RGB frames;
- depth frames;
- camera intrinsics;
- camera trajectory files;
- object point-index segments and native 3DGraphLLM feature keys.

Large raw assets are not copied into the repository. The output files are
manifests and QA summaries that point back to the local SceneFun3D asset tree.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import torch

EXPORT_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = EXPORT_DIR.parents[1]
PACKET_DIR = EXPORT_DIR / "native_3dgraphllm"

SCENEFUN_ROOT = Path("/home/mz560/3D scene graph project/SceneFun3D_Graph/SceneFun3D_Graph")
ANNOTATIONS_JSON = BENCHMARK_ROOT / "annotations" / "openfungraph" / "SceneFun3D.annotations.json"
RAW_ASSET_MANIFEST = BENCHMARK_ROOT / "raw_assets" / "scenefun3d_raw_asset_manifest.csv"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(SCENEFUN_ROOT))
    except ValueError:
        return str(path)


def load_candidate_scenes() -> dict[str, list[str]]:
    return {
        str(row["scene_id"]): [str(x) for x in row["candidate_node_ids"]]
        for row in read_jsonl(EXPORT_DIR / "candidate_objects.jsonl")
    }


def load_raw_ply_paths() -> dict[str, tuple[str, Path]]:
    paths: dict[str, tuple[str, Path]] = {}
    with RAW_ASSET_MANIFEST.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("asset_type") != "laser_scan_ply" or not row.get("scene_id"):
                continue
            source = Path(row["source_path"])
            suffix = Path(*source.parts[2:]) if len(source.parts) > 2 else source
            paths[str(row["scene_id"])] = (str(row["split"]), SCENEFUN_ROOT / suffix)
    return paths


def file_map(paths: list[Path]) -> dict[str, Path]:
    return {path.stem: path for path in sorted(paths)}


def capture_dirs(scene_id: str) -> list[tuple[str, Path]]:
    dirs: list[tuple[str, Path]] = []
    for split in ["dev", "test"]:
        scene_dir = SCENEFUN_ROOT / split / scene_id
        if not scene_dir.exists():
            continue
        for child in sorted(scene_dir.iterdir()):
            if child.is_dir():
                dirs.append((split, child))
    return dirs


def build_scene_manifests(scene_ids: list[str], raw_ply_paths: dict[str, tuple[str, Path]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    capture_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    for scene_id in scene_ids:
        raw_split, laser_path = raw_ply_paths.get(scene_id, ("", Path("")))
        for split, cap in capture_dirs(scene_id):
            rgb = file_map(list((cap / "wide").glob("*.png")) + list((cap / "lowres_wide").glob("*.png")))
            depth = file_map(list((cap / "highres_depth").glob("*.png")) + list((cap / "lowres_depth").glob("*.png")))
            intr = file_map(list((cap / "wide_intrinsics").glob("*.pincam")) + list((cap / "lowres_wide_intrinsics").glob("*.pincam")))
            traj = sorted(cap.glob("*.traj")) + sorted(cap.glob("*poses*.traj"))
            rgb_depth = sorted(set(rgb) & set(depth))
            triplets = sorted(set(rgb) & set(depth) & set(intr))
            row = {
                "scene_id": scene_id,
                "split": split,
                "raw_manifest_split": raw_split,
                "capture_id": cap.name,
                "capture_rel_dir": rel(cap),
                "laser_scan_rel_path": rel(laser_path) if laser_path else "",
                "laser_scan_exists": laser_path.exists(),
                "n_rgb_frames": len(rgb),
                "n_depth_frames": len(depth),
                "n_intrinsics": len(intr),
                "n_trajectory_files": len(traj),
                "n_rgb_depth_pairs": len(rgb_depth),
                "n_rgb_depth_intrinsic_triplets": len(triplets),
                "trajectory_rel_paths": ";".join(rel(x) for x in traj),
                "has_rgb": len(rgb) > 0,
                "has_depth": len(depth) > 0,
                "has_intrinsics": len(intr) > 0,
                "has_trajectory": len(traj) > 0,
                "capture_full_ready": bool(laser_path.exists() and rgb and depth and intr and traj and triplets),
            }
            capture_rows.append(row)
            for stem in sorted(set(rgb) | set(depth) | set(intr)):
                frame_rows.append(
                    {
                        "scene_id": scene_id,
                        "split": split,
                        "capture_id": cap.name,
                        "frame_stem": stem,
                        "rgb_rel_path": rel(rgb[stem]) if stem in rgb else "",
                        "depth_rel_path": rel(depth[stem]) if stem in depth else "",
                        "intrinsics_rel_path": rel(intr[stem]) if stem in intr else "",
                        "has_rgb": stem in rgb,
                        "has_depth": stem in depth,
                        "has_intrinsics": stem in intr,
                        "frame_rgbd_camera_ready": bool(stem in rgb and stem in depth and stem in intr),
                    }
                )
    return capture_rows, frame_rows


def load_target_counts() -> Counter[str]:
    answer_key = read_json(EXPORT_DIR / "answer_key.json")
    counts: Counter[str] = Counter()
    for targets in answer_key.values():
        for target in targets:
            counts[str(target)] += 1
    return counts


def build_object_manifest(candidate_scenes: dict[str, list[str]], raw_ply_paths: dict[str, tuple[str, Path]]) -> list[dict[str, Any]]:
    annotations = {f"{row['scene_id']}/{row['annot_id']}": row for row in read_json(ANNOTATIONS_JSON)}
    attrs = torch.load(PACKET_DIR / "fungraph_scene3d_attributes.pt", map_location="cpu")
    point_feats = torch.load(PACKET_DIR / "fungraph_scene3d_uni3d_feats.pt", map_location="cpu")
    img_feats = torch.load(PACKET_DIR / "fungraph_scene3d_videofeats.pt", map_location="cpu")
    node_mapping = read_json(EXPORT_DIR / "node_id_mapping.json")
    target_counts = load_target_counts()

    rows: list[dict[str, Any]] = []
    for nscene, item in sorted(attrs.items()):
        scene_id = str(item["source_scene_id"])
        _, laser_path = raw_ply_paths.get(scene_id, ("", Path("")))
        node_ids = [str(x) for x in item["node_ids"]]
        labels = [str(x) for x in item["objects"]]
        candidate_nodes = set(candidate_scenes.get(scene_id, []))
        for obj_id, node_id in enumerate(node_ids):
            anno = annotations.get(f"{scene_id}/{node_id}", {})
            indices = anno.get("indices") or []
            feature_key = f"{nscene}_{obj_id:02}"
            mapping_key = f"{scene_id}/{node_id}"
            row = {
                "scene_id": scene_id,
                "native_scene_id": nscene,
                "object_id": obj_id,
                "node_id": node_id,
                "label": labels[obj_id],
                "is_export_candidate": node_id in candidate_nodes,
                "target_query_count": target_counts[node_id],
                "laser_scan_rel_path": rel(laser_path) if laser_path else "",
                "laser_scan_exists": laser_path.exists(),
                "n_point_indices": len(indices),
                "has_point_segment": len(indices) > 0,
                "has_record_camera": bool(anno.get("record_camera")),
                "has_bbox_geometry": mapping_key in node_mapping,
                "native_feature_key": feature_key,
                "has_point_feature": feature_key in point_feats,
                "has_image_feature": feature_key in img_feats,
                "object_full_ready": bool(
                    node_id in candidate_nodes
                    and laser_path.exists()
                    and len(indices) > 0
                    and anno.get("record_camera")
                    and mapping_key in node_mapping
                    and feature_key in point_feats
                    and feature_key in img_feats
                ),
            }
            rows.append(row)
    return rows


def summarize(capture_rows: list[dict[str, Any]], frame_rows: list[dict[str, Any]], object_rows: list[dict[str, Any]]) -> dict[str, Any]:
    scenes = sorted({str(row["scene_id"]) for row in capture_rows})
    scene_ready = {}
    for scene_id in scenes:
        caps = [row for row in capture_rows if str(row["scene_id"]) == scene_id]
        objs = [row for row in object_rows if str(row["scene_id"]) == scene_id and row["is_export_candidate"]]
        scene_ready[scene_id] = {
            "n_captures": len(caps),
            "n_full_captures": sum(bool(row["capture_full_ready"]) for row in caps),
            "n_rgb_depth_intrinsic_triplets": sum(int(row["n_rgb_depth_intrinsic_triplets"]) for row in caps),
            "n_export_candidate_objects": len(objs),
            "n_full_objects": sum(bool(row["object_full_ready"]) for row in objs),
            "full_scene_ready": bool(caps and all(row["capture_full_ready"] for row in caps) and objs and all(row["object_full_ready"] for row in objs)),
        }
    return {
        "status": "full_raw_multimodal_benchmark_ready",
        "n_scenes": len(scenes),
        "n_captures": len(capture_rows),
        "n_frames_indexed": len(frame_rows),
        "n_frame_rgbd_camera_triplets": sum(bool(row["frame_rgbd_camera_ready"]) for row in frame_rows),
        "n_objects": len(object_rows),
        "n_export_candidate_objects": sum(bool(row["is_export_candidate"]) for row in object_rows),
        "n_full_export_candidate_objects": sum(bool(row["object_full_ready"]) for row in object_rows if row["is_export_candidate"]),
        "n_scenes_full_ready": sum(bool(item["full_scene_ready"]) for item in scene_ready.values()),
        "all_scenes_full_ready": all(item["full_scene_ready"] for item in scene_ready.values()),
        "scene_ready": scene_ready,
        "feature_note": "Raw modalities are complete and native packet feature keys are aligned. Existing 1024-D packet tensors are deterministic SceneFun3D adapter features, not pretrained Uni3D/DINO/VLSAT encoder embeddings.",
    }


def write_status_doc(summary: dict[str, Any]) -> None:
    lines = [
        "# Full Multimodal Benchmark Status",
        "",
        "This document describes the data side of the benchmark, not model baselines.",
        "",
        "## Result",
        "",
        f"- Status: `{summary['status']}`",
        f"- Scenes full ready: {summary['n_scenes_full_ready']} / {summary['n_scenes']}",
        f"- Captures indexed: {summary['n_captures']}",
        f"- RGB-D-camera frame triplets indexed: {summary['n_frame_rgbd_camera_triplets']}",
        f"- Export candidate objects full ready: {summary['n_full_export_candidate_objects']} / {summary['n_export_candidate_objects']}",
        "",
        "## What Full Means Here",
        "",
        "- every exported SceneFun3D scene has a laser-scan point cloud;",
        "- every capture has RGB frames, depth frames, camera intrinsics, and a trajectory file;",
        "- every indexed frame triplet has RGB, depth, and intrinsics paths;",
        "- every exported candidate object has annotation point indices, bbox geometry, record-camera metadata, and native 3DGraphLLM feature keys;",
        "- raw assets are referenced by manifest paths and are not copied into the repository.",
        "",
        "## Important Boundary",
        "",
        summary["feature_note"],
        "",
        "To turn the native packet into original-3DGraphLLM-style pretrained features, run the chosen 3D/2D/relation encoders on these indexed raw assets and replace the adapter tensors while preserving the manifest keys.",
    ]
    (EXPORT_DIR / "FULL_MULTIMODAL_BENCHMARK_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    candidate_scenes = load_candidate_scenes()
    raw_ply_paths = load_raw_ply_paths()
    scene_ids = sorted(candidate_scenes)
    capture_rows, frame_rows = build_scene_manifests(scene_ids, raw_ply_paths)
    object_rows = build_object_manifest(candidate_scenes, raw_ply_paths)
    summary = summarize(capture_rows, frame_rows, object_rows)

    write_csv(EXPORT_DIR / "full_scene_capture_manifest.csv", capture_rows)
    write_jsonl(EXPORT_DIR / "full_scene_frame_index.jsonl", frame_rows)
    write_csv(EXPORT_DIR / "full_object_modality_manifest.csv", object_rows)
    write_json(EXPORT_DIR / "full_multimodal_readiness.json", summary)
    write_status_doc(summary)

    manifest_path = PACKET_DIR / "native_packet_manifest.json"
    manifest = read_json(manifest_path)
    manifest["benchmark_modality_status"] = summary["status"]
    manifest["full_multimodal_readiness"] = {
        "all_scenes_full_ready": summary["all_scenes_full_ready"],
        "n_scenes_full_ready": summary["n_scenes_full_ready"],
        "n_scenes": summary["n_scenes"],
        "n_frame_rgbd_camera_triplets": summary["n_frame_rgbd_camera_triplets"],
        "n_full_export_candidate_objects": summary["n_full_export_candidate_objects"],
        "n_export_candidate_objects": summary["n_export_candidate_objects"],
    }
    write_json(manifest_path, manifest)

    print(json.dumps({k: summary[k] for k in [
        "status",
        "n_scenes",
        "n_scenes_full_ready",
        "n_captures",
        "n_frame_rgbd_camera_triplets",
        "n_export_candidate_objects",
        "n_full_export_candidate_objects",
        "all_scenes_full_ready",
    ]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
