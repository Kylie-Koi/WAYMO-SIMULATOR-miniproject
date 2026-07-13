"""Headless baseline-vs-random-forest robotaxi deployment experiment.

This is deliberately a fleet-operations model, not a self-driving physics
model.  It asks whether learning demand patterns in simulation improves where
idle taxis are placed before requests arrive.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from deployment import (
    DISTANCES,
    ZONE_NAMES,
    allocate_vehicles,
    minimum_cost_assignment,
    reposition_fleet,
)


INTERVALS_PER_DAY = 48
INTERVAL_HOURS = 0.5
AVERAGE_CITY_SPEED_MPH = 18.0
VARIABLE_COST_PER_MILE = 0.67


@dataclass(frozen=True)
class DemandContext:
    day: int
    day_of_week: int
    interval: int
    rain: int
    event_zone: int
    previous_demand: tuple[int, ...]


@dataclass(frozen=True)
class SimulationPeriod:
    context: DemandContext
    origins: tuple[int, ...]
    destinations: tuple[int, ...]


@dataclass
class PolicyMetrics:
    strategy: str
    requests: int = 0
    served_requests: int = 0
    reposition_miles: float = 0.0
    pickup_miles: float = 0.0
    occupied_miles: float = 0.0
    pickup_minutes: float = 0.0

    @property
    def empty_miles(self) -> float:
        return self.reposition_miles + self.pickup_miles

    @property
    def total_miles(self) -> float:
        return self.empty_miles + self.occupied_miles

    @property
    def operating_cost(self) -> float:
        # This is a public-data-friendly variable-cost proxy, not a claim about
        # Waymo's confidential accounting costs.
        return self.total_miles * VARIABLE_COST_PER_MILE

    @property
    def service_rate(self) -> float:
        return self.served_requests / self.requests if self.requests else 0.0

    @property
    def average_pickup_minutes(self) -> float:
        return self.pickup_minutes / self.served_requests if self.served_requests else 0.0

    def summary(self) -> dict[str, float | int | str]:
        return {
            "strategy": self.strategy,
            "requests": self.requests,
            "served_requests": self.served_requests,
            "service_rate_percent": self.service_rate * 100,
            "reposition_miles": self.reposition_miles,
            "pickup_miles": self.pickup_miles,
            "empty_miles": self.empty_miles,
            "occupied_miles": self.occupied_miles,
            "total_miles": self.total_miles,
            "average_pickup_minutes": self.average_pickup_minutes,
            "modeled_variable_operating_cost": self.operating_cost,
        }


class RandomForestDemandModel:
    """Predict next-interval request counts independently for all nine zones."""

    feature_names = (
        "zone",
        "hour_sin",
        "hour_cos",
        "day_of_week",
        "is_weekend",
        "rain",
        "event_here",
        "previous_zone_demand",
        "previous_total_demand",
    )

    def __init__(self, seed: int = 42, n_estimators: int = 300):
        self.regressor = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=18,
            min_samples_leaf=2,
            max_features=0.8,
            random_state=seed,
            n_jobs=-1,
        )

    @staticmethod
    def _features(context: DemandContext, zone: int) -> list[float]:
        angle = 2 * math.pi * context.interval / INTERVALS_PER_DAY
        return [
            float(zone),
            math.sin(angle),
            math.cos(angle),
            float(context.day_of_week),
            float(context.day_of_week >= 5),
            float(context.rain),
            float(context.event_zone == zone),
            float(context.previous_demand[zone]),
            float(sum(context.previous_demand)),
        ]

    def fit(self, periods: list[SimulationPeriod]) -> "RandomForestDemandModel":
        rows: list[list[float]] = []
        targets: list[int] = []
        for period in periods:
            counts = np.bincount(period.origins, minlength=len(ZONE_NAMES))
            for zone in range(len(ZONE_NAMES)):
                rows.append(self._features(period.context, zone))
                targets.append(int(counts[zone]))
        self.regressor.fit(np.asarray(rows), np.asarray(targets))
        return self

    def predict(self, context: DemandContext) -> np.ndarray:
        rows = [self._features(context, zone) for zone in range(len(ZONE_NAMES))]
        return np.maximum(self.regressor.predict(np.asarray(rows)), 0.0)

    def evaluate(self, periods: list[SimulationPeriod]) -> dict[str, float]:
        actual: list[int] = []
        predicted: list[float] = []
        for period in periods:
            counts = np.bincount(period.origins, minlength=len(ZONE_NAMES))
            actual.extend(counts.tolist())
            predicted.extend(self.predict(period.context).tolist())
        return {
            "mae_requests_per_zone_interval": mean_absolute_error(actual, predicted),
            "r2": r2_score(actual, predicted),
        }

    def feature_importance(self) -> dict[str, float]:
        pairs = zip(self.feature_names, self.regressor.feature_importances_)
        return dict(sorted(pairs, key=lambda pair: pair[1], reverse=True))


def _demand_rates(context: DemandContext) -> np.ndarray:
    """Latent request rates used to create synthetic historical demand."""

    hour = context.interval * INTERVAL_HOURS
    base = np.asarray([1.6, 1.2, 1.1, 1.0, 1.5, 0.9, 1.3, 1.1, 0.8])

    # Low overnight demand plus morning and evening commute peaks.
    overnight = 0.35 if hour < 6 else 1.0
    morning_peak = math.exp(-0.5 * ((hour - 8.0) / 1.5) ** 2)
    evening_peak = math.exp(-0.5 * ((hour - 17.5) / 1.8) ** 2)
    lunch_peak = math.exp(-0.5 * ((hour - 12.5) / 2.0) ** 2)
    rates = base * overnight
    rates += morning_peak * np.asarray([0.8, 0.7, 0.2, 0.5, 0.8, 0.2, 2.8, 2.3, 0.5])
    rates += evening_peak * np.asarray([2.9, 2.4, 0.8, 0.8, 1.2, 0.5, 0.3, 0.3, 0.3])
    rates += lunch_peak * np.asarray([1.2, 1.0, 0.4, 0.5, 1.0, 0.4, 0.2, 0.2, 0.2])

    if context.day_of_week >= 5:
        rates *= np.asarray([1.1, 1.1, 1.25, 0.9, 0.9, 0.9, 0.75, 0.75, 1.3])
    if context.rain:
        rates *= 1.18
    if context.event_zone >= 0:
        rates[context.event_zone] += 3.5

    # Recent observed demand is a useful near-term signal but does not fully
    # determine the next period, preserving realistic stochastic uncertainty.
    rates += 0.12 * np.asarray(context.previous_demand)
    return rates


def _destination_weights(origin: int, hour: float) -> np.ndarray:
    weights = np.exp(-DISTANCES[origin] / 5.0) + 0.12
    if 6.0 <= hour < 10.0 and origin in (6, 7, 8):
        weights[[0, 1, 4]] += 2.5
    elif 16.0 <= hour < 20.0 and origin in (0, 1, 3, 4):
        weights[[6, 7, 8]] += 2.2
    weights[origin] = 0.0
    return weights / weights.sum()


def generate_periods(days: int, seed: int, start_day: int = 0) -> list[SimulationPeriod]:
    """Create reproducible simulated historical or evaluation periods."""

    rng = np.random.default_rng(seed)
    periods: list[SimulationPeriod] = []
    for day in range(start_day, start_day + days):
        previous = np.zeros(len(ZONE_NAMES), dtype=int)
        rain = int(rng.random() < 0.24)
        has_event = rng.random() < 0.32
        event_zone = int(rng.choice([0, 1, 2, 4, 8])) if has_event else -1
        event_start = int(rng.integers(32, 41)) if has_event else -1

        for interval in range(INTERVALS_PER_DAY):
            active_event = event_zone if event_start <= interval < event_start + 4 else -1
            context = DemandContext(
                day=day,
                day_of_week=day % 7,
                interval=interval,
                rain=rain,
                event_zone=active_event,
                previous_demand=tuple(int(value) for value in previous),
            )
            counts = rng.poisson(_demand_rates(context))
            origins = np.repeat(np.arange(len(ZONE_NAMES)), counts).astype(int)
            rng.shuffle(origins)
            hour = interval * INTERVAL_HOURS
            destinations = tuple(
                int(rng.choice(len(ZONE_NAMES), p=_destination_weights(int(origin), hour)))
                for origin in origins
            )
            periods.append(
                SimulationPeriod(
                    context=context,
                    origins=tuple(int(value) for value in origins),
                    destinations=destinations,
                )
            )
            previous = counts
    return periods


def _uniform_allocation(fleet_size: int) -> np.ndarray:
    return allocate_vehicles(np.ones(len(ZONE_NAMES)), fleet_size)


def run_policy(
    periods: list[SimulationPeriod],
    fleet_size: int,
    strategy: str,
    model: RandomForestDemandModel | None = None,
    rebalance_every: int = 2,
    seed: int = 42,
) -> tuple[PolicyMetrics, list[dict[str, Any]]]:
    """Run one policy over fixed demand and return aggregate plus daily data."""

    if strategy not in {"random_cruising_baseline", "random_forest"}:
        raise ValueError("unknown strategy")
    if strategy == "random_forest" and model is None:
        raise ValueError("random_forest strategy requires a trained model")

    positions = np.repeat(np.arange(len(ZONE_NAMES)), _uniform_allocation(fleet_size))
    rng = np.random.default_rng(seed)
    metrics = PolicyMetrics(strategy=strategy)
    daily: dict[int, PolicyMetrics] = {}

    for period in periods:
        day_metrics = daily.setdefault(period.context.day, PolicyMetrics(strategy=strategy))
        if period.context.interval % rebalance_every == 0:
            if strategy == "random_cruising_baseline":
                # Mirrors Taxi.choose_new_destination() in the pygame demo.
                # We still optimize which taxi goes to which sampled patrol
                # zone, making this a conservative version of random cruising.
                random_zones = rng.integers(0, len(ZONE_NAMES), size=fleet_size)
                target = np.bincount(random_zones, minlength=len(ZONE_NAMES))
            else:
                target = allocate_vehicles(model.predict(period.context) + 0.15, fleet_size)
            positions, reposition = reposition_fleet(positions, target)
            metrics.reposition_miles += reposition
            day_metrics.reposition_miles += reposition

        origins = np.asarray(period.origins, dtype=int)
        destinations = np.asarray(period.destinations, dtype=int)
        request_count = len(origins)
        metrics.requests += request_count
        day_metrics.requests += request_count
        if request_count == 0:
            continue

        costs = DISTANCES[np.ix_(positions, origins)]
        taxi_rows, request_cols = minimum_cost_assignment(costs)
        pickup = costs[taxi_rows, request_cols]
        occupied = DISTANCES[origins[request_cols], destinations[request_cols]]
        served = len(request_cols)

        positions[taxi_rows] = destinations[request_cols]
        pickup_miles = float(pickup.sum())
        occupied_miles = float(occupied.sum())
        pickup_minutes = float((pickup / AVERAGE_CITY_SPEED_MPH * 60).sum())
        for bucket in (metrics, day_metrics):
            bucket.served_requests += served
            bucket.pickup_miles += pickup_miles
            bucket.occupied_miles += occupied_miles
            bucket.pickup_minutes += pickup_minutes

    daily_rows = [daily[day].summary() | {"day": day} for day in sorted(daily)]
    return metrics, daily_rows


def percent_reduction(baseline: float, modeled: float) -> float:
    return (baseline - modeled) / baseline * 100 if baseline else 0.0


def run_experiment(
    train_days: int = 70,
    test_days: int = 14,
    fleet_size: int = 30,
    seed: int = 42,
    output_dir: str | Path = "results/random_forest",
) -> dict[str, Any]:
    """Train the forest, run both policies, and save reproducible artifacts."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    training = generate_periods(train_days, seed=seed, start_day=0)
    evaluation = generate_periods(test_days, seed=seed + 1, start_day=train_days)

    model = RandomForestDemandModel(seed=seed).fit(training)
    model_quality = model.evaluate(evaluation)
    baseline, baseline_daily = run_policy(
        evaluation,
        fleet_size,
        "random_cruising_baseline",
        seed=seed + 2,
    )
    learned, learned_daily = run_policy(
        evaluation, fleet_size, "random_forest", model=model
    )

    baseline_summary = baseline.summary()
    learned_summary = learned.summary()
    comparison = {
        "empty_miles_reduction_percent": percent_reduction(
            baseline.empty_miles, learned.empty_miles
        ),
        "pickup_time_reduction_percent": percent_reduction(
            baseline.average_pickup_minutes, learned.average_pickup_minutes
        ),
        "operating_cost_reduction_percent": percent_reduction(
            baseline.operating_cost, learned.operating_cost
        ),
        "service_rate_change_percentage_points": (
            learned.service_rate - baseline.service_rate
        )
        * 100,
    }
    report: dict[str, Any] = {
        "experiment": {
            "train_days": train_days,
            "test_days": test_days,
            "fleet_size": fleet_size,
            "seed": seed,
            "cost_scope": "modeled variable mileage cost only",
            "cost_per_mile_usd": VARIABLE_COST_PER_MILE,
        },
        "model_quality": model_quality,
        "feature_importance": model.feature_importance(),
        "without_model": baseline_summary,
        "with_random_forest": learned_summary,
        "comparison": comparison,
    }

    joblib.dump(model, output / "demand_random_forest.joblib", compress=3)
    (output / "comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    fieldnames = list(baseline_daily[0].keys())
    with (output / "daily_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(baseline_daily)
        writer.writerows(learned_daily)
    return report


def _print_report(report: dict[str, Any]) -> None:
    baseline = report["without_model"]
    learned = report["with_random_forest"]
    comparison = report["comparison"]
    quality = report["model_quality"]
    print("Random-forest demand model")
    print(f"  Held-out MAE: {quality['mae_requests_per_zone_interval']:.3f} requests/zone/interval")
    print(f"  Held-out R^2: {quality['r2']:.3f}")
    print("\nWithout model (random cruising)")
    print(f"  Empty miles: {baseline['empty_miles']:.1f}")
    print(f"  Average pickup: {baseline['average_pickup_minutes']:.2f} minutes")
    print(f"  Variable operating cost: ${baseline['modeled_variable_operating_cost']:.2f}")
    print("\nWith random forest (predicted-demand placement)")
    print(f"  Empty miles: {learned['empty_miles']:.1f}")
    print(f"  Average pickup: {learned['average_pickup_minutes']:.2f} minutes")
    print(f"  Variable operating cost: ${learned['modeled_variable_operating_cost']:.2f}")
    print("\nChange")
    print(f"  Empty miles: {comparison['empty_miles_reduction_percent']:.2f}% reduction")
    print(f"  Pickup time: {comparison['pickup_time_reduction_percent']:.2f}% reduction")
    print(f"  Operating cost: {comparison['operating_cost_reduction_percent']:.2f}% reduction")
    print("\nArtifacts: results/random_forest/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-days", type=int, default=70)
    parser.add_argument("--test-days", type=int, default=14)
    parser.add_argument("--fleet-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="results/random_forest")
    args = parser.parse_args()
    report = run_experiment(
        train_days=args.train_days,
        test_days=args.test_days,
        fleet_size=args.fleet_size,
        seed=args.seed,
        output_dir=args.output_dir,
    )
    _print_report(report)


if __name__ == "__main__":
    main()
