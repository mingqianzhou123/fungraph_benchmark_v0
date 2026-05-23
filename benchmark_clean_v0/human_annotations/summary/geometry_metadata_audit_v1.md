# Geometry / Metadata Audit — Benchmark-v2

Generated: 2026-05-24

This audit supports the paper's limitation section:
> *Color/material grounding remains limited because current graph metadata*
> *lacks reliable perceptual attributes.*

---

## 1. Bbox Coverage (SceneFun3D)

| | Count |
|---|---|
| Total SceneFun3D scenes in benchmark | 20 |
| Scenes with geometry data | 20 |
| Scenes without geometry data | 0 |
| Total nodes across geometry-covered scenes | 317 |
| Nodes with bbox (bbox_center + bbox_min + bbox_max) | 317 / 317 = **100%** |

### Per-scene bbox coverage

| Scene | Nodes total | Nodes with bbox | Mean bbox volume (m³) |
|---|---|---|---|
| 420683 | 21 | 21 | 0.0934 |
| 421013 | 22 | 22 | 0.0659 |
| 421015 | 11 | 11 | 0.1857 |
| 421063 | 12 | 12 | 0.1768 |
| 421254 | 28 | 28 | 0.0404 |
| 421267 | 18 | 18 | 0.0726 |
| 421380 | 22 | 22 | 0.0434 |
| 421602 | 19 | 19 | 0.2308 |
| 422007 | 16 | 16 | 0.1497 |
| 422391 | 10 | 10 | 0.0399 |
| 422813 | 13 | 13 | 0.1070 |
| 422826 | 10 | 10 | 0.1275 |
| 460417 | 14 | 14 | 0.0744 |
| 460419 | 14 | 14 | 0.2794 |
| 466183 | 14 | 14 | 0.1934 |
| 466192 | 8 | 8 | 0.1630 |
| 466803 | 6 | 6 | 0.1470 |
| 467293 | 7 | 7 | 0.0294 |
| 468076 | 9 | 9 | 0.0308 |
| 469011 | 43 | 43 | 1.1398 |

---

## 2. Bbox Extent and Volume Statistics

All measurements in metres (scene coordinate units). z-axis is vertical (up).

  Extent X (width): n=317  min=0.0076  median=0.1095  mean=0.2900  max=7.7413
  Extent Y (depth): n=317  min=0.0114  median=0.0917  mean=0.2306  max=5.0686
  Extent Z (height): n=317  min=0.0087  median=0.0722  mean=0.2873  max=2.3444
  Volume (m³): n=317  min=0.0000  median=0.0005  mean=0.2528  max=41.9958

### Volume histogram

| Bucket | Count |
|---|---|
| <0.001 m³ | 180 |
| 0.001–0.01 m³ | 43 |
| 0.01–0.1 m³ | 33 |
| 0.1–1.0 m³ | 52 |
| ≥1.0 m³ | 9 |

Note: the large proportion of `<0.001 m³` volumes corresponds to small interactive elements
(knobs, buttons, handles, outlets) — exactly the target objects in functional queries.

---

## 3. Perceptual Attribute Coverage

### SceneFun3D (source for all human-annotation queries)

Node fields present: `node_id`, `label`, `indices_count`, `bbox_center`, `bbox_min`, `bbox_max`

| Perceptual field | Nodes with field | % |
|---|---|---|
| `color` / `colors` | 0 / 317 | 0.0% |
| `material` / `materials` | 0 / 317 | 0.0% |
| `attributes` / `attribute` | 0 / 317 | 0.0% |

**Result: SceneFun3D nodes carry NO color, material, or perceptual attribute fields.**
The only node metadata available is: `node_id`, `label`, `indices_count`, `bbox_center`,
`bbox_min`, `bbox_max`.

### 3DSSG (separate dataset — not used for functional queries)

Total nodes across 1335 scenes: 38929

| Perceptual field | Nodes with field | % |
|---|---|---|
| `attributes` (any) | 31410 / 38929 | 80.7% |
| `attributes.color` | 12561 / 38929 | 32.3% |
| `attributes.material` | 5356 / 38929 | 13.8% |
| `attributes.shape` | 11934 / 38929 | 30.7% |
| `attributes.texture` | 2435 / 38929 | 6.3% |

3DSSG attribute sub-keys (by frequency):

| Sub-key | Count |
|---|---|
| `lexical` | 18204 |
| `color` | 12561 |
| `shape` | 11934 |
| `size` | 10183 |
| `material` | 5356 |
| `state` | 3890 |
| `other` | 3162 |
| `texture` | 2435 |
| `style` | 49 |

**Important**: 3DSSG color/material data is NOT transferred to SceneFun3D nodes.
The two datasets use different scene representations and node IDs.
Even if color labels were available in 3DSSG, they cannot be reliably mapped to
the SceneFun3D interactive-element nodes used in functional queries.

---

## 4. Implication for Benchmark

| Evidence type | Available in SceneFun3D graph | Notes |
|---|---|---|
| Functional relation (pull/rotate/press) | ✓ | Core of all queries |
| Geometry (bbox position/size) | ✓ | All 317 nodes |
| Spatial relation (left/right/above) | ✓ (derived from bbox) | Used in geometry_aware queries |
| Node label | ✓ | All 317 nodes |
| Color | ✗ | 0 / 317 nodes |
| Material | ✗ | 0 / 317 nodes |
| Texture | ✗ | 0 / 317 nodes |
| Affordance text | ✗ | Not in node metadata |

All 173 human-annotated functional queries (133 main + 40 long-range) were designed
to use only available evidence: functional relations, geometry, and node labels.
No query depends on color or material for disambiguation.
