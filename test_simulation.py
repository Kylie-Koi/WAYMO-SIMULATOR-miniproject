import tempfile
import unittest

import numpy as np

from deployment import allocate_vehicles, reposition_fleet
from simulation import generate_periods, run_experiment


class DeploymentTests(unittest.TestCase):
    def test_allocation_preserves_fleet_size(self):
        allocation = allocate_vehicles([1, 2, 3, 4, 5, 6, 7, 8, 9], 30)
        self.assertEqual(int(allocation.sum()), 30)
        self.assertTrue(np.all(allocation >= 0))

    def test_reposition_is_zero_when_already_at_target(self):
        allocation = allocate_vehicles(np.ones(9), 30)
        positions = np.repeat(np.arange(9), allocation)
        updated, miles = reposition_fleet(positions, allocation)
        np.testing.assert_array_equal(updated, positions)
        self.assertEqual(miles, 0.0)

    def test_demand_generation_is_reproducible(self):
        self.assertEqual(generate_periods(1, 123), generate_periods(1, 123))

    def test_small_experiment_writes_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            report = run_experiment(
                train_days=5,
                test_days=2,
                fleet_size=20,
                seed=7,
                output_dir=directory,
            )
            self.assertIn("without_model", report)
            self.assertIn("with_random_forest", report)
            self.assertIn("operating_cost_reduction_percent", report["comparison"])


if __name__ == "__main__":
    unittest.main()
