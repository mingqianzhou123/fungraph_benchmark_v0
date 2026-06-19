#!/usr/bin/env python3
"""AI pre-review for expansion freeze candidates.

This is a triage layer, not final human annotation. It flags wording/evidence/pair
risks and prepares a short Dennis signoff packet.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
EXPANSION_DIR = EXPORT_DIR / "expansion_v1"
PREREVIEW_DIR = EXPANSION_DIR / "ai_prereview_v1"

SLASHY = re.compile(r"\s/\s")
DOUBLE_SPACE = re.compile(r"\s{2,}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def clean_label(label: str | None) -> str:
    return (label or "").replace(" / ", "/").strip().lower()


def review_query(row: dict[str, Any], evidence_by_qid: dict[str, dict[str, Any]]) -> dict[str, Any]:
    text = row.get("query_text") or ""
    target = row.get("target_label") or ""
    anchor = row.get("anchor_label") or ""
    relation = (row.get("supporting_edge_ids") or ["||"])[0].split("|")[1]
    evidence = evidence_by_qid.get(row["query_id"], {})
    flags: list[str] = []
    score = 100

    if not evidence.get("visual_evidence_ready"):
        flags.append("missing_visual_evidence")
        score -= 50
    if evidence.get("was_missing_from_previous_full_perception_export"):
        flags.append("new_expansion_relation_pointcloud_only")
        score -= 8
    if not evidence.get("has_previous_depth_tested_rgbd_crop"):
        flags.append("no_depth_tested_rgbd_crop")
        score -= 4
    if SLASHY.search(text) or SLASHY.search(target) or SLASHY.search(anchor):
        flags.append("slash_label_needs_wording_cleanup")
        score -= 12
    if DOUBLE_SPACE.search(text):
        flags.append("double_space_wording_bug")
        score -= 10
    if "perform '" in text:
        flags.append("fallback_template_wording")
        score -= 20
    if len(text) > 130:
        flags.append("overlong_query")
        score -= 8
    if clean_label(target) and clean_label(target) not in clean_label(text):
        flags.append("target_label_not_in_query_text")
        score -= 15
    if clean_label(anchor) and clean_label(anchor).split("/")[0] not in clean_label(text):
        flags.append("anchor_label_not_in_query_text")
        score -= 8
    if row.get("target_label") in {"knob", "handle", "remote"} and "same_label_disambiguation" in row.get("difficulty_tags", []):
        flags.append("same_label_disambiguation_requires_visual_check")
        score -= 4
    if relation in {"press or rotate to  control the water flow"}:
        flags.append("source_relation_has_spacing_typo")
        score -= 12

    if "missing_visual_evidence" in flags:
        decision = "reject_until_evidence_fixed"
    elif any(flag in flags for flag in ["fallback_template_wording", "double_space_wording_bug", "source_relation_has_spacing_typo"]):
        decision = "revise_wording_before_signoff"
    elif "slash_label_needs_wording_cleanup" in flags:
        decision = "revise_wording_before_signoff"
    elif score >= 88:
        decision = "ai_recommend_accept_after_human_spotcheck"
    else:
        decision = "needs_human_review"

    reviewed = dict(row)
    reviewed.update({
        "relation": relation,
        "ai_prereview_decision": decision,
        "ai_prereview_score": max(0, score),
        "ai_prereview_flags": flags,
        "ai_prereview_notes": "; ".join(flags) if flags else "no obvious automatic issue detected",
        "paper_use_allowed": False,
        "human_review_required": True,
        "dennis_signoff_required": True,
        "review_layer": "ai_prereview_v1_not_human_annotation",
    })
    return reviewed


def review_pair(row: dict[str, Any], draft_ids: set[str], functional_candidate_ids: set[str]) -> dict[str, Any]:
    flags: list[str] = []
    score = 100
    qa = row.get("query_a_id")
    qb = row.get("query_b_id")
    if qa not in draft_ids or qb not in draft_ids:
        flags.append("query_id_not_in_expansion_draft")
        score -= 60
    if qa not in functional_candidate_ids or qb not in functional_candidate_ids:
        flags.append("pair_endpoint_not_in_116_functional_candidate_split")
        score -= 20
    if row.get("target_a_node_id") == row.get("target_b_node_id"):
        flags.append("same_target_answer_not_useful_for_object_selection_contrast")
        score -= 28
    if row.get("changed_factor") == "spatial_qualifier" and (row.get("target_geom_diff_m") or 0) < 0.25:
        flags.append("small_spatial_separation")
        score -= 18
    if row.get("changed_factor") == "anchor_object" and row.get("anchor_a_node_id") == row.get("anchor_b_node_id"):
        flags.append("anchor_object_factor_not_changed")
        score -= 50
    if row.get("changed_factor") == "functional_relation" and row.get("relation_a") == row.get("relation_b"):
        flags.append("functional_relation_factor_not_changed")
        score -= 50
    if row.get("target_label") in {"knob", "handle"}:
        flags.append("high_frequency_target_label")
        score -= 3

    if any(flag.endswith("not_changed") for flag in flags) or "query_id_not_in_expansion_draft" in flags:
        decision = "reject_candidate"
    elif "same_target_answer_not_useful_for_object_selection_contrast" in flags:
        decision = "needs_human_review_not_primary_pair"
    elif "pair_endpoint_not_in_116_functional_candidate_split" in flags:
        decision = "keep_as_secondary_diagnostic_only"
    elif score >= 82:
        decision = "ai_recommend_accept_after_human_spotcheck"
    else:
        decision = "needs_human_review"

    reviewed = dict(row)
    reviewed.update({
        "ai_prereview_decision": decision,
        "ai_prereview_score": max(0, score),
        "ai_prereview_flags": flags,
        "ai_prereview_notes": "; ".join(flags) if flags else "no obvious automatic issue detected",
        "paper_use_allowed": False,
        "human_review_required": True,
        "dennis_signoff_required": True,
        "review_layer": "ai_prereview_v1_not_human_annotation",
    })
    return reviewed


def summarize(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(row.get(key) for row in rows).most_common())


def write_status(summary: dict[str, Any]) -> None:
    lines = [
        "# AI Pre-Review v1 Status",
        "",
        "This directory contains automatic triage for expansion freeze candidates. It is not human annotation and does not enable paper use.",
        "",
        "## Functional Candidates",
        "",
        f"- Reviewed: {summary['n_functional_reviewed']}",
        f"- AI recommended accept after spot-check: {summary['n_functional_ai_accept']}",
        f"- Need wording revision: {summary['n_functional_revise_wording']}",
        f"- Need human review: {summary['n_functional_needs_review']}",
        "",
        "## Minimal Pairs",
        "",
        f"- Reviewed: {summary['n_pair_reviewed']}",
        f"- AI recommended accept after spot-check: {summary['n_pair_ai_accept']}",
        f"- Secondary diagnostic only: {summary['n_pair_secondary_only']}",
        f"- Need human review or reject: {summary['n_pair_needs_review_or_reject']}",
        "",
        "## Boundary",
        "",
        "All outputs keep `paper_use_allowed=false`. Dennis signoff is still required for any paper-grade split.",
    ]
    (PREREVIEW_DIR / "AI_PREREVIEW_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_dennis_packet(summary: dict[str, Any], functional: list[dict[str, Any]], pairs: list[dict[str, Any]]) -> None:
    relation_counts = Counter((row.get("supporting_edge_ids") or ["||"])[0].split("|")[1] for row in functional)
    accepted_functional = [r for r in functional if r["ai_prereview_decision"] == "ai_recommend_accept_after_human_spotcheck"]
    revise_examples = [r for r in functional if r["ai_prereview_decision"] == "revise_wording_before_signoff"][:12]
    pair_accept = [r for r in pairs if r["ai_prereview_decision"] == "ai_recommend_accept_after_human_spotcheck"]
    pair_secondary = [r for r in pairs if r["ai_prereview_decision"] == "keep_as_secondary_diagnostic_only"]
    lines = [
        "# Dennis Benchmark Signoff Packet - AI Pre-Review v1",
        "",
        "This packet prepares a decision point. It does not replace Dennis signoff.",
        "",
        "## Recommended Decisions",
        "",
        "1. Approve the benchmark structure if you agree with a two-level evaluation: old frozen 683-row export for reproduction, and reviewed expansion candidates for stronger diagnostics.",
        "2. Do not call the 116 functional candidates final until wording review is accepted.",
        "3. Treat the minimal-pair candidates as diagnostics, not primary leaderboard rows, unless pair validity is manually confirmed.",
        "",
        "## Functional Candidate Triage",
        "",
        f"- Total functional freeze candidates: {summary['n_functional_reviewed']}",
        f"- AI recommended accept after human spot-check: {summary['n_functional_ai_accept']}",
        f"- Need wording revision before signoff: {summary['n_functional_revise_wording']}",
        f"- Need broader human review: {summary['n_functional_needs_review']}",
        f"- Exact relation types: {len(relation_counts)}",
        "",
        "Primary risk: many source labels contain slash-style merged labels such as `dresser / chest of drawers`; these are valid object labels but awkward natural language, so they should be rewritten before paper release.",
        "",
        "## Minimal-Pair Triage",
        "",
        f"- Total pair candidates: {summary['n_pair_reviewed']}",
        f"- AI recommended accept after human spot-check: {summary['n_pair_ai_accept']}",
        f"- Secondary diagnostic only: {summary['n_pair_secondary_only']}",
        f"- Need review or reject: {summary['n_pair_needs_review_or_reject']}",
        "",
        "Primary risk: several auto-mined pairs do not both belong to the 116 functional candidate split, and a few anchor-object pairs keep the same target answer. These are useful diagnostics but weak as primary paper evidence.",
        "",
        "## Files To Inspect",
        "",
        "- `expansion_v1/ai_prereview_v1/functional_ai_prereview_v1.csv`",
        "- `expansion_v1/ai_prereview_v1/minimal_pair_ai_prereview_v1.csv`",
        "- `expansion_v1/ai_prereview_v1/functional_ai_recommended_accept_v1.jsonl`",
        "- `expansion_v1/ai_prereview_v1/minimal_pair_ai_recommended_accept_v1.jsonl`",
        "",
        "## Example Wording Revisions Needed",
        "",
    ]
    for row in revise_examples:
        lines.append(f"- `{row['query_id']}`: {row['query_text']}")
    lines.extend([
        "",
        "## Signoff Questions",
        "",
        "1. Should slash-label objects be rewritten into one canonical human-facing label before final split release?",
        "2. Should expansion rows without previous depth-tested RGB-D crop metadata remain in the final split if they have pointcloud-render evidence?",
        "3. Should minimal pairs be reported as a separate diagnostic table rather than merged into the main benchmark score?",
        "4. Is the paper claim allowed to say `195 unique source functional relation instances` and `116 reviewed balanced candidates`, while avoiding `500 independent functional relations`?",
        "",
        "## Current Guardrail",
        "",
        "All AI pre-review outputs keep `paper_use_allowed=false`. A later human-reviewed manifest must explicitly record Dennis approval before paper use.",
    ])
    (EXPANSION_DIR / "DENNIS_BENCHMARK_SIGNOFF_PACKET.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    PREREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    functional = read_jsonl(EXPANSION_DIR / "functional_balanced_116_frozen_candidate.jsonl")
    pairs = read_jsonl(EXPANSION_DIR / "minimal_pairs_expanded_60_frozen_candidate.jsonl")
    draft_ids = {row["query_id"] for row in read_jsonl(EXPANSION_DIR / "functional_unique_relation_585_draft.jsonl")}
    functional_candidate_ids = {row["query_id"] for row in functional}
    evidence_by_qid = {row["query_id"]: row for row in read_jsonl(EXPANSION_DIR / "perception_evidence" / "expansion_perception_evidence_index.jsonl")}

    reviewed_functional = [review_query(row, evidence_by_qid) for row in functional]
    reviewed_pairs = [review_pair(row, draft_ids, functional_candidate_ids) for row in pairs]
    accepted_functional = [row for row in reviewed_functional if row["ai_prereview_decision"] == "ai_recommend_accept_after_human_spotcheck"]
    accepted_pairs = [row for row in reviewed_pairs if row["ai_prereview_decision"] == "ai_recommend_accept_after_human_spotcheck"]

    summary = {
        "status": "ai_prereview_ready_not_human_annotation",
        "paper_use_allowed": False,
        "n_functional_reviewed": len(reviewed_functional),
        "n_functional_ai_accept": len(accepted_functional),
        "n_functional_revise_wording": sum(row["ai_prereview_decision"] == "revise_wording_before_signoff" for row in reviewed_functional),
        "n_functional_needs_review": sum(row["ai_prereview_decision"] == "needs_human_review" for row in reviewed_functional),
        "functional_decision_counts": summarize(reviewed_functional, "ai_prereview_decision"),
        "functional_flag_counts": dict(Counter(flag for row in reviewed_functional for flag in row["ai_prereview_flags"]).most_common()),
        "n_pair_reviewed": len(reviewed_pairs),
        "n_pair_ai_accept": len(accepted_pairs),
        "n_pair_secondary_only": sum(row["ai_prereview_decision"] == "keep_as_secondary_diagnostic_only" for row in reviewed_pairs),
        "n_pair_needs_review_or_reject": sum(row["ai_prereview_decision"] in {"needs_human_review", "needs_human_review_not_primary_pair", "reject_candidate"} for row in reviewed_pairs),
        "pair_decision_counts": summarize(reviewed_pairs, "ai_prereview_decision"),
        "pair_flag_counts": dict(Counter(flag for row in reviewed_pairs for flag in row["ai_prereview_flags"]).most_common()),
        "required_before_paper_use": ["human wording review", "evidence spot-check", "Dennis signoff", "final paper manifest"],
    }

    write_json(PREREVIEW_DIR / "ai_prereview_summary.json", summary)
    write_jsonl(PREREVIEW_DIR / "functional_ai_prereview_v1.jsonl", reviewed_functional)
    write_jsonl(PREREVIEW_DIR / "minimal_pair_ai_prereview_v1.jsonl", reviewed_pairs)
    write_jsonl(PREREVIEW_DIR / "functional_ai_recommended_accept_v1.jsonl", accepted_functional)
    write_jsonl(PREREVIEW_DIR / "minimal_pair_ai_recommended_accept_v1.jsonl", accepted_pairs)
    write_csv(
        PREREVIEW_DIR / "functional_ai_prereview_v1.csv",
        reviewed_functional,
        ["freeze_candidate_id", "query_id", "ai_prereview_decision", "ai_prereview_score", "ai_prereview_flags", "scene_id", "target_label", "relation", "anchor_label", "query_text", "perception_evidence_tier", "has_depth_tested_rgbd_crop", "needs_evidence_generation", "paper_use_allowed"],
    )
    write_csv(
        PREREVIEW_DIR / "minimal_pair_ai_prereview_v1.csv",
        reviewed_pairs,
        ["freeze_candidate_id", "pair_id", "ai_prereview_decision", "ai_prereview_score", "ai_prereview_flags", "changed_factor", "scene_id", "target_label", "relation_a", "relation_b", "anchor_a_label", "anchor_b_label", "target_geom_diff_m", "query_a_id", "query_b_id", "paper_use_allowed"],
    )
    write_status(summary)
    write_dennis_packet(summary, reviewed_functional, reviewed_pairs)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
