#!/usr/bin/env python3
"""Build conservative freeze-candidate splits from expansion_v1.

These files are not paper-frozen human-reviewed splits. They are deterministic
freeze candidates that make the next human/Dennis review concrete.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
EXPANSION_DIR = EXPORT_DIR / "expansion_v1"
INTERMEDIATE_DIR = EXPANSION_DIR / "_intermediate"
FINAL_CANDIDATE_DIR = EXPANSION_DIR / "final_candidates"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def evidence_rank(row: dict[str, Any]) -> int:
    if row.get("has_depth_tested_rgbd_crop"):
        return 0
    if row.get("perception_evidence_tier") != "not_in_previous_export":
        return 1
    return 2


def build_functional_candidates() -> list[dict[str, Any]]:
    rows = read_jsonl(INTERMEDIATE_DIR / "balanced_unique_relation_candidate_v1.jsonl")
    out = []
    for idx, row in enumerate(rows):
        frozen = dict(row)
        frozen["split"] = "functional_balanced_116_frozen_candidate_v1"
        frozen["source"] = "balanced_openfungraph_unique_relation_frozen_candidate_v1"
        frozen["freeze_candidate_id"] = f"freeze_func_v1_{idx:04d}"
        frozen["freeze_status"] = "auto_selected_candidate_needs_human_signoff"
        frozen["paper_use_allowed"] = False
        frozen["human_review_required"] = True
        frozen["dennis_signoff_required"] = True
        out.append(frozen)
    return out


def build_minimal_pair_candidates(max_pairs: int = 60) -> list[dict[str, Any]]:
    rows = read_jsonl(INTERMEDIATE_DIR / "minimal_pair_candidates_v1.jsonl")
    rows = sorted(rows, key=lambda r: (r["changed_factor"], r["scene_id"], r.get("target_geom_diff_m") or 9999, r["pair_id"]))
    by_factor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_factor[row["changed_factor"]].append(row)

    selected: list[dict[str, Any]] = []
    # Keep all scarce scientific contrast types first, then fill with spatial pairs.
    for factor in ["functional_relation", "anchor_object"]:
        selected.extend(by_factor.get(factor, []))
    remaining = max_pairs - len(selected)
    selected.extend(by_factor.get("spatial_qualifier", [])[: max(0, remaining)])
    selected = selected[:max_pairs]

    out = []
    for idx, row in enumerate(selected):
        frozen = dict(row)
        frozen["freeze_candidate_id"] = f"freeze_minpair_v1_{idx:04d}"
        frozen["split"] = "minimal_pairs_expanded_60_frozen_candidate_v1"
        frozen["freeze_status"] = "auto_selected_candidate_needs_human_signoff"
        frozen["paper_use_allowed"] = False
        frozen["human_review_required"] = True
        frozen["dennis_signoff_required"] = True
        out.append(frozen)
    return out


def write_status(summary: dict[str, Any]) -> None:
    lines = [
        "# Expansion Freeze Candidate v1 Status",
        "",
        "These files are deterministic freeze candidates, not final paper-frozen benchmark splits.",
        "They are intended for human review, Dennis signoff, and evidence checking.",
        "",
        "## Functional Candidate Split",
        "",
        f"- Candidate rows: {summary['n_functional_candidates']}",
        f"- Exact relation types: {summary['n_functional_relation_types']}",
        f"- Max rows per exact relation: {summary['functional_max_per_relation']}",
        f"- Rows still needing evidence generation: {summary['n_functional_needing_evidence_generation']}",
        "",
        "## Minimal-Pair Candidate Split",
        "",
        f"- Candidate pairs: {summary['n_minimal_pair_candidates']}",
        f"- Changed-factor distribution: {summary['minimal_pair_changed_factor_counts']}",
        "",
        "## Boundary",
        "",
        "Do not report these as final benchmark results until review_decision fields are filled, evidence exists, and Dennis signs off.",
    ]
    (INTERMEDIATE_DIR / "FROZEN_CANDIDATE_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    functional = build_functional_candidates()
    minimal_pairs = build_minimal_pair_candidates()
    relation_counts = Counter(row["supporting_edge_ids"][0].split("|")[1] for row in functional)
    pair_counts = Counter(row["changed_factor"] for row in minimal_pairs)
    summary = {
        "status": "freeze_candidates_ready_not_paper_frozen",
        "n_functional_candidates": len(functional),
        "n_functional_relation_types": len(relation_counts),
        "functional_max_per_relation": max(relation_counts.values()) if relation_counts else 0,
        "n_functional_needing_evidence_generation": sum(bool(row.get("needs_evidence_generation")) for row in functional),
        "functional_relation_counts": dict(relation_counts.most_common()),
        "n_minimal_pair_candidates": len(minimal_pairs),
        "minimal_pair_changed_factor_counts": dict(pair_counts.most_common()),
        "paper_use_allowed": False,
        "required_before_paper_use": [
            "human query wording review",
            "minimal-pair validity review",
            "perception evidence completion",
            "Dennis signoff",
        ],
    }
    write_jsonl(FINAL_CANDIDATE_DIR / "functional_balanced_116_frozen_candidate.jsonl", functional)
    write_jsonl(FINAL_CANDIDATE_DIR / "minimal_pairs_expanded_60_frozen_candidate.jsonl", minimal_pairs)
    write_json(INTERMEDIATE_DIR / "freeze_candidate_summary.json", summary)
    write_status(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
