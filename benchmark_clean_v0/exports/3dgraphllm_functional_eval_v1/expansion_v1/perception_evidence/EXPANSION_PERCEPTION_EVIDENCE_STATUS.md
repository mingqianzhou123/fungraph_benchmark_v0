# Expansion Perception Evidence v1 Status

This layer adds inspectable visual evidence cards for the expansion functional freeze candidates.
It does not modify the old 683-row full-perception evidence layer.

## Coverage

- Functional freeze candidates: 116
- Visual evidence ready: 116
- Previously missing candidates now with pointcloud evidence: 21
- Candidates with previous depth-tested RGB-D crop metadata: 46
- Images written: 116

## Boundary

The generated evidence cards are GT pointcloud object-segment renders. They make every candidate inspectable, but they do not imply that every candidate has a newly depth-tested camera RGB-D crop.
