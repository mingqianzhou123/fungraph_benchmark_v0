#!/usr/bin/env python3
"""Build full-coverage relation-conditioned perception evidence.

The strict RGB-D crop layer can only certify relations that are co-visible under
the frozen depth z-test. This script adds a complementary pointcloud-render
fallback so every relation has an inspectable visual evidence card without
pretending that missing camera views exist.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_projection_dryrun import (  # noqa: E402
    ANNOTATIONS_JSON,
    EVIDENCE_DIR,
    load_raw_ply_paths,
    parse_ply_vertices,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)

RULE_VERSION = "full_perception_evidence_v1_20260618_rgbd_or_pointcloud"
IMAGE_ROOT_REL = Path("relation_conditioned_evidence") / "full_perception_evidence" / "images"
IMAGE_ROOT = EVIDENCE_DIR.parent / IMAGE_ROOT_REL
INDEX_PATH = EVIDENCE_DIR / "full_perception_evidence_index.jsonl"
SUMMARY_PATH = EVIDENCE_DIR / "full_perception_evidence_summary.json"
STATUS_PATH = EVIDENCE_DIR / "FULL_PERCEPTION_EVIDENCE_STATUS.md"

TARGET_COLOR = (0, 180, 95)
ANCHOR_COLOR = (230, 130, 20)
CONTEXT_COLOR = (172, 176, 180)
TEXT_COLOR = (30, 34, 38)
MUTED_TEXT = (92, 100, 108)
PANEL_BG = (246, 248, 250)
CANVAS_BG = (255, 255, 255)


def object_points(verts: np.ndarray, indices: list[int], max_points: int) -> tuple[np.ndarray, np.ndarray]:
    idx = np.asarray(indices or [], dtype=np.int64)
    idx = idx[(idx >= 0) & (idx < len(verts))]
    if max_points and len(idx) > max_points:
        step = max(1, len(idx) // max_points)
        idx = idx[::step][:max_points]
    if len(idx) == 0:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.uint8)
    xyz = np.column_stack([verts["x"][idx], verts["y"][idx], verts["z"][idx]]).astype(np.float32)
    rgb = np.column_stack([verts["red"][idx], verts["green"][idx], verts["blue"][idx]]).astype(np.uint8)
    return xyz, rgb


def sample_scene_context(verts: np.ndarray, max_points: int) -> np.ndarray:
    n = len(verts)
    if n == 0:
        return np.zeros((0, 3), dtype=np.float32)
    step = max(1, n // max_points)
    idx = np.arange(0, n, step, dtype=np.int64)[:max_points]
    return np.column_stack([verts["x"][idx], verts["y"][idx], verts["z"][idx]]).astype(np.float32)


def padded_bounds(points: np.ndarray, dims: tuple[int, int], pad_frac: float = 0.22) -> tuple[float, float, float, float]:
    if len(points) == 0:
        return -1.0, -1.0, 1.0, 1.0
    vals = points[:, list(dims)]
    lo = vals.min(axis=0)
    hi = vals.max(axis=0)
    span = np.maximum(hi - lo, 0.25)
    lo = lo - span * pad_frac
    hi = hi + span * pad_frac
    return float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1])


def project(points: np.ndarray, dims: tuple[int, int], bounds: tuple[float, float, float, float], box: tuple[int, int, int, int]) -> np.ndarray:
    if len(points) == 0:
        return np.zeros((0, 2), dtype=np.int32)
    x0, y0, x1, y1 = box
    min_a, min_b, max_a, max_b = bounds
    width = max(1.0, max_a - min_a)
    height = max(1.0, max_b - min_b)
    u = x0 + (points[:, dims[0]] - min_a) / width * (x1 - x0)
    v = y1 - (points[:, dims[1]] - min_b) / height * (y1 - y0)
    u = np.clip(np.rint(u), x0, x1).astype(np.int32)
    v = np.clip(np.rint(v), y0, y1).astype(np.int32)
    return np.column_stack([u, v])


def local_context(context: np.ndarray, bounds_xy: tuple[float, float, float, float], bounds_xz: tuple[float, float, float, float]) -> np.ndarray:
    if len(context) == 0:
        return context
    min_x = min(bounds_xy[0], bounds_xz[0])
    max_x = max(bounds_xy[2], bounds_xz[2])
    min_y, max_y = bounds_xy[1], bounds_xy[3]
    min_z, max_z = bounds_xz[1], bounds_xz[3]
    mask = (
        (context[:, 0] >= min_x)
        & (context[:, 0] <= max_x)
        & (context[:, 1] >= min_y)
        & (context[:, 1] <= max_y)
        & (context[:, 2] >= min_z)
        & (context[:, 2] <= max_z)
    )
    return context[mask]


def draw_points(draw: ImageDraw.ImageDraw, pts: np.ndarray, color: tuple[int, int, int], radius: int = 1) -> None:
    if len(pts) == 0:
        return
    if radius <= 1:
        draw.point([tuple(x) for x in pts], fill=color)
        return
    for x, y in pts:
        draw.ellipse((int(x) - radius, int(y) - radius, int(x) + radius, int(y) + radius), fill=color)


def draw_object_box(
    draw: ImageDraw.ImageDraw,
    pts: np.ndarray,
    color: tuple[int, int, int],
    label: str,
    font: ImageFont.ImageFont,
) -> None:
    if len(pts) == 0:
        return
    x0 = int(pts[:, 0].min())
    y0 = int(pts[:, 1].min())
    x1 = int(pts[:, 0].max())
    y1 = int(pts[:, 1].max())
    draw.rectangle((x0, y0, x1, y1), outline=color, width=2)
    draw.text((x0 + 4, max(0, y0 - 16)), label, fill=color, font=font)


def render_card(
    out_path: Path,
    relation: dict[str, Any],
    target_xyz: np.ndarray,
    anchor_xyz: np.ndarray,
    context_xyz: np.ndarray,
    official_row: dict[str, Any] | None,
) -> None:
    canvas = Image.new("RGB", (760, 470), CANVAS_BG)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    title = f"{relation['export_split']} | scene {relation['scene_id']} | {relation['query_id']}"
    tier = "RGB-D crop + pointcloud render" if official_row and official_row.get("relation_crop_ready") else "pointcloud render fallback"
    draw.text((18, 14), title[:110], fill=TEXT_COLOR, font=font)
    draw.text((18, 31), tier, fill=MUTED_TEXT, font=font)
    draw.text((18, 448), relation["relation_key"][:115], fill=MUTED_TEXT, font=font)

    top_box = (28, 62, 360, 424)
    side_box = (400, 62, 732, 424)
    for box, label in [(top_box, "top-down x/y"), (side_box, "side x/z")]:
        draw.rectangle(box, fill=PANEL_BG, outline=(210, 214, 218), width=1)
        draw.text((box[0] + 8, box[1] + 8), label, fill=MUTED_TEXT, font=font)

    union = np.vstack([arr for arr in [target_xyz, anchor_xyz] if len(arr)]) if (len(target_xyz) or len(anchor_xyz)) else np.zeros((0, 3), dtype=np.float32)
    bounds_xy = padded_bounds(union, (0, 1))
    bounds_xz = padded_bounds(union, (0, 2))
    ctx = local_context(context_xyz, bounds_xy, bounds_xz)
    if len(ctx) > 7000:
        ctx = ctx[:: max(1, len(ctx) // 7000)][:7000]

    for dims, box in [((0, 1), top_box), ((0, 2), side_box)]:
        bounds = bounds_xy if dims == (0, 1) else bounds_xz
        draw_points(draw, project(ctx, dims, bounds, box), CONTEXT_COLOR, radius=1)
        tproj = project(target_xyz, dims, bounds, box)
        aproj = project(anchor_xyz, dims, bounds, box)
        draw_points(draw, tproj, TARGET_COLOR, radius=2)
        draw_points(draw, aproj, ANCHOR_COLOR, radius=2)
        draw_object_box(draw, tproj, TARGET_COLOR, f"target: {relation.get('target_label') or ''}"[:36], font)
        if len(anchor_xyz):
            draw_object_box(draw, aproj, ANCHOR_COLOR, f"anchor: {relation.get('anchor_label') or ''}"[:36], font)

    if official_row and official_row.get("relation_crop_ready"):
        view = official_row["selected_views"][0]
        note = f"depth-tested RGB-D view: {view['frame_key']} score={view['view_score']}"
    else:
        reason = official_row.get("failure_reason") if official_row else "no_official_crop_row"
        note = f"RGB-D crop unavailable under frozen rule: {reason}"
    draw.text((400, 431), note[:58], fill=MUTED_TEXT, font=font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=78, optimize=True)


def build(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    annotations = {f"{row['scene_id']}/{row['annot_id']}": row for row in read_json(ANNOTATIONS_JSON)}
    ply_paths = load_raw_ply_paths()
    relations = list(read_jsonl(EVIDENCE_DIR / "relation_evidence_index.jsonl"))
    official_rows = {row["relation_key"]: row for row in read_jsonl(EVIDENCE_DIR / "official_crop_index.jsonl")}
    if args.limit_relations:
        relations = relations[: args.limit_relations]

    scene_cache: dict[str, np.ndarray] = {}
    context_cache: dict[str, np.ndarray] = {}
    object_cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
    out_rows: list[dict[str, Any]] = []

    for relation in relations:
        scene_id = str(relation["scene_id"])
        if scene_id not in scene_cache:
            scene_cache[scene_id] = parse_ply_vertices(ply_paths[scene_id])
            context_cache[scene_id] = sample_scene_context(scene_cache[scene_id], args.max_context_points)
        verts = scene_cache[scene_id]

        node_ids = [str(relation["target_node_id"])]
        if not relation.get("anchor_missing"):
            node_ids.append(str(relation["anchor_node_id"]))
        for node_id in node_ids:
            key = (scene_id, node_id)
            if key not in object_cache:
                anno = annotations.get(f"{scene_id}/{node_id}", {})
                object_cache[key] = object_points(verts, anno.get("indices") or [], args.max_object_points)

        target_xyz, _ = object_cache[(scene_id, str(relation["target_node_id"]))]
        if relation.get("anchor_missing"):
            anchor_xyz = np.zeros((0, 3), dtype=np.float32)
        else:
            anchor_xyz, _ = object_cache[(scene_id, str(relation["anchor_node_id"]))]
        official = official_rows.get(relation["relation_key"])
        rel_path = IMAGE_ROOT_REL / scene_id / f"{relation['relation_dir']}.jpg"
        out_path = EVIDENCE_DIR.parent / rel_path
        if args.write_images:
            render_card(out_path, relation, target_xyz, anchor_xyz, context_cache[scene_id], official)

        has_crop = bool(official and official.get("relation_crop_ready"))
        row = {
            "relation_key": relation["relation_key"],
            "relation_dir": relation["relation_dir"],
            "query_id": relation["query_id"],
            "export_split": relation["export_split"],
            "scene_id": scene_id,
            "query_text": relation.get("query_text"),
            "target_node_id": relation["target_node_id"],
            "target_label": relation.get("target_label"),
            "anchor_node_id": relation["anchor_node_id"],
            "anchor_label": relation.get("anchor_label"),
            "anchor_missing": relation["anchor_missing"],
            "visual_evidence_ready": len(target_xyz) > 0 and (relation.get("anchor_missing") or len(anchor_xyz) > 0),
            "evidence_tier": "rgbd_crop_plus_pointcloud_render" if has_crop else "pointcloud_render_fallback",
            "has_depth_tested_rgbd_crop": has_crop,
            "official_crop_failure_reason": "" if has_crop else (official.get("failure_reason") if official else "missing_official_crop_row"),
            "pointcloud_render_rel_path": str(rel_path),
            "primary_visual_rel_path": str(rel_path),
            "selected_rgbd_views": official.get("selected_views", []) if official else [],
            "n_target_points_rendered": int(len(target_xyz)),
            "n_anchor_points_rendered": int(len(anchor_xyz)),
            "render_rule_version": RULE_VERSION,
            "important_boundary": "Fallback render is generated from GT SceneFun3D pointcloud object segments. It is visual evidence, but it is not a real camera RGB-D crop.",
        }
        out_rows.append(row)

    by_split = Counter(row["export_split"] for row in out_rows)
    ready_by_split = Counter(row["export_split"] for row in out_rows if row["visual_evidence_ready"])
    crop_by_split = Counter(row["export_split"] for row in out_rows if row["has_depth_tested_rgbd_crop"])
    summary = {
        "status": "full_perception_evidence_ready",
        "selection_rule_version": RULE_VERSION,
        "n_relations": len(out_rows),
        "n_visual_evidence_ready": sum(row["visual_evidence_ready"] for row in out_rows),
        "n_depth_tested_rgbd_crop_relations": sum(row["has_depth_tested_rgbd_crop"] for row in out_rows),
        "n_pointcloud_render_fallback_relations": sum(not row["has_depth_tested_rgbd_crop"] for row in out_rows),
        "n_pointcloud_render_images": len(out_rows) if args.write_images else 0,
        "images_written": bool(args.write_images),
        "image_root_rel_path": str(IMAGE_ROOT_REL),
        "by_split": {
            split: {
                "n_relations": by_split[split],
                "n_visual_evidence_ready": ready_by_split[split],
                "n_depth_tested_rgbd_crop_relations": crop_by_split[split],
                "n_pointcloud_render_fallback_relations": by_split[split] - crop_by_split[split],
            }
            for split in sorted(by_split)
        },
        "important_boundary": "Full coverage is achieved with a tiered evidence policy: strict RGB-D crop when available, otherwise a GT pointcloud-render fallback. Do not report the fallback rows as depth-tested camera evidence.",
    }
    return out_rows, summary


def write_status(summary: dict[str, Any]) -> None:
    lines = [
        "# Full Perception Evidence Status",
        "",
        "This layer provides one inspectable visual evidence card for every relation in the 3DGraphLLM functional export.",
        "",
        "## Result",
        "",
        f"- Status: `{summary['status']}`",
        f"- Selection rule: `{summary['selection_rule_version']}`",
        f"- Visual evidence ready: {summary['n_visual_evidence_ready']} / {summary['n_relations']}",
        f"- Depth-tested RGB-D crop relations: {summary['n_depth_tested_rgbd_crop_relations']} / {summary['n_relations']}",
        f"- Pointcloud-render fallback relations: {summary['n_pointcloud_render_fallback_relations']} / {summary['n_relations']}",
        f"- Pointcloud-render images: {summary['n_pointcloud_render_images']}",
        f"- Image root: `{summary['image_root_rel_path']}`",
        "",
        "## Boundary",
        "",
        summary["important_boundary"],
        "",
        "The strict RGB-D crop layer remains `official_crop_*`. This full-coverage layer is the benchmark-facing perception evidence layer when every relation needs an inspectable visual artifact.",
    ]
    STATUS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-relations", type=int, default=0)
    parser.add_argument("--max-object-points", type=int, default=2500)
    parser.add_argument("--max-context-points", type=int, default=35000)
    parser.add_argument("--write-images", action="store_true")
    args = parser.parse_args()

    rows, summary = build(args)
    write_jsonl(INDEX_PATH, rows)
    write_json(SUMMARY_PATH, summary)
    write_status(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
