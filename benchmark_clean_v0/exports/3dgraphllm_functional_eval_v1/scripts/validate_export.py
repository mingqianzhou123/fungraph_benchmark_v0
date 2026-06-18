#!/usr/bin/env python3
"""Validate the 3DGraphLLM functional evaluation export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]

EXPECTED_COUNTS = {
    "functional_500_eval.jsonl": 500,
    "human_133_eval.jsonl": 133,
    "minimal_pairs_28_eval.jsonl": 28,
    "long_range_50_eval.jsonl": 50,
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def assert_unique_query_ids(path: str, rows: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for row in rows:
        qid = row.get("query_id")
        assert qid, f"{path}: missing query_id"
        assert qid not in seen, f"{path}: duplicate query_id {qid}"
        seen.add(qid)


def validate_query_rows(path: str, rows: list[dict[str, Any]], candidates_by_scene: dict[str, set[str]]) -> None:
    assert_unique_query_ids(path, rows)
    for row in rows:
        qid = row["query_id"]
        scene_id = row.get("scene_id")
        assert scene_id, f"{path}:{qid}: missing scene_id"
        assert scene_id in candidates_by_scene, f"{path}:{qid}: scene has no candidates: {scene_id}"
        targets = row.get("target_node_ids") or []
        assert targets, f"{path}:{qid}: missing target_node_ids"
        for target in targets:
            assert target in candidates_by_scene[scene_id], f"{path}:{qid}: target not in candidates: {target}"
        assert row.get("query_text"), f"{path}:{qid}: missing query_text"
        assert row.get("prompt"), f"{path}:{qid}: missing prompt"
        assert row.get("source"), f"{path}:{qid}: missing source"
        assert isinstance(row.get("difficulty_tags"), list), f"{path}:{qid}: difficulty_tags must be list"
        candidate_node_ids = row.get("candidate_node_ids") or []
        assert set(candidate_node_ids) == candidates_by_scene[scene_id], f"{path}:{qid}: embedded candidates mismatch scene candidates"


def main() -> None:
    candidate_rows = read_jsonl(EXPORT_DIR / "candidate_objects.jsonl")
    candidates_by_scene = {
        row["scene_id"]: set(row["candidate_node_ids"])
        for row in candidate_rows
    }
    assert candidates_by_scene, "candidate_objects.jsonl is empty"

    query_files = [
        "functional_500_eval.jsonl",
        "human_133_eval.jsonl",
        "long_range_50_eval.jsonl",
    ]
    all_query_ids: set[str] = set()
    for filename in query_files:
        rows = read_jsonl(EXPORT_DIR / filename)
        assert len(rows) == EXPECTED_COUNTS[filename], f"{filename}: expected {EXPECTED_COUNTS[filename]}, got {len(rows)}"
        validate_query_rows(filename, rows, candidates_by_scene)
        all_query_ids.update(row["query_id"] for row in rows)

    minimal_pairs = read_jsonl(EXPORT_DIR / "minimal_pairs_28_eval.jsonl")
    assert len(minimal_pairs) == EXPECTED_COUNTS["minimal_pairs_28_eval.jsonl"], "minimal pair count mismatch"
    pair_ids = set()
    for row in minimal_pairs:
        pair_id = row.get("pair_id")
        assert pair_id, "minimal pair missing pair_id"
        assert pair_id not in pair_ids, f"duplicate pair_id {pair_id}"
        pair_ids.add(pair_id)
        assert row.get("query_a_id") in all_query_ids, f"{pair_id}: query_a_id not exported"
        assert row.get("query_b_id") in all_query_ids, f"{pair_id}: query_b_id not exported"

    answer_key = json.loads((EXPORT_DIR / "answer_key.json").read_text(encoding="utf-8"))
    assert set(answer_key) == all_query_ids, "answer_key query ids do not match exported query ids"

    node_mapping = json.loads((EXPORT_DIR / "node_id_mapping.json").read_text(encoding="utf-8"))
    for scene_id, node_ids in candidates_by_scene.items():
        for node_id in node_ids:
            key = f"{scene_id}/{node_id}"
            assert key in node_mapping, f"missing node_id_mapping key {key}"

    summary = json.loads((EXPORT_DIR / "export_summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["functional_500_eval"] == 500
    assert summary["counts"]["human_133_eval"] == 133
    assert summary["counts"]["minimal_pairs_28_eval"] == 28
    assert summary["counts"]["long_range_50_eval"] == 50

    native_dir = EXPORT_DIR / "native_3dgraphllm"
    native_manifest = native_dir / "native_packet_manifest.json"
    if native_manifest.exists():
        manifest = json.loads(native_manifest.read_text(encoding="utf-8"))
        assert manifest["status"] in {
            "loader_smoke_test_ready_not_full_modality",
            "real_scene3d_modality_features_ready_not_pretrained_uni3d",
            "full_scene3d_multimodal_adapter_ready_not_pretrained_encoder_features",
        }
        expected_native_files = [
            "fungraph_scene3d_attributes.pt",
            "fungraph_scene3d_uni3d_feats.pt",
            "fungraph_scene3d_videofeats.pt",
            "fungraph_scene3d_gnn_feats.pt",
            "fungraph_functional_500_val.json",
            "fungraph_functional_500_objselect_val.json",
            "fungraph_human_133_val.json",
            "fungraph_human_133_objselect_val.json",
            "fungraph_long_range_50_val.json",
            "fungraph_long_range_50_objselect_val.json",
            "fungraph_smoke_1_val.json",
            "fungraph_objselect_smoke_1_val.json",
            "config_fungraph_eval.py",
        ]
        for filename in expected_native_files:
            assert (native_dir / filename).exists(), f"missing native packet file: {filename}"

    audit_report = EXPORT_DIR / "asset_alignment_report.md"
    audit_manifest = EXPORT_DIR / "native_3dgraphllm_asset_manifest.csv"
    audit_schema = EXPORT_DIR / "native_3dgraphllm_asset_schema.json"
    if audit_report.exists() or audit_manifest.exists() or audit_schema.exists():
        assert audit_report.exists(), "missing asset_alignment_report.md"
        assert audit_manifest.exists(), "missing native_3dgraphllm_asset_manifest.csv"
        assert audit_schema.exists(), "missing native_3dgraphllm_asset_schema.json"

    object_manifest = EXPORT_DIR / "object_modality_manifest.csv"
    scene_rgbd_manifest = EXPORT_DIR / "scene_rgbd_manifest.csv"
    if object_manifest.exists() or scene_rgbd_manifest.exists():
        assert object_manifest.exists(), "missing object_modality_manifest.csv"
        assert scene_rgbd_manifest.exists(), "missing scene_rgbd_manifest.csv"
        with object_manifest.open("r", encoding="utf-8", newline="") as f:
            rows = list(__import__("csv").DictReader(f))
        assert rows, "object_modality_manifest.csv is empty"
        assert all(row["has_point_xyz"] == "True" for row in rows), "not all objects have point xyz"
        assert all(row["has_point_rgb"] == "True" for row in rows), "not all objects have point rgb"
        with scene_rgbd_manifest.open("r", encoding="utf-8", newline="") as f:
            scene_rows = list(__import__("csv").DictReader(f))
        assert len(scene_rows) == len(candidates_by_scene), "scene_rgbd_manifest scene count mismatch"
        assert all(row["has_rgb"] == "True" for row in scene_rows), "not all scenes have RGB frames"
        assert all(row["has_depth"] == "True" for row in scene_rows), "not all scenes have depth frames"

    full_summary = EXPORT_DIR / "full_multimodal_readiness.json"
    full_capture_manifest = EXPORT_DIR / "full_scene_capture_manifest.csv"
    full_frame_index = EXPORT_DIR / "full_scene_frame_index.jsonl"
    full_object_manifest = EXPORT_DIR / "full_object_modality_manifest.csv"
    full_status_doc = EXPORT_DIR / "FULL_MULTIMODAL_BENCHMARK_STATUS.md"
    if any(path.exists() for path in [full_summary, full_capture_manifest, full_frame_index, full_object_manifest, full_status_doc]):
        assert full_summary.exists(), "missing full_multimodal_readiness.json"
        assert full_capture_manifest.exists(), "missing full_scene_capture_manifest.csv"
        assert full_frame_index.exists(), "missing full_scene_frame_index.jsonl"
        assert full_object_manifest.exists(), "missing full_object_modality_manifest.csv"
        assert full_status_doc.exists(), "missing FULL_MULTIMODAL_BENCHMARK_STATUS.md"
        summary = json.loads(full_summary.read_text(encoding="utf-8"))
        assert summary["status"] == "full_raw_multimodal_benchmark_ready"
        assert summary["n_scenes"] == len(candidates_by_scene)
        assert summary["all_scenes_full_ready"] is True, "not all scenes are full multimodal ready"
        assert summary["n_export_candidate_objects"] == sum(len(x) for x in candidates_by_scene.values())
        assert summary["n_full_export_candidate_objects"] == summary["n_export_candidate_objects"], "not all exported candidate objects are full ready"

    print("3DGraphLLM export validation passed")


if __name__ == "__main__":
    main()
