"""Fleet placement helpers used by the headless experiment.

The pygame demo represents locations as road intersections.  This module keeps
the same nine-zone layout, but contains no pygame code, so experiments can run
quickly from a terminal or CI job.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


ZONE_NAMES = (
    "Downtown West",
    "Downtown East",
    "Airport",
    "Midtown West",
    "Midtown Central",
    "Midtown East",
    "Residential West",
    "Residential Central",
    "Park East",
)

# Miles between neighboring intersections.  Horizontal links are longer than
# vertical links because that is also true in the visual simulator.
_X = (0.0, 4.5, 8.5)
_Y = (0.0, 2.7, 5.4)
ZONE_COORDINATES = tuple((x, y) for y in _Y for x in _X)


def distance_matrix() -> np.ndarray:
    """Return shortest road distance between every pair of zones in miles."""

    matrix = np.zeros((len(ZONE_COORDINATES), len(ZONE_COORDINATES)))
    for origin, (x1, y1) in enumerate(ZONE_COORDINATES):
        for destination, (x2, y2) in enumerate(ZONE_COORDINATES):
            # The city is a complete rectangular road grid, so Manhattan
            # distance is the shortest road-path distance.
            matrix[origin, destination] = abs(x1 - x2) + abs(y1 - y2)
    return matrix


DISTANCES = distance_matrix()


def allocate_vehicles(scores: Sequence[float], fleet_size: int) -> np.ndarray:
    """Convert zone demand scores into integer vehicle targets.

    Largest-remainder rounding guarantees that the result always contains
    exactly ``fleet_size`` vehicles.
    """

    if fleet_size <= 0:
        raise ValueError("fleet_size must be positive")

    values = np.maximum(np.asarray(scores, dtype=float), 0.0)
    if values.shape != (len(ZONE_NAMES),):
        raise ValueError(f"scores must contain {len(ZONE_NAMES)} zone values")
    if values.sum() == 0:
        values = np.ones_like(values)

    quotas = values / values.sum() * fleet_size
    allocation = np.floor(quotas).astype(int)
    remaining = fleet_size - int(allocation.sum())
    if remaining:
        order = np.argsort(-(quotas - allocation), kind="stable")
        allocation[order[:remaining]] += 1
    return allocation


def expanded_positions(allocation: Sequence[int]) -> np.ndarray:
    """Expand per-zone vehicle counts into one zone index per vehicle."""

    counts = np.asarray(allocation, dtype=int)
    if counts.shape != (len(ZONE_NAMES),) or np.any(counts < 0):
        raise ValueError("allocation must contain nine non-negative counts")
    return np.repeat(np.arange(len(ZONE_NAMES), dtype=int), counts)


def minimum_cost_assignment(costs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Solve a rectangular assignment, with a small dependency-free fallback."""

    try:
        from scipy.optimize import linear_sum_assignment

        return linear_sum_assignment(costs)
    except ImportError:
        # Greedy is only a fallback for environments without SciPy.  It is
        # deterministic and adequate for this small nine-zone demonstration.
        remaining_rows = set(range(costs.shape[0]))
        remaining_cols = set(range(costs.shape[1]))
        rows: list[int] = []
        cols: list[int] = []
        while remaining_rows and remaining_cols:
            row, col = min(
                ((r, c) for r in remaining_rows for c in remaining_cols),
                key=lambda pair: (costs[pair], pair),
            )
            rows.append(row)
            cols.append(col)
            remaining_rows.remove(row)
            remaining_cols.remove(col)
        return np.asarray(rows, dtype=int), np.asarray(cols, dtype=int)


def reposition_fleet(
    current_positions: Sequence[int], target_allocation: Sequence[int]
) -> tuple[np.ndarray, float]:
    """Move taxis to a target distribution using minimum total empty miles."""

    current = np.asarray(current_positions, dtype=int)
    targets = expanded_positions(target_allocation)
    if len(current) != len(targets):
        raise ValueError("target allocation must equal the current fleet size")

    costs = DISTANCES[np.ix_(current, targets)]
    rows, cols = minimum_cost_assignment(costs)
    updated = current.copy()
    updated[rows] = targets[cols]
    return updated, float(costs[rows, cols].sum())
