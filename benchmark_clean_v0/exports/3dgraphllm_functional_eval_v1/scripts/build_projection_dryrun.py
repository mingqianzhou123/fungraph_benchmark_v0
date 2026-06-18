#!/usr/bin/env python3
"""Build a relation-level projection dry-run index.

This is a benchmark data utility, not a baseline. It projects GT target/anchor
point segments into candidate RGB-D camera frames and records placeholder
co-visibility metadata. It deliberately does not produce official crops: the
selection thresholds are not frozen and depth z-test is not applied yet.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

EXPORT_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = EXPORT_DIR.parents[1]
EVIDENCE_DIR = EXPORT_DIR / "relation_conditioned_evidence"
SCENEFUN_ROOT = Path("/home/mz560/3D scene graph project/SceneFun3D_Graph/SceneFun3D_Graph")
ANNOTATIONS_JSON = BENCHMARK_ROOT / "annotations" / "openfungraph" / "SceneFun3D.annotations.json"
RAW_ASSET_MANIFEST = BENCHMARK_ROOT / "raw_assets" / "scenefun3d_raw_asset_manifest.csv"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_raw_ply_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    with RAW_ASSET_MANIFEST.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("asset_type") != "laser_scan_ply" or not row.get("scene_id"):
                continue
            source = Path(row["source_path"])
            suffix = Path(*source.parts[2:]) if len(source.parts) > 2 else source
            paths[str(row["scene_id"])] = SCENEFUN_ROOT / suffix
    return paths


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
    dtype = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("red", "u1"), ("green", "u1"), ("blue", "u1")])
    return np.memmap(path, dtype=dtype, mode="r", offset=offset, shape=(n_vertices,))


def points_for_node(verts: np.ndarray, indices: list[int], max_points: int) -> np.ndarray:
    idx = np.asarray(indices or [], dtype=np.int64)
    idx = idx[(idx >= 0) & (idx < len(verts))]
    if max_points and len(idx) > max_points:
        step = max(1, len(idx) // max_points)
        idx = idx[::step][:max_points]
    if len(idx) == 0:
        return np.zeros((0, 3), dtype=np.float32)
    return np.column_stack([verts["x"][idx], verts["y"][idx], verts["z"][idx]]).astype(np.float32)


def parse_intrinsics(path: Path) -> dict[str, float]:
    values = [float(x) for x in path.read_text(encoding="utf-8").strip().split()]
    if len(values) < 6:
        raise ValueError(f"Expected 6 intrinsics values in {path}")
    width, height, fx, fy, cx, cy = values[:6]
    return {"width": width, "height": height, "fx": fx, "fy": fy, "cx": cx, "cy": cy}


def rodrigues(rotvec: np.ndarray) -> np.ndarray:
    theta = float(np.linalg.norm(rotvec))
    if theta < 1e-9:
        return np.eye(3, dtype=np.float64)
    axis = rotvec.astype(np.float64) / theta
    x, y, z = axis
    k = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]], dtype=np.float64)
    return np.eye(3, dtype=np.float64) + math.sin(theta) * k + (1.0 - math.cos(theta)) * (k @ k)


def load_trajectory(path: Path) -> list[dict[str, Any]]:
    poses = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = [float(x) for x in line.strip().split()]
            if len(parts) < 7:
                continue
            t = np.array(parts[1:4], dtype=np.float64)
            r = rodrigues(np.array(parts[4:7], dtype=np.float64))
            cam_to_world = np.eye(4, dtype=np.float64)
            cam_to_world[:3, :3] = r
            cam_to_world[:3, 3] = t
            poses.append({"timestamp": parts[0], "cam_to_world": cam_to_world})
    if not poses:
        raise ValueError(f"No poses in trajectory: {path}")
    return poses


def nearest_pose(poses: list[dict[str, Any]], timestamp: float) -> dict[str, Any]:
    return min(poses, key=lambda p: abs(float(p["timestamp"]) - timestamp))


def frame_timestamp(frame_stem: str) -> float:
    return float(str(frame_stem).split("_")[-1])


def scene_capture_root(frame: dict[str, Any]) -> Path:
    split = frame_split(frame)
    return SCENEFUN_ROOT / split / str(frame["scene_id"]) / str(frame["capture_id"])


def frame_split(frame: dict[str, Any]) -> str:
    return str(frame.get("split") or str(frame["rgb_rel_path"]).split("/", 1)[0])


def project_points(points_laser: np.ndarray, laser_to_world: np.ndarray, cam_to_world: np.ndarray, intr: dict[str, float]) -> dict[str, Any]:
    if len(points_laser) == 0:
        return empty_projection("no_points")
    pts_h = np.concatenate([points_laser.astype(np.float64), np.ones((len(points_laser), 1), dtype=np.float64)], axis=1)
    pts_world = (laser_to_world @ pts_h.T).T
    world_to_cam = np.linalg.inv(cam_to_world)
    pts_cam = (world_to_cam @ pts_world.T).T[:, :3]

    # ARKit camera coordinates look down negative z, with y up. Convert to a
    # conventional image plane for a placeholder dry-run.
    depth = -pts_cam[:, 2]
    valid_depth = depth > 1e-5
    if not np.any(valid_depth):
        return empty_projection("behind_camera")
    pts = pts_cam[valid_depth]
    depth = depth[valid_depth]
    u = intr["fx"] * (pts[:, 0] / depth) + intr["cx"]
    v = intr["cy"] - intr["fy"] * (pts[:, 1] / depth)
    in_bounds = (u >= 0) & (u < intr["width"]) & (v >= 0) & (v < intr["height"])
    if not np.any(in_bounds):
        return {
            **empty_projection("outside_frame"),
            "n_projected_depth_positive": int(len(depth)),
            "projected_fraction_depth_positive": round(float(len(depth) / len(points_laser)), 6),
        }
    ui = u[in_bounds]
    vi = v[in_bounds]
    di = depth[in_bounds]
    bbox = [float(ui.min()), float(vi.min()), float(ui.max()), float(vi.max())]
    area = max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])
    return {
        "projection_status": "projected_in_frame",
        "failure_reason": "",
        "n_points_total": int(len(points_laser)),
        "n_projected_depth_positive": int(len(depth)),
        "n_projected_in_frame": int(len(ui)),
        "projected_fraction_depth_positive": round(float(len(depth) / len(points_laser)), 6),
        "projected_fraction_in_frame": round(float(len(ui) / len(points_laser)), 6),
        "bbox_xyxy": [round(x, 3) for x in bbox],
        "bbox_area_px": round(float(area), 3),
        "median_depth": round(float(np.median(di)), 6),
    }


def empty_projection(reason: str) -> dict[str, Any]:
    return {
        "projection_status": "not_projected",
        "failure_reason": reason,
        "n_points_total": 0,
        "n_projected_depth_positive": 0,
        "n_projected_in_frame": 0,
        "projected_fraction_depth_positive": 0.0,
        "projected_fraction_in_frame": 0.0,
        "bbox_xyxy": None,
        "bbox_area_px": 0.0,
        "median_depth": None,
    }


def load_frames_by_key() -> dict[str, dict[str, Any]]:
    rows = {}
    for row in read_jsonl(EVIDENCE_DIR / "relation_frame_candidates.jsonl"):
        rows[str(row["frame_key"])] = row
    return rows


def build_projection_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    annotations = {f"{row['scene_id']}/{row['annot_id']}": row for row in read_json(ANNOTATIONS_JSON)}
    ply_paths = load_raw_ply_paths()
    frames_by_key = load_frames_by_key()
    relations = list(read_jsonl(EVIDENCE_DIR / "relation_evidence_index.jsonl"))
    if args.limit_relations:
        relations = relations[: args.limit_relations]

    scene_cache: dict[str, np.ndarray] = {}
    node_points_cache: dict[tuple[str, str], np.ndarray] = {}
    transform_cache: dict[tuple[str, str, str], np.ndarray] = {}
    traj_cache: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    intr_cache: dict[str, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []

    for relation in relations:
        scene_id = str(relation["scene_id"])
        if scene_id not in scene_cache:
            scene_cache[scene_id] = parse_ply_vertices(ply_paths[scene_id])
        verts = scene_cache[scene_id]
        node_ids = [str(relation["target_node_id"])]
        if not relation.get("anchor_missing"):
            node_ids.append(str(relation["anchor_node_id"]))
        for node_id in node_ids:
            key = (scene_id, node_id)
            if key not in node_points_cache:
                anno = annotations.get(f"{scene_id}/{node_id}", {})
                node_points_cache[key] = points_for_node(verts, anno.get("indices") or [], args.max_points_per_object)

        for frame_key in relation["candidate_frame_keys"]:
            frame = frames_by_key[frame_key]
            root = scene_capture_root(frame)
            split = frame_split(frame)
            cache_key = (split, scene_id, str(frame["capture_id"]))
            if cache_key not in transform_cache:
                transform_cache[cache_key] = np.load(root / f"{frame['capture_id']}_refined_transform.npy")
            if cache_key not in traj_cache:
                traj_cache[cache_key] = load_trajectory(root / "lowres_wide.traj")
            intr_path = SCENEFUN_ROOT / str(frame["intrinsics_rel_path"])
            if str(intr_path) not in intr_cache:
                intr_cache[str(intr_path)] = parse_intrinsics(intr_path)

            timestamp = frame_timestamp(str(frame["frame_stem"]))
            pose = nearest_pose(traj_cache[cache_key], timestamp)
            target_proj = project_points(
                node_points_cache[(scene_id, str(relation["target_node_id"]))],
                transform_cache[cache_key],
                pose["cam_to_world"],
                intr_cache[str(intr_path)],
            )
            if relation.get("anchor_missing"):
                anchor_proj = empty_projection("anchor_missing")
            else:
                anchor_proj = project_points(
                    node_points_cache[(scene_id, str(relation["anchor_node_id"]))],
                    transform_cache[cache_key],
                    pose["cam_to_world"],
                    intr_cache[str(intr_path)],
                )
            target_visible = target_proj["n_projected_in_frame"] >= args.min_visible_points
            anchor_visible = relation.get("anchor_missing") or anchor_proj["n_projected_in_frame"] >= args.min_visible_points
            rows.append(
                {
                    "relation_key": relation["relation_key"],
                    "relation_dir": relation["relation_dir"],
                    "query_id": relation["query_id"],
                    "export_split": relation["export_split"],
                    "scene_id": scene_id,
                    "target_node_id": relation["target_node_id"],
                    "anchor_node_id": relation["anchor_node_id"],
                    "anchor_missing": relation["anchor_missing"],
                    "frame_key": frame_key,
                    "capture_id": frame["capture_id"],
                    "frame_stem": frame["frame_stem"],
                    "rgb_rel_path": frame["rgb_rel_path"],
                    "depth_rel_path": frame["depth_rel_path"],
                    "intrinsics_rel_path": frame["intrinsics_rel_path"],
                    "trajectory_rel_path": str(Path(split) / scene_id / str(frame["capture_id"]) / "lowres_wide.traj"),
                    "refined_transform_rel_path": str(Path(split) / scene_id / str(frame["capture_id"]) / f"{frame['capture_id']}_refined_transform.npy"),
                    "nearest_pose_timestamp": round(float(pose["timestamp"]), 6),
                    "frame_pose_time_delta": round(abs(float(pose["timestamp"]) - timestamp), 6),
                    "target_projection": target_proj,
                    "anchor_projection": anchor_proj,
                    "target_visible_placeholder": bool(target_visible),
                    "anchor_visible_placeholder": bool(anchor_visible),
                    "co_visible_placeholder": bool(target_visible and anchor_visible),
                    "min_visible_points_placeholder": args.min_visible_points,
                    "depth_z_test_applied": False,
                    "selection_rule_version": "placeholder_dryrun_arkit_negative_z_no_depth_ztest_v1",
                    "is_placeholder_rule": True,
                    "coordinate_frame": "laser_scan_points -> refined_transform.npy -> ARKit world -> nearest lowres_wide.traj camera pose -> wide_intrinsics",
                    "pose_convention_assumption": "lowres_wide.traj stores ARKit camera-to-world pose as translation plus rotation vector; camera forward is negative z",
                }
            )
    summary = summarize(rows, len(relations), args)
    return rows, summary


def summarize(rows: list[dict[str, Any]], n_relations: int, args: argparse.Namespace) -> dict[str, Any]:
    relation_has_cov = defaultdict(bool)
    relation_counts = defaultdict(int)
    split_counts: Counter[str] = Counter()
    split_cov: Counter[str] = Counter()
    for row in rows:
        key = str(row["relation_key"])
        relation_counts[key] += 1
        if row["co_visible_placeholder"]:
            relation_has_cov[key] = True
        split_counts[str(row["export_split"])] += 1
    relation_split = {}
    for row in rows:
        relation_split[str(row["relation_key"])] = str(row["export_split"])
    for key, ok in relation_has_cov.items():
        if ok:
            split_cov[relation_split[key]] += 1
    split_rel_counts = Counter(relation_split.values())
    return {
        "status": "projection_dryrun_placeholder_ready",
        "n_relations": n_relations,
        "n_projection_rows": len(rows),
        "n_relations_with_placeholder_coview": sum(bool(v) for v in relation_has_cov.values()),
        "n_relations_without_placeholder_coview": n_relations - sum(bool(v) for v in relation_has_cov.values()),
        "n_rows_with_placeholder_coview": sum(bool(row["co_visible_placeholder"]) for row in rows),
        "min_visible_points_placeholder": args.min_visible_points,
        "max_points_per_object": args.max_points_per_object,
        "depth_z_test_applied": False,
        "selection_rule_version": "placeholder_dryrun_arkit_negative_z_no_depth_ztest_v1",
        "by_split": {
            split: {
                "n_relations": split_rel_counts[split],
                "n_projection_rows": split_counts[split],
                "n_relations_with_placeholder_coview": split_cov[split],
            }
            for split in sorted(split_rel_counts)
        },
        "important_boundary": "This is a placeholder dry-run projection index, not official crop evidence. Pose convention and visibility thresholds must be audited before using crops as benchmark evidence.",
    }


def write_status(summary: dict[str, Any]) -> None:
    lines = [
        "# Projection Dry-Run Status",
        "",
        "This directory records placeholder projection metadata for relation-conditioned evidence. It does not run baselines, does not extract encoder features, and does not create official benchmark crops.",
        "",
        "## Result",
        "",
        f"- Status: `{summary['status']}`",
        f"- Relations checked: {summary['n_relations']}",
        f"- Projection rows: {summary['n_projection_rows']}",
        f"- Relations with placeholder co-visible frame: {summary['n_relations_with_placeholder_coview']} / {summary['n_relations']}",
        f"- Frame rows with placeholder co-visibility: {summary['n_rows_with_placeholder_coview']}",
        "",
        "## Boundary",
        "",
        summary["important_boundary"],
        "",
        "Depth z-test is not applied. The rule is explicitly marked `is_placeholder_rule = true` in every row.",
    ]
    (EVIDENCE_DIR / "PROJECTION_DRYRUN_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-relations", type=int, default=0, help="Optional relation-row limit for smoke tests.")
    parser.add_argument("--max-points-per-object", type=int, default=5000)
    parser.add_argument("--min-visible-points", type=int, default=10)
    args = parser.parse_args()
    rows, summary = build_projection_rows(args)
    write_jsonl(EVIDENCE_DIR / "projection_dryrun_index.jsonl", rows)
    write_json(EVIDENCE_DIR / "projection_dryrun_summary.json", summary)
    write_status(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
