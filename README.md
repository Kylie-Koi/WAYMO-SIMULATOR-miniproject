# WAYMO-SIMULATOR
Trial RL session-other av projects are better, this is a trial repo, might be adding friends to this one
This project contains two related prototypes:

- `main.py`: an animated pygame robotaxi demonstration.
- `simulation.py`: a reproducible fleet-deployment experiment that trains a
  random forest to predict demand and compares it with the visual simulator's
  no-model random-cruising strategy.

## Run the random-forest experiment

The experiment uses the same held-out requests for both strategies. The only
difference is where taxis are placed before requests arrive.

Create and activate a local environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The environment only needs to be created once. In a new Terminal window, run
`source .venv/bin/activate` again before using the project.

```bash
python3 simulation.py
```

Optional settings:

```bash
python3 simulation.py --train-days 70 --test-days 14 --fleet-size 30 --seed 42
```

Outputs are written to `results/random_forest/`:

- `demand_random_forest.joblib`: trained model.
- `comparison.json`: model accuracy and baseline-versus-model results.
- `daily_metrics.csv`: day-level metrics for graphing or statistical analysis.

The reported operating cost is a transparent variable-mileage proxy, not
Waymo's internal or total operating cost. Synthetic demand is used, so results
measure performance inside this simulator and require real-world validation.
