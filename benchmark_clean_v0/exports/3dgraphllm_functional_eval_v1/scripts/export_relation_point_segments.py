#!/usr/bin/env python3
"""Export local target/anchor point segments for relation evidence rows.

The generated PLY files can be large and should not be committed. This helper is
provided so the benchmark can materialize point segments from the committed
manifests when needed.
"""

from __future__ import annotations

import argparse
import csv
import json
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
        header_lines = []
        while True:
            line = f.readline()
            if not line:
                raise ValueError(f"PLY header not terminated: {path}")
            header_lines.append(line)
            if line.strip() == b"end_header":
                break
        offset = f.tell()
    header = b"".join(header_lines).decode("ascii", errors="replace")
    n_vertices = None
    for line in header.splitlines():
        if line.startswith("element vertex "):
            n_vertices = int(line.split()[-1])
            break
    if n_vertices is None:
        raise ValueError(f"Missing vertex count in PLY: {path}")
    dtype = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("red", "u1"), ("green", "u1"), ("blue", "u1")])
    return np.memmap(path, dtype=dtype, mode="r", offset=offset, shape=(n_vertices,))


def write_ascii_ply(path: Path, verts: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(verts)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
        for v in verts:
            f.write(f"{float(v['x'])} {float(v['y'])} {float(v['z'])} {int(v['red'])} {int(v['green'])} {int(v['blue'])}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=EVIDENCE_DIR / "pointclouds_local")
    parser.add_argument("--limit", type=int, default=0, help="Optional number of relation rows to materialize; 0 means all.")
    args = parser.parse_args()

    annotations = {f"{row['scene_id']}/{row['annot_id']}": row for row in read_json(ANNOTATIONS_JSON)}
    ply_paths = load_raw_ply_paths()
    scene_cache: dict[str, np.ndarray] = {}
    written: dict[str, str] = {}
    rows = list(read_jsonl(EVIDENCE_DIR / "relation_evidence_index.jsonl"))
    if args.limit:
        rows = rows[: args.limit]
    for row in rows:
        scene_id = str(row["scene_id"])
        if scene_id not in scene_cache:
            scene_cache[scene_id] = parse_ply_vertices(ply_paths[scene_id])
        verts = scene_cache[scene_id]
        for node_id in [row["target_node_id"], None if row["anchor_missing"] else row["anchor_node_id"]]:
            if not node_id:
                continue
            key = f"{scene_id}/{node_id}"
            if key in written:
                continue
            anno = annotations.get(key, {})
            idx = np.asarray(anno.get("indices") or [], dtype=np.int64)
            idx = idx[(idx >= 0) & (idx < len(verts))]
            out_path = args.out_dir / scene_id / f"{node_id}.ply"
            write_ascii_ply(out_path, verts[idx])
            written[key] = str(out_path)
    print(json.dumps({"segments_written": len(written), "out_dir": str(args.out_dir)}, indent=2))


if __name__ == "__main__":
    main()
