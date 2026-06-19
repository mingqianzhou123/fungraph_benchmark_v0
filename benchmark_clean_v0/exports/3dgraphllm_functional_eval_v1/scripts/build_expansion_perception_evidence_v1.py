#!/usr/bin/env python3
"""Build perception evidence cards for expansion freeze candidates."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_full_perception_evidence import (  # noqa: E402
    object_points,
    render_card,
    sample_scene_context,
)
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

EXPORT_DIR = SCRIPT_DIR.parent
EXPANSION_DIR = EXPORT_DIR / "expansion_v1"
FINAL_CANDIDATE_DIR = EXPANSION_DIR / "final_candidates"
OUT_DIR = EXPANSION_DIR / "perception_evidence"
INTERMEDIATE_DIR = EXPANSION_DIR / "_intermediate"
IMAGE_ROOT_REL = Path("perception_evidence") / "images"
IMAGE_ROOT = EXPANSION_DIR / IMAGE_ROOT_REL
RULE_VERSION = "expansion_perception_evidence_v1_20260618_pointcloud_with_previous_crop_metadata"


def safe_relation_dir(row: dict[str, Any]) -> str:
    return str(row["query_id"]).replace("/", "_").replace("|", "_")


def load_previous_full_perception() -> dict[tuple[str, str, str], dict[str, Any]]:
    path = EVIDENCE_DIR / "full_perception_evidence_index.jsonl"
    if not path.exists():
        return {}
    rows = {}
    for row in read_jsonl(path):
        rows[(str(row["scene_id"]), str(row["target_node_id"]), str(row["anchor_node_id"]))] = row
    return rows


def build(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = read_jsonl(FINAL_CANDIDATE_DIR / "functional_balanced_116_frozen_candidate.jsonl")
    annotations = {f"{row['scene_id']}/{row['annot_id']}": row for row in read_json(ANNOTATIONS_JSON)}
    previous = load_previous_full_perception()
    ply_paths = load_raw_ply_paths()

    scene_cache: dict[str, np.ndarray] = {}
    context_cache: dict[str, np.ndarray] = {}
    object_cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
    out_rows: list[dict[str, Any]] = []

    for candidate in candidates:
        scene_id = str(candidate["scene_id"])
        target_id = str(candidate["target_node_id"])
        anchor_id = str(candidate["anchor_node_id"])
        if scene_id not in scene_cache:
            scene_cache[scene_id] = parse_ply_vertices(ply_paths[scene_id])
            context_cache[scene_id] = sample_scene_context(scene_cache[scene_id], args.max_context_points)
        verts = scene_cache[scene_id]

        for node_id in [target_id, anchor_id]:
            key = (scene_id, node_id)
            if key not in object_cache:
                anno = annotations.get(f"{scene_id}/{node_id}", {})
                object_cache[key] = object_points(verts, anno.get("indices") or [], args.max_object_points)

        target_xyz, _ = object_cache[(scene_id, target_id)]
        anchor_xyz, _ = object_cache[(scene_id, anchor_id)]
        previous_row = previous.get((scene_id, target_id, anchor_id), {})
        relation_dir = safe_relation_dir(candidate)
        rel_path = IMAGE_ROOT_REL / scene_id / f"{relation_dir}.jpg"
        out_path = EXPANSION_DIR / rel_path
        relation_for_render = {
            "export_split": "functional_balanced_116_frozen_candidate_v1",
            "scene_id": scene_id,
            "query_id": candidate["query_id"],
            "relation_key": f"{candidate['query_id']}|{target_id}|{anchor_id}",
            "target_label": candidate.get("target_label"),
            "anchor_label": candidate.get("anchor_label"),
        }
        if args.write_images:
            render_card(out_path, relation_for_render, target_xyz, anchor_xyz, context_cache[scene_id], None)

        was_missing = candidate.get("perception_evidence_tier") == "not_in_previous_export"
        visual_ready = len(target_xyz) > 0 and len(anchor_xyz) > 0
        out_rows.append({
            "relation_key": relation_for_render["relation_key"],
            "query_id": candidate["query_id"],
            "freeze_candidate_id": candidate["freeze_candidate_id"],
            "unique_relation_id": candidate["unique_relation_id"],
            "scene_id": scene_id,
            "query_text": candidate.get("query_text"),
            "target_node_id": target_id,
            "target_label": candidate.get("target_label"),
            "anchor_node_id": anchor_id,
            "anchor_label": candidate.get("anchor_label"),
            "supporting_edge_ids": candidate.get("supporting_edge_ids") or [],
            "visual_evidence_ready": visual_ready,
            "expansion_evidence_tier": "pointcloud_render_generated_for_expansion",
            "previous_export_evidence_tier": candidate.get("perception_evidence_tier"),
            "was_missing_from_previous_full_perception_export": was_missing,
            "has_previous_depth_tested_rgbd_crop": bool(previous_row.get("has_depth_tested_rgbd_crop", False)),
            "previous_primary_visual_rel_path": previous_row.get("primary_visual_rel_path", ""),
            "pointcloud_render_rel_path": str(rel_path),
            "primary_visual_rel_path": str(rel_path),
            "n_target_points_rendered": int(len(target_xyz)),
            "n_anchor_points_rendered": int(len(anchor_xyz)),
            "render_rule_version": RULE_VERSION,
            "important_boundary": "Expansion evidence cards are GT pointcloud object-segment renders. Previous RGB-D crop metadata is inherited only when already available; new expansion rows are not newly depth-tested camera crops.",
        })

    by_previous = Counter(row["previous_export_evidence_tier"] for row in out_rows)
    summary = {
        "status": "expansion_perception_evidence_ready",
        "selection_rule_version": RULE_VERSION,
        "n_functional_candidates": len(out_rows),
        "n_visual_evidence_ready": sum(row["visual_evidence_ready"] for row in out_rows),
        "n_previously_missing_relations_now_have_pointcloud_evidence": sum(row["was_missing_from_previous_full_perception_export"] and row["visual_evidence_ready"] for row in out_rows),
        "n_with_previous_depth_tested_rgbd_crop": sum(row["has_previous_depth_tested_rgbd_crop"] for row in out_rows),
        "n_pointcloud_render_images": len(out_rows) if args.write_images else 0,
        "images_written": bool(args.write_images),
        "image_root_rel_path": str(IMAGE_ROOT_REL),
        "previous_export_evidence_tier_counts": dict(by_previous.most_common()),
        "important_boundary": "This completes visual evidence cards for freeze candidates, not new camera-depth z-test crops for all candidates.",
    }
    return out_rows, summary


def write_status(summary: dict[str, Any]) -> None:
    lines = [
        "# Expansion Perception Evidence v1 Status",
        "",
        "This layer adds inspectable visual evidence cards for the expansion functional freeze candidates.",
        "It does not modify the old 683-row full-perception evidence layer.",
        "",
        "## Coverage",
        "",
        f"- Functional freeze candidates: {summary['n_functional_candidates']}",
        f"- Visual evidence ready: {summary['n_visual_evidence_ready']}",
        f"- Previously missing candidates now with pointcloud evidence: {summary['n_previously_missing_relations_now_have_pointcloud_evidence']}",
        f"- Candidates with previous depth-tested RGB-D crop metadata: {summary['n_with_previous_depth_tested_rgbd_crop']}",
        f"- Images written: {summary['n_pointcloud_render_images']}",
        "",
        "## Boundary",
        "",
        "The generated evidence cards are GT pointcloud object-segment renders. They make every candidate inspectable, but they do not imply that every candidate has a newly depth-tested camera RGB-D crop.",
    ]
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    (INTERMEDIATE_DIR / "EXPANSION_PERCEPTION_EVIDENCE_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-images", action="store_true")
    parser.add_argument("--max-object-points", type=int, default=5500)
    parser.add_argument("--max-context-points", type=int, default=50000)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, summary = build(args)
    write_jsonl(OUT_DIR / "expansion_perception_evidence_index.jsonl", rows)
    write_json(OUT_DIR / "expansion_perception_evidence_summary.json", summary)
    write_status(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
