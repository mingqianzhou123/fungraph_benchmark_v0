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

    evidence_dir = EXPORT_DIR / "relation_conditioned_evidence"
    if evidence_dir.exists():
        required = [
            "README.md",
            "RELATION_EVIDENCE_STATUS.md",
            "relation_evidence_summary.json",
            "relation_evidence_index.jsonl",
            "relation_frame_candidates.jsonl",
            "query_relation_index.jsonl",
            "minimal_pair_relation_index.jsonl",
            "sample_load_relation_evidence.py",
        ]
        for filename in required:
            assert (evidence_dir / filename).exists(), f"missing relation evidence file: {filename}"
        summary = json.loads((evidence_dir / "relation_evidence_summary.json").read_text(encoding="utf-8"))
        expected_relations = sum(EXPECTED_COUNTS[name] for name in ["functional_500_eval.jsonl", "human_133_eval.jsonl", "long_range_50_eval.jsonl"])
        assert summary["status"] == "relation_conditioned_evidence_index_ready_not_projected"
        assert summary["n_relations"] == expected_relations
        assert summary["n_relation_evidence_ready"] == expected_relations
        assert summary["n_minimal_pairs"] == EXPECTED_COUNTS["minimal_pairs_28_eval.jsonl"]
        assert summary["n_minimal_pairs_ready"] == EXPECTED_COUNTS["minimal_pairs_28_eval.jsonl"]
        relation_rows = read_jsonl(evidence_dir / "relation_evidence_index.jsonl")
        assert len(relation_rows) == expected_relations
        assert all(row["relation_evidence_ready"] is True for row in relation_rows), "not all relation evidence rows are ready"
        assert all("|" in row["relation_key"] for row in relation_rows), "invalid relation key format"

        projection_summary_path = evidence_dir / "projection_dryrun_summary.json"
        projection_index_path = evidence_dir / "projection_dryrun_index.jsonl"
        projection_status_path = evidence_dir / "PROJECTION_DRYRUN_STATUS.md"
        if any(path.exists() for path in [projection_summary_path, projection_index_path, projection_status_path]):
            assert projection_summary_path.exists(), "missing projection_dryrun_summary.json"
            assert projection_index_path.exists(), "missing projection_dryrun_index.jsonl"
            assert projection_status_path.exists(), "missing PROJECTION_DRYRUN_STATUS.md"
            projection_summary = json.loads(projection_summary_path.read_text(encoding="utf-8"))
            projection_rows = read_jsonl(projection_index_path)
            assert projection_summary["status"] == "projection_dryrun_placeholder_ready"
            assert projection_summary["n_relations"] == expected_relations
            assert projection_summary["n_projection_rows"] == summary["n_frame_candidates"]
            assert len(projection_rows) == summary["n_frame_candidates"]
            assert projection_summary["depth_z_test_applied"] is False
            assert all(row["is_placeholder_rule"] is True for row in projection_rows), "projection dry-run rows must remain placeholder"
            assert all(row["depth_z_test_applied"] is False for row in projection_rows), "projection dry-run unexpectedly applied depth z-test"
            assert all(row["selection_rule_version"].startswith("placeholder_dryrun_") for row in projection_rows), "projection dry-run selection rule must be placeholder"

        official_summary_path = evidence_dir / "official_crop_summary.json"
        official_crop_index_path = evidence_dir / "official_crop_index.jsonl"
        official_frame_index_path = evidence_dir / "official_frame_projection_index.jsonl"
        official_status_path = evidence_dir / "OFFICIAL_CROP_STATUS.md"
        qc_report_path = evidence_dir / "p4_qc_report.csv"
        qc_html_path = evidence_dir / "p4_sanity_examples.html"
        if any(path.exists() for path in [official_summary_path, official_crop_index_path, official_frame_index_path, official_status_path]):
            assert official_summary_path.exists(), "missing official_crop_summary.json"
            assert official_crop_index_path.exists(), "missing official_crop_index.jsonl"
            assert official_frame_index_path.exists(), "missing official_frame_projection_index.jsonl"
            assert official_status_path.exists(), "missing OFFICIAL_CROP_STATUS.md"
            assert qc_report_path.exists(), "missing p4_qc_report.csv"
            assert qc_html_path.exists(), "missing p4_sanity_examples.html"
            official_summary = json.loads(official_summary_path.read_text(encoding="utf-8"))
            official_rows = read_jsonl(official_crop_index_path)
            official_frame_rows = read_jsonl(official_frame_index_path)
            assert official_summary["status"] == "official_relation_crop_metadata_ready"
            assert official_summary["selection_rule_version"] == "covisible_depth_ztest_v1_20260618_full_frame_mining"
            assert official_summary["n_relations"] == expected_relations
            assert len(official_rows) == expected_relations
            assert len(official_frame_rows) == official_summary["n_depth_tested_frame_rows"]
            assert official_summary["n_relations_crop_ready"] == sum(row["relation_crop_ready"] for row in official_rows)
            assert official_summary["n_relations_crop_ready"] > 0, "official crop layer has no ready relations"
            assert official_summary["depth_z_test_applied"] is True
            assert all(row["depth_z_test_applied"] is True for row in official_rows), "official crop rows must be depth-tested"
            assert all(row["selection_rule_version"] == official_summary["selection_rule_version"] for row in official_rows), "official crop rule mismatch"
            assert all(row["is_placeholder_rule"] is False for row in official_frame_rows), "official frame rows must not be placeholder"
            assert all(row["depth_z_test_applied"] is True for row in official_frame_rows), "official frame rows must be depth-tested"
            assert (evidence_dir / "qc_overlays").exists(), "missing qc_overlays directory"
            assert len(list((evidence_dir / "qc_overlays").glob("*.jpg"))) >= 1, "missing QC overlay images"

        full_perception_summary_path = evidence_dir / "full_perception_evidence_summary.json"
        full_perception_index_path = evidence_dir / "full_perception_evidence_index.jsonl"
        full_perception_status_path = evidence_dir / "FULL_PERCEPTION_EVIDENCE_STATUS.md"
        full_perception_image_dir = evidence_dir / "full_perception_evidence" / "images"
        if any(path.exists() for path in [full_perception_summary_path, full_perception_index_path, full_perception_status_path]):
            assert full_perception_summary_path.exists(), "missing full_perception_evidence_summary.json"
            assert full_perception_index_path.exists(), "missing full_perception_evidence_index.jsonl"
            assert full_perception_status_path.exists(), "missing FULL_PERCEPTION_EVIDENCE_STATUS.md"
            full_perception_summary = json.loads(full_perception_summary_path.read_text(encoding="utf-8"))
            full_perception_rows = read_jsonl(full_perception_index_path)
            assert full_perception_summary["status"] == "full_perception_evidence_ready"
            assert full_perception_summary["selection_rule_version"] == "full_perception_evidence_v1_20260618_rgbd_or_pointcloud"
            assert full_perception_summary["n_relations"] == expected_relations
            assert full_perception_summary["n_visual_evidence_ready"] == expected_relations
            assert len(full_perception_rows) == expected_relations
            assert all(row["visual_evidence_ready"] is True for row in full_perception_rows), "not all relations have visual evidence"
            assert all(row["evidence_tier"] in {"rgbd_crop_plus_pointcloud_render", "pointcloud_render_fallback"} for row in full_perception_rows), "unknown perception evidence tier"
            assert full_perception_summary["n_depth_tested_rgbd_crop_relations"] == sum(row["has_depth_tested_rgbd_crop"] for row in full_perception_rows)
            assert full_perception_summary["n_pointcloud_render_fallback_relations"] == sum(not row["has_depth_tested_rgbd_crop"] for row in full_perception_rows)
            if full_perception_summary.get("images_written"):
                assert full_perception_image_dir.exists(), "missing full perception image directory"
                image_count = len(list(full_perception_image_dir.glob("*/*.jpg")))
                assert image_count == expected_relations, f"expected {expected_relations} perception images, got {image_count}"
                for row in full_perception_rows:
                    assert (evidence_dir.parent / row["primary_visual_rel_path"]).exists(), f"missing perception image: {row['primary_visual_rel_path']}"

    expansion_dir = EXPORT_DIR / "expansion_v1"
    if expansion_dir.exists():
        required = [
            "README.md",
            "expansion_manifest_v1.json",
            "DENNIS_BENCHMARK_SIGNOFF_PACKET.md",
            "final_candidates/functional_balanced_116_frozen_candidate.jsonl",
            "final_candidates/minimal_pairs_expanded_60_frozen_candidate.jsonl",
            "perception_evidence/expansion_perception_evidence_summary.json",
            "perception_evidence/expansion_perception_evidence_index.jsonl",
            "ai_prereview_v1/ai_prereview_summary.json",
            "ai_prereview_v1/functional_ai_prereview_v1.csv",
            "ai_prereview_v1/minimal_pair_ai_prereview_v1.csv",
            "ai_prereview_v1/functional_ai_recommended_accept_v1.jsonl",
            "ai_prereview_v1/minimal_pair_ai_recommended_accept_v1.jsonl",
        ]
        for filename in required:
            assert (expansion_dir / filename).exists(), f"missing expansion_v1 file: {filename}"

        manifest = json.loads((expansion_dir / "expansion_manifest_v1.json").read_text(encoding="utf-8"))
        expansion_evidence_summary = json.loads((expansion_dir / "perception_evidence" / "expansion_perception_evidence_summary.json").read_text(encoding="utf-8"))
        prereview_summary = json.loads((expansion_dir / "ai_prereview_v1" / "ai_prereview_summary.json").read_text(encoding="utf-8"))
        freeze_functional_rows = read_jsonl(expansion_dir / "final_candidates" / "functional_balanced_116_frozen_candidate.jsonl")
        freeze_pair_rows = read_jsonl(expansion_dir / "final_candidates" / "minimal_pairs_expanded_60_frozen_candidate.jsonl")
        expansion_evidence_rows = read_jsonl(expansion_dir / "perception_evidence" / "expansion_perception_evidence_index.jsonl")
        prereview_functional_accept_rows = read_jsonl(expansion_dir / "ai_prereview_v1" / "functional_ai_recommended_accept_v1.jsonl")
        prereview_pair_accept_rows = read_jsonl(expansion_dir / "ai_prereview_v1" / "minimal_pair_ai_recommended_accept_v1.jsonl")

        with (expansion_dir / "ai_prereview_v1" / "functional_ai_prereview_v1.csv").open("r", encoding="utf-8", newline="") as f:
            prereview_functional_csv = list(__import__("csv").DictReader(f))
        with (expansion_dir / "ai_prereview_v1" / "minimal_pair_ai_prereview_v1.csv").open("r", encoding="utf-8", newline="") as f:
            prereview_pair_csv = list(__import__("csv").DictReader(f))

        assert manifest["status"] == "expansion_v1_clean_manifest_ready"
        assert manifest["paper_use_allowed"] is False
        freeze_summary = manifest["freeze_candidates"]
        assert freeze_summary["status"] == "freeze_candidates_ready_not_paper_frozen"
        assert freeze_summary["paper_use_allowed"] is False
        assert len(freeze_functional_rows) == freeze_summary["n_functional_candidates"] == 116
        assert len(freeze_pair_rows) == freeze_summary["n_minimal_pair_candidates"] == 60
        assert freeze_summary["functional_max_per_relation"] <= 15
        assert all(row.get("paper_use_allowed") is False for row in freeze_functional_rows), "freeze functional candidates must not be paper-enabled"
        assert all(row.get("human_review_required") is True for row in freeze_functional_rows), "freeze functional candidates require human review"
        assert all(row.get("dennis_signoff_required") is True for row in freeze_functional_rows), "freeze functional candidates require Dennis signoff"

        assert expansion_evidence_summary["status"] == "expansion_perception_evidence_ready"
        assert len(expansion_evidence_rows) == expansion_evidence_summary["n_functional_candidates"] == len(freeze_functional_rows)
        assert expansion_evidence_summary["n_visual_evidence_ready"] == len(freeze_functional_rows)
        assert expansion_evidence_summary["n_previously_missing_relations_now_have_pointcloud_evidence"] == freeze_summary["n_functional_needing_evidence_generation"]
        assert (EXPORT_DIR / "BENCHMARK_CLAIM_AUDIT.md").exists(), "missing BENCHMARK_CLAIM_AUDIT.md"

        assert prereview_summary["status"] == "ai_prereview_ready_not_human_annotation"
        assert prereview_summary["paper_use_allowed"] is False
        assert len(prereview_functional_csv) == prereview_summary["n_functional_reviewed"] == len(freeze_functional_rows)
        assert len(prereview_pair_csv) == prereview_summary["n_pair_reviewed"] == len(freeze_pair_rows)
        assert len(prereview_functional_accept_rows) == prereview_summary["n_functional_ai_accept"]
        assert len(prereview_pair_accept_rows) == prereview_summary["n_pair_ai_accept"]
        assert prereview_summary["n_functional_ai_accept"] > 0
        assert prereview_summary["n_functional_revise_wording"] > 0

        for row in freeze_functional_rows:
            qid = row["query_id"]
            scene_id = row["scene_id"]
            assert scene_id in candidates_by_scene, f"{qid}: scene has no candidates: {scene_id}"
            for target in row.get("target_node_ids") or []:
                assert target in candidates_by_scene[scene_id], f"{qid}: target not in candidates: {target}"
            assert set(row.get("candidate_node_ids") or []) == candidates_by_scene[scene_id], f"{qid}: embedded candidates mismatch scene candidates"

        freeze_functional_ids = {row["query_id"] for row in freeze_functional_rows}
        evidence_ids = {row["query_id"] for row in expansion_evidence_rows}
        assert evidence_ids == freeze_functional_ids, "expansion evidence rows must match freeze functional candidates"
        if expansion_evidence_summary.get("images_written"):
            for row in expansion_evidence_rows:
                assert (expansion_dir / row["primary_visual_rel_path"]).exists(), f"missing expansion evidence image: {row['primary_visual_rel_path']}"

        allowed_factors = {"spatial_qualifier", "anchor_object", "functional_relation"}
        pair_ids: set[str] = set()
        for row in freeze_pair_rows:
            pair_id = row.get("pair_id")
            assert pair_id and pair_id not in pair_ids, f"duplicate or missing expansion pair_id: {pair_id}"
            pair_ids.add(pair_id)
            assert row.get("changed_factor") in allowed_factors, f"{pair_id}: invalid changed_factor"
            assert row.get("paper_use_allowed") is False, f"{pair_id}: pair candidates must not be paper-enabled"



    release_dir = EXPORT_DIR / "fungraph_full_modality_release_v1"
    if release_dir.exists():
        required = [
            "README.md",
            "dataset_manifest.json",
            "dataset_unique_labels.json",
            "dataset_functional_labels.json",
            "dataset_unique_relations.json",
            "annotation_rules/functional_relation_taxonomy.json",
            "splits/functional_500.jsonl",
            "splits/human_133.jsonl",
            "splits/long_range_50.jsonl",
            "splits/minimal_pairs_28.jsonl",
            "splits/expansion_functional_116_candidates.jsonl",
            "splits/expansion_minimal_pairs_60_candidates.jsonl",
            "query_protocol_v1.md",
            "external/funthor_v1/README.md",
            "external/funthor_v1/funthor_manifest.json",
            "splits/funthor_functional_queries_v1.jsonl",
            "splits/funthor_minimal_pairs_v1.jsonl",
            "splits/funthor_functional_queries_factorized_v2.jsonl",
            "splits/fungraph_existing_queries_categorized_v2.jsonl",
            "fungraph_query_taxonomy_v2_summary.json",
        ]
        for filename in required:
            assert (release_dir / filename).exists(), f"missing full-modality release file: {filename}"

        release_manifest = json.loads((release_dir / "dataset_manifest.json").read_text(encoding="utf-8"))
        assert release_manifest["status"] == "fungraph_full_modality_release_ready"
        assert release_manifest["counts"]["n_scenes"] == len(candidates_by_scene)
        assert release_manifest["counts"]["n_candidate_nodes"] == sum(len(x) for x in candidates_by_scene.values())
        assert release_manifest["counts"]["n_frames"] == summary.get("n_frame_rgbd_camera_triplets", release_manifest["counts"]["n_frames"])
        assert release_manifest["counts"]["n_functional_relations"] >= 160
        assert release_manifest["counts"]["n_unique_relations"] >= 20

        expected_release_splits = {
            "functional_500": EXPECTED_COUNTS["functional_500_eval.jsonl"],
            "human_133": EXPECTED_COUNTS["human_133_eval.jsonl"],
            "long_range_50": EXPECTED_COUNTS["long_range_50_eval.jsonl"],
            "minimal_pairs_28": EXPECTED_COUNTS["minimal_pairs_28_eval.jsonl"],
            "expansion_functional_116_candidates": 116,
            "expansion_minimal_pairs_60_candidates": 60,
        }
        for split_name, expected in expected_release_splits.items():
            rows = read_jsonl(release_dir / "splits" / f"{split_name}.jsonl")
            assert len(rows) == expected, f"release split {split_name}: expected {expected}, got {len(rows)}"

        fungraph_taxonomy_summary = json.loads((release_dir / "fungraph_query_taxonomy_v2_summary.json").read_text(encoding="utf-8"))
        fungraph_categorized_rows = read_jsonl(release_dir / "splits" / "fungraph_existing_queries_categorized_v2.jsonl")
        assert fungraph_taxonomy_summary["status"] == "fungraph_existing_query_taxonomy_v2_ready"
        assert fungraph_taxonomy_summary["paper_use_allowed"] is False
        assert len(fungraph_categorized_rows) == fungraph_taxonomy_summary["counts"]["n_rows"] == 799
        assert release_manifest["counts"]["n_fungraph_existing_queries_categorized_v2"] == 799
        derived = release_manifest.get("derived_splits", {}).get("fungraph_existing_queries_categorized_v2")
        assert derived, "missing FunGraph categorized v2 derived split"
        assert derived["n_rows"] == 799
        assert derived["paper_use_allowed"] is False
        assert derived["axes"] == ["functional_query_type", "spatial_scope", "anchor_visibility"]
        assert set(fungraph_taxonomy_summary["counts"]["by_spatial_scope"]) == {"local", "remote"}
        assert set(fungraph_taxonomy_summary["counts"]["by_anchor_visibility"]) == {"anchor_explicit", "anchor_implicit", "anchor_hidden"}

        external = release_manifest.get("external_datasets", {}).get("funthor_v1")
        assert external, "missing FunTHOR external dataset entry in release manifest"
        assert external["paper_use_allowed"] is False
        assert external["n_scenes"] == 12
        assert external["n_functional_edges"] == 164
        assert external["n_generated_queries"] == 805
        assert external["n_generated_minimal_pairs"] == 200
        assert external["n_factorized_v2_queries"] == 1655
        assert external["factorized_v2_axes"] == ["functional_query_type", "spatial_scope", "anchor_visibility"]
        assert release_manifest["counts"]["n_external_funthor_queries"] == 805
        assert release_manifest["counts"]["n_external_funthor_minimal_pairs"] == 200
        assert release_manifest["counts"]["n_external_funthor_factorized_v2_queries"] == 1655
        assert release_manifest["counts"]["n_total_release_query_rows_including_external"] >= 3500

        funthor_manifest = json.loads((release_dir / "external" / "funthor_v1" / "funthor_manifest.json").read_text(encoding="utf-8"))
        assert funthor_manifest["status"] == "funthor_external_functional_extension_ready"
        assert funthor_manifest["counts"]["n_scenes"] == 12
        assert funthor_manifest["counts"]["n_functional_edges"] == 164
        assert funthor_manifest["counts"]["n_visible_endpoint_edges"] == 161
        assert funthor_manifest["counts"]["n_generated_queries"] == 805
        assert funthor_manifest["counts"]["n_generated_minimal_pairs"] == 200
        assert funthor_manifest["counts"]["n_factorized_v2_queries"] == 1655
        assert funthor_manifest["counts"]["n_unique_relations"] == 18
        assert funthor_manifest["factorized_v2"]["axes"] == ["functional_query_type", "spatial_scope", "anchor_visibility"]
        assert funthor_manifest["factorized_v2"]["paper_use_allowed"] is False

        funthor_queries = read_jsonl(release_dir / "splits" / "funthor_functional_queries_v1.jsonl")
        funthor_pairs = read_jsonl(release_dir / "splits" / "funthor_minimal_pairs_v1.jsonl")
        funthor_v2_queries = read_jsonl(release_dir / "splits" / "funthor_functional_queries_factorized_v2.jsonl")
        assert len(funthor_queries) == 805
        assert len(funthor_pairs) == 200
        assert len(funthor_v2_queries) == 1655
        funthor_query_ids = {row["query_id"] for row in funthor_queries}
        assert len(funthor_query_ids) == len(funthor_queries), "duplicate FunTHOR query ids"
        for row in funthor_queries:
            assert row["dataset"] == "funthor"
            assert row["paper_use_allowed"] is False
            assert row["human_review_required"] is True
            assert row["dennis_signoff_required"] is True
            assert row["target_node_id"] in set(row["candidate_node_ids"]), f"FunTHOR target outside candidate set: {row['query_id']}"
            assert row["query_family"] in {"functional_element_selection", "affected_object_selection"}
            assert row.get("functional_taxonomy", {}).get("relation_category"), f"FunTHOR query missing taxonomy: {row['query_id']}"
        for row in funthor_pairs:
            assert row["dataset"] == "funthor"
            assert row["paper_use_allowed"] is False
            assert row["query_a_id"] in funthor_query_ids
            assert row["query_b_id"] in funthor_query_ids

        allowed_query_types = {
            "functional_element_selection",
            "target_object_selection",
            "relation_verification",
            "state_change_goal_completion",
            "ambiguous_instance_minimal_pair",
            "functional_affordance_selection",
            "functional_consequence_prediction",
        }
        allowed_scopes = {"local", "remote"}
        allowed_anchor_visibility = {"anchor_explicit", "anchor_implicit", "anchor_hidden"}
        allowed_answer_formats = {"node_selection", "boolean", "text"}
        fungraph_categorized_ids = {row["query_id"] for row in fungraph_categorized_rows}
        assert len(fungraph_categorized_ids) == len(fungraph_categorized_rows), "duplicate FunGraph categorized v2 query ids"
        for row in fungraph_categorized_rows:
            qid = row["query_id"]
            assert row["dataset"] == "scenefun3d"
            assert row["generation_version"] == "existing_query_categorized_v2"
            assert row["taxonomy_review_status"] == "auto_labeled_needs_spot_check"
            assert row["paper_use_allowed"] is False
            assert row["human_review_required"] is True
            assert row["dennis_signoff_required"] is True
            assert row["functional_query_type"] in allowed_query_types, f"{qid}: invalid FunGraph query type"
            assert row["spatial_scope"] in allowed_scopes, f"{qid}: invalid FunGraph spatial scope"
            assert row["anchor_visibility"] in allowed_anchor_visibility, f"{qid}: invalid FunGraph anchor visibility"
            assert row["answer_format"] == "node_selection", f"{qid}: existing FunGraph rows must remain node-selection"
            assert row["functional_taxonomy"]["spatial_scope"] == row["spatial_scope"], f"{qid}: taxonomy scope mismatch"
            assert row["functional_taxonomy"]["anchor_visibility"] == row["anchor_visibility"], f"{qid}: taxonomy anchor mismatch"
            for target in row.get("target_node_ids") or []:
                assert target in set(row["candidate_node_ids"]), f"{qid}: target outside candidate set"

        funthor_v2_ids = {row["query_id"] for row in funthor_v2_queries}
        assert len(funthor_v2_ids) == len(funthor_v2_queries), "duplicate FunTHOR v2 query ids"
        assert {row["spatial_scope"] for row in funthor_v2_queries} == allowed_scopes
        assert {row["anchor_visibility"] for row in funthor_v2_queries} == allowed_anchor_visibility
        for row in funthor_v2_queries:
            qid = row["query_id"]
            assert row["dataset"] == "funthor"
            assert row["generation_version"] == "factorized_v2"
            assert row["paper_use_allowed"] is False
            assert row["human_review_required"] is True
            assert row["dennis_signoff_required"] is True
            assert row["functional_query_type"] in allowed_query_types, f"{qid}: invalid query type"
            assert row["spatial_scope"] in allowed_scopes, f"{qid}: invalid spatial scope"
            assert row["anchor_visibility"] in allowed_anchor_visibility, f"{qid}: invalid anchor visibility"
            assert row["answer_format"] in allowed_answer_formats, f"{qid}: invalid answer format"
            assert row["functional_taxonomy"]["spatial_scope"] == row["spatial_scope"], f"{qid}: taxonomy scope mismatch"
            assert row["functional_taxonomy"]["anchor_visibility"] == row["anchor_visibility"], f"{qid}: taxonomy anchor mismatch"
            assert row["target_node_ids"], f"{qid}: missing target_node_ids"
            for target in row["target_node_ids"]:
                assert target in set(row["candidate_node_ids"]), f"{qid}: target outside candidate set"
            if row["answer_format"] == "boolean":
                assert row.get("answer_boolean") is True, f"{qid}: boolean query must carry answer_boolean"
            if row["answer_format"] == "text":
                assert row.get("answer_text"), f"{qid}: text query must carry answer_text"

        scene_manifest = release_manifest["scene_manifest"]
        assert len(scene_manifest) == len(candidates_by_scene)
        for scene_row in scene_manifest:
            scene_id = str(scene_row["scene_id"])
            scene_json_path = release_dir / scene_row["scene_json"]
            frames_path = release_dir / scene_row["frames_jsonl"]
            assert scene_json_path.exists(), f"missing release scene package: {scene_json_path}"
            assert frames_path.exists(), f"missing release frame index: {frames_path}"
            scene_pkg = json.loads(scene_json_path.read_text(encoding="utf-8"))
            frame_rows = read_jsonl(frames_path)
            assert scene_pkg["scene_id"] == scene_id
            assert len(scene_pkg["node_list"]) == len(candidates_by_scene[scene_id])
            assert len(frame_rows) == scene_row["n_frames"] == scene_pkg["dataset"]["frame_summary"]["n_frames"]
            assert scene_pkg["readiness"]["full_scene_ready"] is True
            assert scene_pkg["readiness"]["funthor_style_raw_modalities_present"] is True
            assert scene_pkg["visible"]["visibility_stats"]["n_visible_nodes"] == len(scene_pkg["visible"]["node_ids"])
            assert all("point_annotation" in node for node in scene_pkg["node_list"]), f"{scene_id}: node missing point annotation pointer"

    print("3DGraphLLM export validation passed")


if __name__ == "__main__":
    main()
