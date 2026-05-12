"""Phase 2: Node-Level Geometry Feature Bank for SceneFun3D nodes.

Reads (read-only):
  - benchmark_clean_v0/geometry/scenefun3d_node_geom.json

Writes:
  - benchmark_clean_v0/multimodal_extension/node_geometry_features.csv
  - benchmark_clean_v0/multimodal_extension/node_geometry_features.pt
  - benchmark_clean_v0/multimodal_extension/feature_index.json

Design decisions (confirmed by Mingqian, 2026-05-11):
  1. Height axis is y (data evidence: y ranges 2-7m around 0; z has 100-380m global offset).
     -> height = bbox_size_y (NOT size_z).
  2. scene_normalized uses 方案 C (gravity-aligned hierarchical):
       - Horizontal (x, z): min-max normalize within scene AABB -> [0, 1].
       - Vertical (y): preserve absolute meters relative to scene's lowest node.
  3. .pt file format: dict with features tensor + columns + ids + row index.

Usage:
  python phase2_node_geometry_features.py
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import torch

# --- Paths ---
SCRIPT_DIR = Path(__file__).resolve().parent       # multimodal_extension/scripts/
EXT_DIR    = SCRIPT_DIR.parent                      # multimodal_extension/
REPO_ROOT  = EXT_DIR.parent                         # benchmark_clean_v0/

GEOM_PATH  = REPO_ROOT / "geometry" / "scenefun3d_node_geom.json"
OUT_CSV    = EXT_DIR / "node_geometry_features.csv"
OUT_PT     = EXT_DIR / "node_geometry_features.pt"
OUT_INDEX  = EXT_DIR / "feature_index.json"

# --- Feature column contract (FROZEN: append-only, never insert/delete/reorder) ---
NODE_FEATURE_COLUMNS = [
    # --- Identifiers (2) ---
    "scene_id",
    "node_id",

    # --- Coverage flag (1) ---
    "has_bbox",

    # --- Raw bbox (9) ---
    "bbox_center_x", "bbox_center_y", "bbox_center_z",
    "bbox_min_x",    "bbox_min_y",    "bbox_min_z",
    "bbox_max_x",    "bbox_max_y",    "bbox_max_z",

    # --- Size derivatives (6) ---
    "bbox_size_x", "bbox_size_y", "bbox_size_z",
    "bbox_volume",
    "bbox_diagonal",
    "height",                          # = bbox_size_y (y-up convention)

    # --- Scene-relative (6, 方案 C: horizontal normalized; vertical in meters) ---
    "scene_normalized_center_x",       # (center_x - scene_min_x) / scene_extent_x  in [0,1]
    "height_from_floor_m",             # center_y - scene_min_y (meters, absolute scale)
    "scene_normalized_center_z",       # (center_z - scene_min_z) / scene_extent_z  in [0,1]
    "scene_normalized_size_x",         # size_x / scene_extent_x
    "bbox_size_y_m",                   # size_y in meters (absolute, equals bbox_size_y/height)
    "scene_normalized_size_z",         # size_z / scene_extent_z
]

NUMERIC_COLUMNS = NODE_FEATURE_COLUMNS[2:]   # 22 numeric columns (incl. has_bbox as float)

EPS = 1e-9


def safe_norm(val: float, scene_min_d: float, scene_size_d: float) -> float:
    """Min-max normalize; fall back to 0.0 if scene extent is degenerate."""
    if scene_size_d > EPS:
        return (val - scene_min_d) / scene_size_d
    return 0.0


def safe_size_ratio(size_d: float, scene_size_d: float) -> float:
    """size_d / scene_size_d with degenerate-axis fallback."""
    if scene_size_d > EPS:
        return size_d / scene_size_d
    return 0.0


def load_geometry(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compute_scene_bboxes(geom: dict) -> dict[str, dict[str, list[float]]]:
    """For each scene, compute the axis-aligned bbox over all its nodes."""
    scene_bboxes = {}
    for scene_id, nodes in geom.items():
        if not nodes:
            continue
        all_mins = [v["bbox_min"] for v in nodes.values()]
        all_maxs = [v["bbox_max"] for v in nodes.values()]
        scene_min  = [min(r[d] for r in all_mins) for d in range(3)]
        scene_max  = [max(r[d] for r in all_maxs) for d in range(3)]
        scene_size = [scene_max[d] - scene_min[d] for d in range(3)]
        scene_bboxes[scene_id] = {
            "min":  scene_min,
            "max":  scene_max,
            "size": scene_size,
        }
    return scene_bboxes


def compute_node_features(
    geom: dict,
    scene_bboxes: dict[str, dict[str, list[float]]],
) -> tuple[list[dict], dict[str, dict]]:
    """Return (rows, feature_index)."""
    rows: list[dict] = []
    feature_index: dict[str, dict] = {}
    row_idx = 0

    for scene_id in sorted(geom.keys()):
        s_min  = scene_bboxes[scene_id]["min"]
        s_size = scene_bboxes[scene_id]["size"]

        for node_id in sorted(geom[scene_id].keys()):
            g = geom[scene_id][node_id]
            center = g["bbox_center"]
            bmin   = g["bbox_min"]
            bmax   = g["bbox_max"]

            size     = [bmax[d] - bmin[d] for d in range(3)]
            volume   = size[0] * size[1] * size[2]
            diagonal = math.sqrt(size[0] ** 2 + size[1] ** 2 + size[2] ** 2)
            height   = size[1]                           # y-up

            # 方案 C：x, z horizontal min-max; y absolute meters
            norm_center_x = safe_norm(center[0], s_min[0], s_size[0])
            norm_center_z = safe_norm(center[2], s_min[2], s_size[2])
            height_from_floor_m = center[1] - s_min[1]

            norm_size_x = safe_size_ratio(size[0], s_size[0])
            norm_size_z = safe_size_ratio(size[2], s_size[2])
            size_y_m    = size[1]

            key = f"{scene_id}/{node_id}"
            assert key not in feature_index, f"duplicate key: {key}"

            rows.append({
                "scene_id": scene_id,
                "node_id":  node_id,
                "has_bbox": True,
                "bbox_center_x": center[0],
                "bbox_center_y": center[1],
                "bbox_center_z": center[2],
                "bbox_min_x":    bmin[0],
                "bbox_min_y":    bmin[1],
                "bbox_min_z":    bmin[2],
                "bbox_max_x":    bmax[0],
                "bbox_max_y":    bmax[1],
                "bbox_max_z":    bmax[2],
                "bbox_size_x":   size[0],
                "bbox_size_y":   size[1],
                "bbox_size_z":   size[2],
                "bbox_volume":   volume,
                "bbox_diagonal": diagonal,
                "height":        height,
                "scene_normalized_center_x": norm_center_x,
                "height_from_floor_m":       height_from_floor_m,
                "scene_normalized_center_z": norm_center_z,
                "scene_normalized_size_x":   norm_size_x,
                "bbox_size_y_m":             size_y_m,
                "scene_normalized_size_z":   norm_size_z,
            })
            feature_index[key] = {
                "scene_id":    scene_id,
                "node_id":     node_id,
                "feature_row": row_idx,
                "has_bbox":    True,
            }
            row_idx += 1

    return rows, feature_index


def save_csv(rows: list[dict], path: Path) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=NODE_FEATURE_COLUMNS)
    df.to_csv(path, index=False, encoding="utf-8")
    return df


def save_pt(df: pd.DataFrame, path: Path, feature_index: dict[str, dict]) -> torch.Tensor:
    # has_bbox (bool) -> float; numeric columns float32
    numeric_df = df[NUMERIC_COLUMNS].copy()
    numeric_df["has_bbox"] = numeric_df["has_bbox"].astype(float)
    features = torch.tensor(numeric_df.to_numpy(dtype="float32"), dtype=torch.float32)

    payload = {
        "features":          features,
        "columns":           list(NUMERIC_COLUMNS),
        "scene_ids":         df["scene_id"].tolist(),
        "node_ids":          df["node_id"].tolist(),
        "feature_row_index": feature_index,
    }
    torch.save(payload, path)
    return features


def save_index(feature_index: dict[str, dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(feature_index, f, indent=2, ensure_ascii=False)


def verify(
    df: pd.DataFrame,
    features: torch.Tensor,
    feature_index: dict[str, dict],
    geom: dict,
) -> list[str]:
    """Run all sanity checks. Returns list of failure messages (empty if all pass)."""
    failures: list[str] = []
    n_nodes_expected = sum(len(v) for v in geom.values())

    def check(label: str, cond: bool, detail: str = "") -> None:
        status = "pass" if cond else "FAIL"
        suffix = f"  ({detail})" if detail else ""
        print(f"[CHECK] {label}: {status}{suffix}")
        if not cond:
            failures.append(f"{label}{(' - ' + detail) if detail else ''}")

    # 1. Row count
    check("CSV row count == geom node count",
          len(df) == n_nodes_expected,
          f"got {len(df)}, expected {n_nodes_expected}")

    # 2. Column count
    check("CSV column count == 24",
          len(df.columns) == 24,
          f"got {len(df.columns)}")

    # 3. has_bbox all True
    check("all has_bbox == True", bool(df["has_bbox"].all()))

    # 4. No NaN
    nan_count = df[NUMERIC_COLUMNS].isna().sum().sum()
    check("NaN count == 0", nan_count == 0, f"{int(nan_count)} NaN cells")

    # 5. scene_normalized_center_x / _z range (horizontal axes only under 方案 C)
    for col in ["scene_normalized_center_x", "scene_normalized_center_z"]:
        vmin, vmax = float(df[col].min()), float(df[col].max())
        in_range = (vmin >= -EPS) and (vmax <= 1.0 + EPS)
        check(f"{col} in [0,1]", in_range, f"min={vmin:.4f}, max={vmax:.4f}")

    # 5b. height_from_floor_m sanity: >=0 (lowest node is at floor=0)
    hmin = float(df["height_from_floor_m"].min())
    hmax = float(df["height_from_floor_m"].max())
    check("height_from_floor_m >= 0",
          hmin >= -EPS,
          f"min={hmin:.4f}, max={hmax:.4f}")

    # 6. scene_normalized_size >= 0
    for col in ["scene_normalized_size_x", "scene_normalized_size_z"]:
        vmin = float(df[col].min())
        check(f"{col} >= 0", vmin >= -EPS, f"min={vmin:.6f}")
    check("bbox_size_y_m >= 0",
          float(df["bbox_size_y_m"].min()) >= -EPS,
          f"min={float(df['bbox_size_y_m'].min()):.6f}")

    # 7. bbox_volume >= 0
    check("bbox_volume >= 0",
          float(df["bbox_volume"].min()) >= -EPS,
          f"min={float(df['bbox_volume'].min()):.6f}")

    # 8. feature_index key count
    check("feature_index key count == n_nodes",
          len(feature_index) == n_nodes_expected,
          f"got {len(feature_index)}")

    # 9. feature_row is a complete consecutive set
    row_set = {v["feature_row"] for v in feature_index.values()}
    check("feature_row == set(range(n))",
          row_set == set(range(n_nodes_expected)),
          f"missing or duplicate rows")

    # 10. Tensor / CSV alignment + manual recomputation on first 5 nodes
    sample_keys = list(feature_index.keys())[:5]
    max_diff = 0.0
    for key in sample_keys:
        row = feature_index[key]["feature_row"]
        scene_id = feature_index[key]["scene_id"]
        node_id  = feature_index[key]["node_id"]
        g = geom[scene_id][node_id]

        # Manual recomputation
        size_manual = [g["bbox_max"][d] - g["bbox_min"][d] for d in range(3)]
        vol_manual  = size_manual[0] * size_manual[1] * size_manual[2]
        diag_manual = math.sqrt(sum(s ** 2 for s in size_manual))

        csv_row = df.iloc[row]
        diffs = [
            abs(csv_row["bbox_center_x"] - g["bbox_center"][0]),
            abs(csv_row["bbox_center_y"] - g["bbox_center"][1]),
            abs(csv_row["bbox_center_z"] - g["bbox_center"][2]),
            abs(csv_row["bbox_size_x"]   - size_manual[0]),
            abs(csv_row["bbox_size_y"]   - size_manual[1]),
            abs(csv_row["bbox_size_z"]   - size_manual[2]),
            abs(csv_row["bbox_volume"]   - vol_manual),
            abs(csv_row["bbox_diagonal"] - diag_manual),
            abs(csv_row["height"]        - size_manual[1]),
        ]
        max_diff = max(max_diff, max(diffs))

        # CSV vs tensor
        tensor_row = features[row].tolist()
        for i, col in enumerate(NUMERIC_COLUMNS):
            csv_val = float(csv_row[col]) if col != "has_bbox" else float(bool(csv_row[col]))
            assert abs(tensor_row[i] - csv_val) < 1e-4, \
                f"mismatch at row {row}, col {col}: tensor={tensor_row[i]} csv={csv_val}"

    check("manual recomputation diff < 1e-5", max_diff < 1e-5,
          f"max_diff={max_diff:.2e}")

    # Print ranges for visual inspection
    print()
    print("[ranges]")
    print(f"  scene_normalized_center_x: [{df['scene_normalized_center_x'].min():.4f}, "
          f"{df['scene_normalized_center_x'].max():.4f}]")
    print(f"  scene_normalized_center_z: [{df['scene_normalized_center_z'].min():.4f}, "
          f"{df['scene_normalized_center_z'].max():.4f}]")
    print(f"  height_from_floor_m:       [{df['height_from_floor_m'].min():.4f}, "
          f"{df['height_from_floor_m'].max():.4f}] meters")
    print(f"  height:                    [{df['height'].min():.4f}, "
          f"{df['height'].max():.4f}] meters")
    print(f"  bbox_volume:               [{df['bbox_volume'].min():.4e}, "
          f"{df['bbox_volume'].max():.4e}]")

    return failures


def main() -> None:
    print(f"[Phase 2] Node-Level Geometry Feature Bank")
    print(f"[Phase 2] Started at {datetime.now(timezone.utc).isoformat()}")
    print(f"[Phase 2] Input:  {GEOM_PATH}")
    print(f"[Phase 2] Output: {EXT_DIR}")
    print()

    geom = load_geometry(GEOM_PATH)
    n_scenes = len(geom)
    n_nodes  = sum(len(v) for v in geom.values())
    print(f"[load] {n_scenes} scenes, {n_nodes} nodes")

    scene_bboxes = compute_scene_bboxes(geom)
    rows, feature_index = compute_node_features(geom, scene_bboxes)
    print(f"[compute] produced {len(rows)} feature rows")

    df = save_csv(rows, OUT_CSV)
    print(f"[write] {OUT_CSV.name} ({len(df)} rows x {len(df.columns)} cols)")

    features = save_pt(df, OUT_PT, feature_index)
    print(f"[write] {OUT_PT.name} (features tensor: {tuple(features.shape)}, dtype={features.dtype})")

    save_index(feature_index, OUT_INDEX)
    print(f"[write] {OUT_INDEX.name} ({len(feature_index)} keys)")
    print()

    failures = verify(df, features, feature_index, geom)
    print()
    if failures:
        print(f"[Phase 2] FAILED {len(failures)} check(s):")
        for msg in failures:
            print(f"  - {msg}")
        raise SystemExit(1)
    print("[Phase 2] All checks passed.")


if __name__ == "__main__":
    main()
