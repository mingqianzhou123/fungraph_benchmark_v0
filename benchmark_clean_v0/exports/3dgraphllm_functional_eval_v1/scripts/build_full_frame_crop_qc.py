#!/usr/bin/env python3
"""Mine full-scene RGB-D frames for relation-conditioned crop evidence.

This script upgrades the sparse projection dry-run into a stronger benchmark
construction pass: for each relation it scans every RGB-D-camera frame in the
scene with a fast geometric prefilter, depth-tests the top candidates, selects
frozen top-K co-visible views, writes local crops, and emits QC metadata.

It does not run baselines or learned feature extraction.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_projection_dryrun import (  # noqa: E402
    ANNOTATIONS_JSON,
    EVIDENCE_DIR,
    SCENEFUN_ROOT,
    frame_split,
    frame_timestamp,
    load_raw_ply_paths,
    load_trajectory,
    nearest_pose,
    parse_intrinsics,
    parse_ply_vertices,
    points_for_node,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)

RULE_VERSION = "covisible_depth_ztest_v1_20260618_full_frame_mining"
DEPTH_SCALE_M = 1000.0
DEPTH_TOLERANCE_M = 0.15
TARGET_MIN_Z_VISIBLE = 5
ANCHOR_MIN_Z_VISIBLE = 20
TARGET_MIN_Z_FRACTION = 0.10
ANCHOR_MIN_Z_FRACTION = 0.03
MIN_BBOX_AREA_PX = 16.0
TOP_K = 3
PREFILTER_TOP_N = 24
PREFILTER_POINTS = 750
ZTEST_POINTS = 5000


def load_all_frames_by_scene() -> dict[str, list[dict[str, Any]]]:
    by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(EVIDENCE_DIR.parent / "full_scene_frame_index.jsonl"):
        if row.get("frame_rgbd_camera_ready"):
            out = dict(row)
            out["frame_key"] = f"{row['scene_id']}|{row['capture_id']}|{row['frame_stem']}"
            by_scene[str(row["scene_id"])].append(out)
    for scene_id in by_scene:
        by_scene[scene_id] = sorted(by_scene[scene_id], key=lambda r: (str(r["capture_id"]), str(r["frame_stem"])))
    return by_scene


def load_depth(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path)).astype(np.float32) / DEPTH_SCALE_M


def frame_root(frame: dict[str, Any]) -> Path:
    return SCENEFUN_ROOT / frame_split(frame) / str(frame["scene_id"]) / str(frame["capture_id"])


def round_box(box: list[float] | None) -> list[float] | None:
    return None if box is None else [round(float(x), 3) for x in box]


def box_area(box: list[float] | None) -> float:
    if box is None:
        return 0.0
    return max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))


def bbox_xyxy(u: np.ndarray, v: np.ndarray) -> list[float]:
    return [float(u.min()), float(v.min()), float(u.max()), float(v.max())]


def empty_projection(reason: str) -> dict[str, Any]:
    return {
        "projection_status": "not_projected",
        "failure_reason": reason,
        "n_points_total": 0,
        "n_projected_depth_positive": 0,
        "n_projected_in_frame": 0,
        "n_depth_pixels_valid": 0,
        "n_ztest_visible": 0,
        "projected_fraction_depth_positive": 0.0,
        "projected_fraction_in_frame": 0.0,
        "ztest_visible_fraction_total": 0.0,
        "ztest_visible_fraction_in_frame": 0.0,
        "bbox_xyxy": None,
        "bbox_area_px": 0.0,
        "ztest_bbox_xyxy": None,
        "ztest_bbox_area_px": 0.0,
        "median_projected_depth": None,
        "median_ztest_depth": None,
    }


def project_points(
    points_laser: np.ndarray,
    laser_to_world: np.ndarray,
    cam_to_world: np.ndarray,
    intr: dict[str, float],
    depth_m: np.ndarray | None = None,
) -> dict[str, Any]:
    if len(points_laser) == 0:
        return empty_projection("no_points")
    pts_h = np.concatenate([points_laser.astype(np.float64), np.ones((len(points_laser), 1), dtype=np.float64)], axis=1)
    pts_world = (laser_to_world @ pts_h.T).T
    pts_cam = (np.linalg.inv(cam_to_world) @ pts_world.T).T[:, :3]
    depth = -pts_cam[:, 2]
    valid_depth = depth > 1e-5
    if not np.any(valid_depth):
        return empty_projection("behind_camera")
    pts = pts_cam[valid_depth]
    depth = depth[valid_depth]
    u = intr["fx"] * (pts[:, 0] / depth) + intr["cx"]
    v = intr["cy"] - intr["fy"] * (pts[:, 1] / depth)
    width = int(intr["width"])
    height = int(intr["height"])
    in_bounds = (u >= 0) & (u < width) & (v >= 0) & (v < height)
    if not np.any(in_bounds):
        out = empty_projection("outside_frame")
        out.update({
            "n_points_total": int(len(points_laser)),
            "n_projected_depth_positive": int(len(depth)),
            "projected_fraction_depth_positive": round(float(len(depth) / len(points_laser)), 6),
        })
        return out

    ui = u[in_bounds]
    vi = v[in_bounds]
    di = depth[in_bounds]
    bbox = bbox_xyxy(ui, vi)
    out = empty_projection("")
    out.update({
        "projection_status": "projected_in_frame",
        "failure_reason": "",
        "n_points_total": int(len(points_laser)),
        "n_projected_depth_positive": int(len(depth)),
        "n_projected_in_frame": int(len(ui)),
        "projected_fraction_depth_positive": round(float(len(depth) / len(points_laser)), 6),
        "projected_fraction_in_frame": round(float(len(ui) / len(points_laser)), 6),
        "bbox_xyxy": round_box(bbox),
        "bbox_area_px": round(float(box_area(bbox)), 3),
        "median_projected_depth": round(float(np.median(di)), 6),
    })
    if depth_m is None:
        return out

    px = np.clip(np.rint(ui).astype(np.int64), 0, width - 1)
    py = np.clip(np.rint(vi).astype(np.int64), 0, height - 1)
    observed = depth_m[py, px]
    valid_observed = observed > 0
    z_visible = valid_observed & (di <= observed + DEPTH_TOLERANCE_M)
    if np.any(z_visible):
        zbox = bbox_xyxy(ui[z_visible], vi[z_visible])
        zmed = round(float(np.median(di[z_visible])), 6)
    else:
        zbox = None
        zmed = None
    out.update({
        "n_depth_pixels_valid": int(np.sum(valid_observed)),
        "n_ztest_visible": int(np.sum(z_visible)),
        "ztest_visible_fraction_total": round(float(np.sum(z_visible) / len(points_laser)), 6),
        "ztest_visible_fraction_in_frame": round(float(np.sum(z_visible) / len(ui)), 6),
        "ztest_bbox_xyxy": round_box(zbox),
        "ztest_bbox_area_px": round(float(box_area(zbox)), 3),
        "median_ztest_depth": zmed,
    })
    return out


def prefilter_score(target: dict[str, Any], anchor: dict[str, Any]) -> float:
    if target["n_projected_in_frame"] < TARGET_MIN_Z_VISIBLE or anchor["n_projected_in_frame"] < ANCHOR_MIN_Z_VISIBLE:
        return 0.0
    return round(
        min(target["projected_fraction_in_frame"], anchor["projected_fraction_in_frame"])
        + 0.0001 * min(target["n_projected_in_frame"], anchor["n_projected_in_frame"])
        + 0.0000001 * min(target["bbox_area_px"], anchor["bbox_area_px"]),
        8,
    )


def target_visible(stats: dict[str, Any]) -> bool:
    return (
        stats["n_ztest_visible"] >= TARGET_MIN_Z_VISIBLE
        and stats["ztest_visible_fraction_total"] >= TARGET_MIN_Z_FRACTION
        and stats["ztest_bbox_area_px"] >= MIN_BBOX_AREA_PX
    )


def anchor_visible(stats: dict[str, Any], anchor_missing: bool) -> bool:
    if anchor_missing:
        return False
    return (
        stats["n_ztest_visible"] >= ANCHOR_MIN_Z_VISIBLE
        and stats["ztest_visible_fraction_total"] >= ANCHOR_MIN_Z_FRACTION
        and stats["ztest_bbox_area_px"] >= MIN_BBOX_AREA_PX
    )


def view_score(target: dict[str, Any], anchor: dict[str, Any]) -> float:
    return round(
        min(target["ztest_visible_fraction_total"], anchor["ztest_visible_fraction_total"])
        + 0.0005 * min(target["n_ztest_visible"], anchor["n_ztest_visible"])
        + 0.000001 * min(target["ztest_bbox_area_px"], anchor["ztest_bbox_area_px"]),
        8,
    )


def union_box(boxes: list[list[float] | None], width: int, height: int, margin: float = 0.15) -> list[int] | None:
    valid = [b for b in boxes if b is not None and box_area(b) > 0]
    if not valid:
        return None
    x1 = min(b[0] for b in valid)
    y1 = min(b[1] for b in valid)
    x2 = max(b[2] for b in valid)
    y2 = max(b[3] for b in valid)
    pad = max(x2 - x1, y2 - y1, 32.0) * margin
    return [
        max(0, int(math.floor(x1 - pad))),
        max(0, int(math.floor(y1 - pad))),
        min(width, int(math.ceil(x2 + pad))),
        min(height, int(math.ceil(y2 + pad))),
    ]


def relation_failure(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "no_prefiltered_frames"
    if not any(r["target_visible"] for r in rows):
        return "target_not_depth_visible"
    if not any(r["anchor_visible"] for r in rows):
        return "anchor_not_depth_visible"
    return "target_anchor_not_covisible_same_frame"


def write_crop(row: dict[str, Any], crop_rel_path: str) -> None:
    image = Image.open(SCENEFUN_ROOT / row["rgb_rel_path"]).convert("RGB")
    box = row["joint_crop_box_xyxy"]
    if not box:
        return
    out_path = EVIDENCE_DIR.parent / crop_rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.crop(tuple(box)).save(out_path, quality=90)


def draw_overlay(row: dict[str, Any], out_path: Path) -> None:
    src = Image.open(SCENEFUN_ROOT / row["rgb_rel_path"]).convert("RGB")
    orig_w, orig_h = src.size
    src.thumbnail((760, 570))
    sx = src.width / float(orig_w)
    sy = src.height / float(orig_h)
    draw = ImageDraw.Draw(src)
    for key, color in [("target_projection", (0, 220, 80)), ("anchor_projection", (255, 160, 0))]:
        box = row[key]["ztest_bbox_xyxy"]
        if box:
            draw.rectangle([box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy], outline=color, width=3)
    if row["joint_crop_box_xyxy"]:
        box = row["joint_crop_box_xyxy"]
        draw.rectangle([box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy], outline=(40, 120, 255), width=2)
    draw.text((8, 8), f"{row['export_split']} {row['scene_id']} score={row['view_score']}", fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    src.save(out_path, quality=85)


def build(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    annotations = {f"{row['scene_id']}/{row['annot_id']}": row for row in read_json(ANNOTATIONS_JSON)}
    ply_paths = load_raw_ply_paths()
    frames_by_scene = load_all_frames_by_scene()
    relations = list(read_jsonl(EVIDENCE_DIR / "relation_evidence_index.jsonl"))
    if args.limit_relations:
        relations = relations[: args.limit_relations]

    scene_cache: dict[str, np.ndarray] = {}
    points_cache: dict[tuple[str, str, int], np.ndarray] = {}
    transform_cache: dict[tuple[str, str, str], np.ndarray] = {}
    traj_cache: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    pose_cache: dict[str, dict[str, Any]] = {}
    intr_cache: dict[str, dict[str, float]] = {}
    depth_cache: dict[str, np.ndarray] = {}

    selected_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    qc_rows: list[dict[str, Any]] = []

    for relation in relations:
        scene_id = str(relation["scene_id"])
        if scene_id not in scene_cache:
            scene_cache[scene_id] = parse_ply_vertices(ply_paths[scene_id])
        verts = scene_cache[scene_id]
        node_ids = [str(relation["target_node_id"])]
        if not relation.get("anchor_missing"):
            node_ids.append(str(relation["anchor_node_id"]))
        for node_id in node_ids:
            for npts in [args.prefilter_points, args.ztest_points]:
                key = (scene_id, node_id, npts)
                if key not in points_cache:
                    anno = annotations.get(f"{scene_id}/{node_id}", {})
                    points_cache[key] = points_for_node(verts, anno.get("indices") or [], npts)

        prefiltered = []
        frame_pool = frames_by_scene.get(scene_id, [])
        for frame in frame_pool:
            split = frame_split(frame)
            root = frame_root(frame)
            cap_key = (split, scene_id, str(frame["capture_id"]))
            if cap_key not in transform_cache:
                transform_cache[cap_key] = np.load(root / f"{frame['capture_id']}_refined_transform.npy")
            if cap_key not in traj_cache:
                traj_cache[cap_key] = load_trajectory(root / "lowres_wide.traj")
            intr_path = SCENEFUN_ROOT / str(frame["intrinsics_rel_path"])
            if str(intr_path) not in intr_cache:
                intr_cache[str(intr_path)] = parse_intrinsics(intr_path)
            frame_key = str(frame["frame_key"])
            if frame_key not in pose_cache:
                pose_cache[frame_key] = nearest_pose(traj_cache[cap_key], frame_timestamp(str(frame["frame_stem"])))
            pose = pose_cache[frame_key]
            intr = intr_cache[str(intr_path)]
            target_pre = project_points(points_cache[(scene_id, str(relation["target_node_id"]), args.prefilter_points)], transform_cache[cap_key], pose["cam_to_world"], intr)
            if relation.get("anchor_missing"):
                anchor_pre = empty_projection("anchor_missing")
            else:
                anchor_pre = project_points(points_cache[(scene_id, str(relation["anchor_node_id"]), args.prefilter_points)], transform_cache[cap_key], pose["cam_to_world"], intr)
            score = prefilter_score(target_pre, anchor_pre)
            if score > 0:
                prefiltered.append((score, frame_key, frame, cap_key, intr_path, pose))

        relation_frames: list[dict[str, Any]] = []
        for _, frame_key, frame, cap_key, intr_path, pose in sorted(prefiltered, key=lambda x: (-x[0], x[1]))[: args.prefilter_top_n]:
            depth_path = SCENEFUN_ROOT / str(frame["depth_rel_path"])
            if str(depth_path) not in depth_cache:
                depth_cache[str(depth_path)] = load_depth(depth_path)
            intr = intr_cache[str(intr_path)]
            target_stats = project_points(points_cache[(scene_id, str(relation["target_node_id"]), args.ztest_points)], transform_cache[cap_key], pose["cam_to_world"], intr, depth_cache[str(depth_path)])
            if relation.get("anchor_missing"):
                anchor_stats = empty_projection("anchor_missing")
            else:
                anchor_stats = project_points(points_cache[(scene_id, str(relation["anchor_node_id"]), args.ztest_points)], transform_cache[cap_key], pose["cam_to_world"], intr, depth_cache[str(depth_path)])
            tvis = target_visible(target_stats)
            avis = anchor_visible(anchor_stats, bool(relation.get("anchor_missing")))
            crop_box = union_box([target_stats["ztest_bbox_xyxy"], anchor_stats["ztest_bbox_xyxy"]], int(intr["width"]), int(intr["height"]))
            covis = bool(tvis and avis and crop_box)
            timestamp = frame_timestamp(str(frame["frame_stem"]))
            split = frame_split(frame)
            row = {
                "relation_key": relation["relation_key"],
                "relation_dir": relation["relation_dir"],
                "query_id": relation["query_id"],
                "export_split": relation["export_split"],
                "scene_id": scene_id,
                "target_node_id": relation["target_node_id"],
                "target_label": relation.get("target_label"),
                "anchor_node_id": relation["anchor_node_id"],
                "anchor_label": relation.get("anchor_label"),
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
                "target_projection": target_stats,
                "anchor_projection": anchor_stats,
                "target_visible": tvis,
                "anchor_visible": avis,
                "co_visible": covis,
                "joint_crop_box_xyxy": crop_box,
                "view_score": view_score(target_stats, anchor_stats) if covis else 0.0,
                "depth_z_test_applied": True,
                "depth_scale_m": DEPTH_SCALE_M,
                "depth_tolerance_m": DEPTH_TOLERANCE_M,
                "selection_rule_version": RULE_VERSION,
                "is_placeholder_rule": False,
                "coordinate_frame": "laser_scan_points -> refined_transform.npy -> ARKit world -> nearest lowres_wide.traj camera pose -> wide_intrinsics",
            }
            relation_frames.append(row)

        ranked = sorted([r for r in relation_frames if r["co_visible"]], key=lambda r: (-r["view_score"], r["frame_pose_time_delta"], r["frame_key"]))
        selected_views = []
        for rank, row in enumerate(ranked[: args.top_k]):
            crop_rel_path = str(Path("relation_conditioned_evidence") / "crops_local" / row["scene_id"] / row["relation_dir"] / f"view_{rank:02d}.jpg")
            view = {
                "rank": rank,
                "frame_key": row["frame_key"],
                "view_score": row["view_score"],
                "rgb_rel_path": row["rgb_rel_path"],
                "depth_rel_path": row["depth_rel_path"],
                "crop_rel_path": crop_rel_path,
                "joint_crop_box_xyxy": row["joint_crop_box_xyxy"],
                "target_ztest_bbox_xyxy": row["target_projection"]["ztest_bbox_xyxy"],
                "anchor_ztest_bbox_xyxy": row["anchor_projection"]["ztest_bbox_xyxy"],
                "target_n_ztest_visible": row["target_projection"]["n_ztest_visible"],
                "anchor_n_ztest_visible": row["anchor_projection"]["n_ztest_visible"],
            }
            selected_views.append(view)
            if args.write_local_crops:
                write_crop(row, crop_rel_path)

        selected = {
            "relation_key": relation["relation_key"],
            "relation_dir": relation["relation_dir"],
            "query_id": relation["query_id"],
            "export_split": relation["export_split"],
            "scene_id": scene_id,
            "target_node_id": relation["target_node_id"],
            "target_label": relation.get("target_label"),
            "anchor_node_id": relation["anchor_node_id"],
            "anchor_label": relation.get("anchor_label"),
            "anchor_missing": relation["anchor_missing"],
            "n_frame_pool": len(frame_pool),
            "n_prefiltered_frames": len(prefiltered),
            "n_depth_tested_frames": len(relation_frames),
            "n_covisible_frames": len(ranked),
            "n_selected_views": len(selected_views),
            "selected_views": selected_views,
            "relation_crop_ready": bool(selected_views),
            "failure_reason": "" if selected_views else relation_failure(relation_frames),
            "selection_rule_version": RULE_VERSION,
            "depth_z_test_applied": True,
            "frame_source": "all_scene_rgbd_frames",
            "prefilter_top_n": args.prefilter_top_n,
        }
        selected_rows.append(selected)
        frame_rows.extend(relation_frames)
        qc_rows.append({
            "relation_key": selected["relation_key"],
            "query_id": selected["query_id"],
            "split": selected["export_split"],
            "scene_id": selected["scene_id"],
            "target_label": selected.get("target_label") or "",
            "anchor_label": selected.get("anchor_label") or "",
            "relation_crop_ready": selected["relation_crop_ready"],
            "n_frame_pool": selected["n_frame_pool"],
            "n_prefiltered_frames": selected["n_prefiltered_frames"],
            "n_depth_tested_frames": selected["n_depth_tested_frames"],
            "n_covisible_frames": selected["n_covisible_frames"],
            "n_selected_views": selected["n_selected_views"],
            "failure_reason": selected["failure_reason"],
        })

    summary = summarize(selected_rows, frame_rows, args)
    return selected_rows, frame_rows, summary, qc_rows


def summarize(selected_rows: list[dict[str, Any]], frame_rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    by_split = Counter(row["export_split"] for row in selected_rows)
    ready_by_split = Counter(row["export_split"] for row in selected_rows if row["relation_crop_ready"])
    tested_by_split = Counter(row["export_split"] for row in frame_rows)
    covis_by_split = Counter(row["export_split"] for row in frame_rows if row["co_visible"])
    return {
        "status": "official_relation_crop_metadata_ready",
        "selection_rule_version": RULE_VERSION,
        "n_relations": len(selected_rows),
        "n_relations_crop_ready": sum(row["relation_crop_ready"] for row in selected_rows),
        "n_relations_without_crop": sum(not row["relation_crop_ready"] for row in selected_rows),
        "n_depth_tested_frame_rows": len(frame_rows),
        "n_covisible_frame_rows": sum(row["co_visible"] for row in frame_rows),
        "top_k": args.top_k,
        "frame_source": "all_scene_rgbd_frames",
        "prefilter_top_n": args.prefilter_top_n,
        "prefilter_points_per_object": args.prefilter_points,
        "ztest_points_per_object": args.ztest_points,
        "depth_z_test_applied": True,
        "depth_scale_m": DEPTH_SCALE_M,
        "depth_tolerance_m": DEPTH_TOLERANCE_M,
        "thresholds": {
            "target_min_z_visible": TARGET_MIN_Z_VISIBLE,
            "anchor_min_z_visible": ANCHOR_MIN_Z_VISIBLE,
            "target_min_z_fraction": TARGET_MIN_Z_FRACTION,
            "anchor_min_z_fraction": ANCHOR_MIN_Z_FRACTION,
            "min_bbox_area_px": MIN_BBOX_AREA_PX,
        },
        "by_split": {
            split: {
                "n_relations": by_split[split],
                "n_relations_crop_ready": ready_by_split[split],
                "n_depth_tested_frame_rows": tested_by_split[split],
                "n_covisible_frame_rows": covis_by_split[split],
            }
            for split in sorted(by_split)
        },
        "important_boundary": "Crop metadata is frozen and depth-tested. Crop images are generated locally under ignored crops_local/ and are not committed; QC overlays are diagnostic spot-check artifacts.",
    }


def write_status(summary: dict[str, Any]) -> None:
    lines = [
        "# Official Relation Crop Status",
        "",
        "This is the frozen relation-conditioned crop metadata layer for the FunGraph 3DGraphLLM export. It scans each scene's full RGB-D frame pool with a fast geometric prefilter, then applies depth z-test to the top candidates. It does not run baselines or learned feature extraction.",
        "",
        "## Result",
        "",
        f"- Status: `{summary['status']}`",
        f"- Selection rule: `{summary['selection_rule_version']}`",
        f"- Frame source: `{summary['frame_source']}`",
        f"- Relations crop-ready: {summary['n_relations_crop_ready']} / {summary['n_relations']}",
        f"- Co-visible depth-tested frame rows: {summary['n_covisible_frame_rows']} / {summary['n_depth_tested_frame_rows']}",
        f"- Depth z-test tolerance: {summary['depth_tolerance_m']} m",
        "",
        "## Boundary",
        "",
        summary["important_boundary"],
        "",
        "Large crop images live under ignored `crops_local/` when generated and are not committed.",
    ]
    (EVIDENCE_DIR / "OFFICIAL_CROP_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_qc(selected_rows: list[dict[str, Any]], frame_rows: list[dict[str, Any]], qc_rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    with (EVIDENCE_DIR / "p4_qc_report.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(qc_rows[0]))
        writer.writeheader()
        writer.writerows(qc_rows)

    frame_by_key = {row["frame_key"] + "|" + row["relation_key"]: row for row in frame_rows}
    ready = sorted([r for r in selected_rows if r["relation_crop_ready"]], key=lambda r: (0 if r["export_split"] == "human_133" else 1, r["scene_id"], r["query_id"]))
    cards = []
    overlay_dir = EVIDENCE_DIR / "qc_overlays"
    if overlay_dir.exists():
        for old_overlay in overlay_dir.glob("*.jpg"):
            old_overlay.unlink()
    for relation in ready[: args.qc_examples]:
        view = relation["selected_views"][0]
        frame = frame_by_key[view["frame_key"] + "|" + relation["relation_key"]]
        overlay_rel = Path("qc_overlays") / f"{relation['relation_dir']}_{view['rank']:02d}.jpg"
        draw_overlay(frame, EVIDENCE_DIR / overlay_rel)
        cards.append((relation, view, overlay_rel))

    html_lines = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Relation Crop QC</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;background:#f7f7f7;color:#222}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px}.card{background:#fff;border:1px solid #ddd;padding:12px}.card img{max-width:100%;height:auto}.meta{font-size:12px;line-height:1.35;word-break:break-word}.legend span{margin-right:14px}</style>",
        "</head><body>",
        "<h1>Relation-Conditioned Crop QC</h1>",
        "<p class='legend'><span style='color:#00aa44'>target box</span><span style='color:#c87800'>anchor box</span><span style='color:#2878ff'>joint crop</span></p>",
        "<div class='grid'>",
    ]
    for relation, view, overlay_rel in cards:
        html_lines.extend([
            "<div class='card'>",
            f"<img src='{html.escape(str(overlay_rel))}' />",
            "<div class='meta'>",
            f"<b>{html.escape(relation['query_id'])}</b><br>",
            f"scene={html.escape(relation['scene_id'])} split={html.escape(relation['export_split'])}<br>",
            f"target={html.escape(str(relation.get('target_label') or ''))} anchor={html.escape(str(relation.get('anchor_label') or ''))}<br>",
            f"score={view['view_score']} target_z={view['target_n_ztest_visible']} anchor_z={view['anchor_n_ztest_visible']}<br>",
            f"{html.escape(relation['relation_key'])}",
            "</div></div>",
        ])
    html_lines.extend(["</div></body></html>"])
    (EVIDENCE_DIR / "p4_sanity_examples.html").write_text("\n".join(html_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-relations", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--prefilter-top-n", type=int, default=PREFILTER_TOP_N)
    parser.add_argument("--prefilter-points", type=int, default=PREFILTER_POINTS)
    parser.add_argument("--ztest-points", type=int, default=ZTEST_POINTS)
    parser.add_argument("--qc-examples", type=int, default=40)
    parser.add_argument("--write-local-crops", action="store_true")
    args = parser.parse_args()

    selected_rows, frame_rows, summary, qc_rows = build(args)
    write_jsonl(EVIDENCE_DIR / "official_crop_index.jsonl", selected_rows)
    write_jsonl(EVIDENCE_DIR / "official_frame_projection_index.jsonl", frame_rows)
    write_json(EVIDENCE_DIR / "official_crop_summary.json", summary)
    write_status(summary)
    write_qc(selected_rows, frame_rows, qc_rows, args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
