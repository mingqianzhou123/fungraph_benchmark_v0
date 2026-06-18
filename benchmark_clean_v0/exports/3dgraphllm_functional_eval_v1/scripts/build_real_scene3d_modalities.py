#!/usr/bin/env python3
"""Build real SceneFun3D modality tensors for the native 3DGraphLLM packet.

The original 3DGraphLLM checkpoint expects 1024-D object features, 1024-D
image/video features, and 512-D edge/GNN features. Without the original Uni3D
and video encoders for SceneFun3D, this script fills those slots with real,
deterministic features extracted from available SceneFun3D modalities:

- object point coordinates and RGB colors from laser-scan PLY + annotation
  point indices;
- object camera metadata from SceneFun3D annotations;
- scene RGB-D frame coverage and sampled frame statistics;
- relative geometry between k-nearest neighboring objects.

These are real modality features, but they are not Uni3D/video-network
embeddings. Treat them as a runnable benchmark adapter and modality-complete
baseline, not as a faithful reproduction of 3DGraphLLM's pretrained feature
distribution.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

EXPORT_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = EXPORT_DIR.parents[1]
PACKET_DIR = EXPORT_DIR / "native_3dgraphllm"

SCENEFUN_ROOT = Path("/home/mz560/3D scene graph project/SceneFun3D_Graph/SceneFun3D_Graph")
ANNOTATIONS_JSON = BENCHMARK_ROOT / "annotations" / "openfungraph" / "SceneFun3D.annotations.json"
RAW_ASSET_MANIFEST = BENCHMARK_ROOT / "raw_assets" / "scenefun3d_raw_asset_manifest.csv"


def native_scene_id(scene_id: str) -> str:
    return f"sf3d{scene_id}_00"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def parse_ply_vertices(path: Path) -> np.ndarray:
    with path.open("rb") as f:
        header_lines: list[bytes] = []
        while True:
            line = f.readline()
            if not line:
                raise ValueError(f"PLY header not terminated: {path}")
            header_lines.append(line)
            if line.strip() == b"end_header":
                break
        offset = f.tell()
    header = b"".join(header_lines).decode("ascii", errors="replace")
    if "format binary_little_endian 1.0" not in header:
        raise ValueError(f"Only binary_little_endian PLY is supported: {path}")
    n_vertices = None
    for line in header.splitlines():
        if line.startswith("element vertex "):
            n_vertices = int(line.split()[-1])
            break
    if n_vertices is None:
        raise ValueError(f"Missing vertex count in PLY: {path}")
    dtype = np.dtype(
        [
            ("x", "<f4"),
            ("y", "<f4"),
            ("z", "<f4"),
            ("red", "u1"),
            ("green", "u1"),
            ("blue", "u1"),
        ]
    )
    return np.memmap(path, dtype=dtype, mode="r", offset=offset, shape=(n_vertices,))


def load_raw_ply_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    with RAW_ASSET_MANIFEST.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("asset_type") != "laser_scan_ply" or not row.get("scene_id"):
                continue
            rel = Path(row["source_path"])
            suffix = Path(*rel.parts[2:]) if len(rel.parts) > 2 else rel
            path = SCENEFUN_ROOT / suffix
            paths[str(row["scene_id"])] = path
    return paths


def load_annotations() -> dict[str, dict[str, Any]]:
    rows = read_json(ANNOTATIONS_JSON)
    return {f"{row['scene_id']}/{row['annot_id']}": row for row in rows}


def load_native_order() -> dict[str, dict[str, Any]]:
    attrs = torch.load(PACKET_DIR / "fungraph_scene3d_attributes.pt", map_location="cpu")
    out: dict[str, dict[str, Any]] = {}
    for nscene, item in attrs.items():
        source_scene = str(item["source_scene_id"])
        out[source_scene] = {
            "native_scene_id": nscene,
            "node_ids": [str(x) for x in item["node_ids"]],
            "objects": [str(x) for x in item["objects"]],
            "locs": item["locs"].float(),
            "obj_ids": [int(x) for x in item["obj_ids"]],
        }
    return out


def finite_array(values: list[float] | np.ndarray, size: int) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32).reshape(-1)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    if arr.size == 0:
        arr = np.zeros(1, dtype=np.float32)
    if arr.size < size:
        reps = int(math.ceil(size / arr.size))
        arr = np.tile(arr, reps)
    return arr[:size].astype(np.float32)


def normalize_stats(values: np.ndarray) -> np.ndarray:
    values = np.nan_to_num(values.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    scale = np.max(np.abs(values))
    if scale > 0:
        values = values / scale
    return values


def point_feature(points: np.ndarray, colors: np.ndarray, loc: np.ndarray, label: str) -> np.ndarray:
    if len(points) == 0:
        stats = np.zeros(64, dtype=np.float32)
    else:
        xyz = points.astype(np.float32)
        rgb = colors.astype(np.float32) / 255.0
        center = xyz.mean(axis=0)
        centered = xyz - center
        cov_diag = centered.std(axis=0)
        quantiles = np.quantile(xyz, [0.05, 0.25, 0.5, 0.75, 0.95], axis=0).reshape(-1)
        rgb_stats = np.concatenate([rgb.mean(axis=0), rgb.std(axis=0), rgb.min(axis=0), rgb.max(axis=0)])
        radial = np.linalg.norm(centered, axis=1)
        radial_stats = np.array([radial.mean(), radial.std(), radial.min(), radial.max()], dtype=np.float32)
        stats = np.concatenate(
            [
                np.array([len(points), math.log1p(len(points))], dtype=np.float32),
                center,
                cov_diag,
                xyz.min(axis=0),
                xyz.max(axis=0),
                loc.astype(np.float32),
                quantiles.astype(np.float32),
                rgb_stats.astype(np.float32),
                radial_stats,
                np.frombuffer(label.encode("utf-8"), dtype=np.uint8).astype(np.float32)[:16] / 255.0,
            ]
        )
    stats = normalize_stats(stats)
    trig = np.concatenate([stats, np.sin(stats * np.pi), np.cos(stats * np.pi), stats**2])
    return finite_array(trig, 1024)


def camera_feature(record_camera: dict[str, Any] | None, scene_rgbd_stats: np.ndarray, loc: np.ndarray) -> np.ndarray:
    cam_values: list[float] = []
    if record_camera:
        for key in ["matrixWorld", "dof", "lookat", "center"]:
            val = record_camera.get(key, [])
            if isinstance(val, list):
                cam_values.extend(float(x) for x in val if isinstance(x, (int, float)))
    stats = np.concatenate([np.asarray(cam_values, dtype=np.float32), scene_rgbd_stats, loc.astype(np.float32)])
    stats = normalize_stats(stats)
    trig = np.concatenate([stats, np.sin(stats), np.cos(stats), stats**2])
    return finite_array(trig, 1024)


def edge_feature(src_loc: np.ndarray, dst_loc: np.ndarray, src_label: str, dst_label: str) -> np.ndarray:
    src_center, src_size = src_loc[:3], src_loc[3:]
    dst_center, dst_size = dst_loc[:3], dst_loc[3:]
    delta = dst_center - src_center
    dist = np.linalg.norm(delta)
    ratios = dst_size / np.maximum(src_size, 1e-6)
    label_bits = np.frombuffer(f"{src_label}->{dst_label}".encode("utf-8"), dtype=np.uint8).astype(np.float32) / 255.0
    stats = np.concatenate([delta, np.array([dist], dtype=np.float32), src_size, dst_size, ratios, label_bits[:32]])
    stats = normalize_stats(stats)
    trig = np.concatenate([stats, np.sin(stats * np.pi), np.cos(stats * np.pi), stats**2])
    return finite_array(trig, 512)


def sample_image_stats(paths: list[Path], max_files: int = 6) -> np.ndarray:
    if Image is None or not paths:
        return np.zeros(12, dtype=np.float32)
    selected = []
    if len(paths) <= max_files:
        selected = paths
    else:
        idxs = np.linspace(0, len(paths) - 1, max_files).round().astype(int)
        selected = [paths[int(i)] for i in idxs]
    means: list[np.ndarray] = []
    stds: list[np.ndarray] = []
    for path in selected:
        try:
            arr = np.asarray(Image.open(path))
        except Exception:
            continue
        if arr.ndim == 2:
            arr = arr[..., None]
        arr = arr.astype(np.float32)
        if arr.max() > 0:
            arr = arr / arr.max()
        flat = arr.reshape(-1, arr.shape[-1])
        means.append(flat.mean(axis=0)[:3])
        stds.append(flat.std(axis=0)[:3])
    if not means:
        return np.zeros(12, dtype=np.float32)
    mean = np.mean(np.stack([finite_array(x, 3) for x in means]), axis=0)
    std = np.mean(np.stack([finite_array(x, 3) for x in stds]), axis=0)
    return finite_array(np.concatenate([mean, std]), 12)


def scene_rgbd_summary(scene_id: str, scenefun_root: Path) -> tuple[np.ndarray, dict[str, Any]]:
    scene_dirs = list((scenefun_root / "dev" / scene_id).glob("*")) + list((scenefun_root / "test" / scene_id).glob("*"))
    capture_dirs = [p for p in scene_dirs if p.is_dir()]
    wide_paths: list[Path] = []
    depth_paths: list[Path] = []
    traj_count = 0
    for cap in capture_dirs:
        wide_paths.extend(sorted((cap / "wide").glob("*.png")))
        wide_paths.extend(sorted((cap / "lowres_wide").glob("*.png")))
        depth_paths.extend(sorted((cap / "highres_depth").glob("*.png")))
        depth_paths.extend(sorted((cap / "lowres_depth").glob("*.png")))
        traj_count += len(list(cap.glob("*.traj"))) + len(list(cap.glob("*poses*.traj")))
    rgb_stats = sample_image_stats(wide_paths)
    depth_stats = sample_image_stats(depth_paths)
    counts = np.array([len(capture_dirs), len(wide_paths), len(depth_paths), traj_count], dtype=np.float32)
    feature = finite_array(normalize_stats(np.concatenate([counts, rgb_stats, depth_stats])), 64)
    manifest = {
        "scene_id": scene_id,
        "n_capture_dirs": len(capture_dirs),
        "n_wide_frames": len(wide_paths),
        "n_depth_frames": len(depth_paths),
        "n_traj_files": traj_count,
        "has_rgb": len(wide_paths) > 0,
        "has_depth": len(depth_paths) > 0,
        "has_camera_trajectory": traj_count > 0,
    }
    return feature, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenefun-root", type=Path, default=SCENEFUN_ROOT)
    parser.add_argument("--packet-dir", type=Path, default=PACKET_DIR)
    args = parser.parse_args()

    annotations = load_annotations()
    raw_ply_paths = load_raw_ply_paths()
    native_order = load_native_order()

    point_feats: dict[str, torch.Tensor] = {}
    img_feats: dict[str, torch.Tensor] = {}
    gnn_feats: dict[str, torch.Tensor] = {}
    object_rows: list[dict[str, Any]] = []
    scene_rows: list[dict[str, Any]] = []

    for scene_id, scene in sorted(native_order.items()):
        ply_path = raw_ply_paths.get(scene_id)
        if ply_path is None or not ply_path.exists():
            raise FileNotFoundError(f"Missing PLY for scene {scene_id}: {ply_path}")
        vertices = parse_ply_vertices(ply_path)
        scene_rgbd_feat, scene_manifest = scene_rgbd_summary(scene_id, args.scenefun_root)
        scene_rows.append(scene_manifest)

        locs = scene["locs"].numpy()
        labels = scene["objects"]
        node_ids = scene["node_ids"]
        nscene = scene["native_scene_id"]

        for obj_id, node_id in enumerate(node_ids):
            anno = annotations.get(f"{scene_id}/{node_id}", {})
            indices = np.asarray(anno.get("indices", []), dtype=np.int64)
            valid = indices[(indices >= 0) & (indices < len(vertices))]
            pts = np.column_stack([vertices["x"][valid], vertices["y"][valid], vertices["z"][valid]]) if len(valid) else np.zeros((0, 3), dtype=np.float32)
            rgb = np.column_stack([vertices["red"][valid], vertices["green"][valid], vertices["blue"][valid]]) if len(valid) else np.zeros((0, 3), dtype=np.uint8)
            item_key = f"{nscene}_{obj_id:02}"
            point_feats[item_key] = torch.tensor(point_feature(pts, rgb, locs[obj_id], labels[obj_id]), dtype=torch.float32)
            img_feats[item_key] = torch.tensor(camera_feature(anno.get("record_camera"), scene_rgbd_feat, locs[obj_id]), dtype=torch.float32)
            object_rows.append(
                {
                    "scene_id": scene_id,
                    "native_scene_id": nscene,
                    "node_id": node_id,
                    "object_id": obj_id,
                    "label": labels[obj_id],
                    "n_annotation_indices": len(indices),
                    "n_valid_points": len(valid),
                    "has_point_xyz": len(valid) > 0,
                    "has_point_rgb": len(valid) > 0,
                    "has_record_camera": bool(anno.get("record_camera")),
                    "feature_key": item_key,
                }
            )

        centers = locs[:, :3]
        edge_rows: list[torch.Tensor] = []
        for obj_id in range(len(node_ids)):
            dists = np.linalg.norm(centers - centers[obj_id], axis=1)
            order = [int(i) for i in np.argsort(dists) if int(i) != obj_id]
            while len(order) < 2:
                order.append(obj_id)
            for nbr_id in order[:2]:
                edge_rows.append(torch.tensor(edge_feature(locs[obj_id], locs[nbr_id], labels[obj_id], labels[nbr_id]), dtype=torch.float32))
        gnn_feats[nscene] = torch.stack(edge_rows, dim=0) if edge_rows else torch.zeros((0, 512), dtype=torch.float32)

    torch.save(point_feats, args.packet_dir / "fungraph_scene3d_uni3d_feats.pt")
    torch.save(img_feats, args.packet_dir / "fungraph_scene3d_videofeats.pt")
    torch.save(gnn_feats, args.packet_dir / "fungraph_scene3d_gnn_feats.pt")

    with (EXPORT_DIR / "object_modality_manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(object_rows[0]))
        writer.writeheader()
        writer.writerows(object_rows)
    with (EXPORT_DIR / "scene_rgbd_manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(scene_rows[0]))
        writer.writeheader()
        writer.writerows(scene_rows)

    manifest_path = args.packet_dir / "native_packet_manifest.json"
    manifest = read_json(manifest_path)
    manifest["status"] = "full_scene3d_multimodal_adapter_ready_not_pretrained_encoder_features"
    manifest["feature_provenance"] = {
        "attributes": "SceneFun3D graph node 3D bounding boxes",
        "uni3d_feats": "1024-D real point/color/statistical object features from laser-scan PLY and annotation point indices; not pretrained Uni3D embeddings",
        "videofeats": "1024-D real RGB-D/camera statistical features from SceneFun3D image/depth frame coverage and annotation camera metadata; not pretrained video-network embeddings",
        "gnn_feats": "512-D real relative-geometry kNN edge features from SceneFun3D object boxes",
    }
    manifest["modality_counts"] = {
        "objects": len(object_rows),
        "scenes": len(scene_rows),
        "objects_with_points": sum(row["has_point_xyz"] for row in object_rows),
        "objects_with_record_camera": sum(row["has_record_camera"] for row in object_rows),
        "scenes_with_rgb": sum(row["has_rgb"] for row in scene_rows),
        "scenes_with_depth": sum(row["has_depth"] for row in scene_rows),
    }
    manifest["scientific_caveat"] = "These tensors are real SceneFun3D modality features but are not distribution-matched Uni3D/video embeddings used by the original 3DGraphLLM checkpoint."
    write_json(manifest_path, manifest)

    print("Wrote real SceneFun3D modality tensors")
    print(json.dumps(manifest["modality_counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
