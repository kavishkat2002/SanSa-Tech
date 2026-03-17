#!/usr/bin/env python3
"""
discover_params.py  –  Box Box Box Parameter Discovery
=======================================================
Reads historical race data and uses numerical optimisation
to find the exact COMPOUND_BASE, DEGRADATION, TEMP_FACTOR,
and DEG_POWER values that reproduce the known results.

Usage:
    python analysis/discover_params.py

Output:
    Prints the discovered parameters, then writes them to
    solution/params.json so race_simulator.py can load them.
"""

import json
import glob
import os
import sys
import time

import numpy as np
from scipy.optimize import minimize, differential_evolution

# ── Paths ──────────────────────────────────────────────────────────────────
HISTORICAL_DIR  = "data/historical_races"
PARAMS_OUT      = "solution/params.json"
TEST_INPUT_DIR  = "data/test_cases/inputs"
TEST_OUTPUT_DIR = "data/test_cases/expected_outputs"


# ── Data Loading ───────────────────────────────────────────────────────────

def load_historical_races(max_races=5000):
    """
    Historical data is stored in batched JSON files, e.g.
        races_00000-00999.json  (list of race dicts)
    Each race dict has: race_config, strategies, finishing_positions
    """
    races = []
    pattern = os.path.join(HISTORICAL_DIR, "races_*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        # Try individual files (race_00001.json style)
        pattern = os.path.join(HISTORICAL_DIR, "race_*.json")
        files = sorted(glob.glob(pattern))

    if not files:
        print(f"ERROR: No historical race files found in {HISTORICAL_DIR}/")
        sys.exit(1)

    for filepath in files:
        with open(filepath, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            races.extend(data)
        else:
            races.append(data)
        if len(races) >= max_races:
            break

    return races[:max_races]


# ── Simulation Core ────────────────────────────────────────────────────────

COMPOUND_IDX = {"SOFT": 0, "MEDIUM": 1, "HARD": 2}

def compute_driver_time(strat, race_config, params):
    """
    params layout:
        [cb_soft, cb_medium, cb_hard,
         dg_soft, dg_medium, dg_hard,
         temp_factor, deg_power]
    """
    cb_soft, cb_med, cb_hard = params[0], params[1], params[2]
    dg_soft, dg_med, dg_hard = params[3], params[4], params[5]
    temp_factor, deg_power   = params[6], params[7]

    compound_base = {"SOFT": cb_soft, "MEDIUM": cb_med, "HARD": cb_hard}
    degradation   = {"SOFT": dg_soft, "MEDIUM": dg_med, "HARD": dg_hard}

    base       = race_config["base_lap_time"]
    pit_time   = race_config["pit_lane_time"]
    track_temp = race_config["track_temp"]
    total_laps = race_config["total_laps"]

    current_tire = strat["starting_tire"]
    total_time   = 0.0
    tire_age     = 0
    pit_idx      = 0
    stops        = strat.get("pit_stops", [])

    for lap in range(1, total_laps + 1):
        tire_age += 1
        lap_time = (
            base
            + compound_base[current_tire]
            + degradation[current_tire] * (tire_age ** deg_power)
            + temp_factor * track_temp
        )
        total_time += lap_time

        if pit_idx < len(stops) and stops[pit_idx]["lap"] == lap:
            total_time   += pit_time
            current_tire  = stops[pit_idx]["to_tire"]
            tire_age      = 0
            pit_idx      += 1

    return total_time


def predict_race(race, params):
    results = []
    for strat in race["strategies"].values():
        t = compute_driver_time(strat, race["race_config"], params)
        results.append((strat["driver_id"], t))
    return [d[0] for d in sorted(results, key=lambda x: x[1])]


# ── Loss Function ──────────────────────────────────────────────────────────

def pairwise_ranking_loss(params, races):
    """
    Smooth surrogate loss over pairwise ordering constraints.
    For every (A,B) pair where A finishes before B, we want time_A < time_B.
    Uses a soft-margin hinge: max(0, margin - (time_B - time_A))^2
    """
    # Clamp deg_power to [1, 4] for stability
    p = list(params)
    p[7] = max(1.0, min(4.0, p[7]))

    loss = 0.0
    margin = 0.5   # seconds — we want at least 0.5s separation

    for race in races:
        actual    = race["finishing_positions"]
        actual_rank = {driver: i for i, driver in enumerate(actual)}

        times = {}
        for strat in race["strategies"].values():
            did = strat["driver_id"]
            times[did] = compute_driver_time(strat, race["race_config"], p)

        drivers = list(times.keys())
        n = len(drivers)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = drivers[i], drivers[j]
                # Correct direction: a should be before b iff rank[a] < rank[b]
                if actual_rank[a] < actual_rank[b]:
                    diff = times[b] - times[a]
                else:
                    diff = times[a] - times[b]
                if diff < margin:
                    loss += (margin - diff) ** 2

    return loss


def exact_match_rate(params, races):
    correct = 0
    for race in races:
        predicted = predict_race(race, params)
        if predicted == race["finishing_positions"]:
            correct += 1
    return correct / len(races)


# ── Optimisation ───────────────────────────────────────────────────────────

def run_optimisation(races):
    print(f"\nFitting parameters on {len(races)} historical races...")
    print("This may take a few minutes.\n")

    # Initial guess (current estimates from race_simulator.py)
    # params: [cb_soft, cb_med, cb_hard, dg_soft, dg_med, dg_hard, temp_factor, deg_power]
    x0 = np.array([-2.5, 0.0, 2.5,
                    0.04, 0.02, 0.01,
                    0.01, 2.0])

    # ── Phase 1: Global search with differential evolution on a small sample ──
    print("Phase 1: Global search (differential evolution, 500 races)...")
    sample = races[:500]

    bounds = [
        (-6.0,  0.0),   # cb_soft  — SOFT is faster, so negative
        (-3.0,  3.0),   # cb_med
        ( 0.0,  6.0),   # cb_hard  — HARD is slower, so positive
        ( 0.001, 0.5),  # dg_soft
        ( 0.001, 0.3),  # dg_med
        ( 0.001, 0.2),  # dg_hard
        (-0.1,   0.1),  # temp_factor
        ( 1.0,   4.0),  # deg_power
    ]

    t0 = time.time()
    de_result = differential_evolution(
        pairwise_ranking_loss,
        bounds,
        args=(sample,),
        seed=42,
        maxiter=300,
        popsize=10,
        tol=1e-6,
        mutation=(0.5, 1.5),
        recombination=0.7,
        workers=1,
        disp=True,
    )
    print(f"Phase 1 done in {time.time()-t0:.1f}s  loss={de_result.fun:.4f}")
    x1 = de_result.x

    # ── Phase 2: Local refinement on larger sample ──
    print(f"\nPhase 2: Local refinement (Nelder-Mead, {len(races)} races)...")
    t0 = time.time()
    nm_result = minimize(
        pairwise_ranking_loss,
        x1,
        args=(races,),
        method="Nelder-Mead",
        options={
            "maxiter": 50000,
            "xatol":   1e-7,
            "fatol":   1e-7,
            "adaptive": True,
        },
    )
    print(f"Phase 2 done in {time.time()-t0:.1f}s  loss={nm_result.fun:.4f}")
    return nm_result.x


# ── Validation ─────────────────────────────────────────────────────────────

def validate_on_test_cases(params):
    test_inputs = sorted(glob.glob(os.path.join(TEST_INPUT_DIR, "test_*.json")))
    test_outputs = sorted(glob.glob(os.path.join(TEST_OUTPUT_DIR, "test_*.json")))

    if not test_inputs or not test_outputs:
        print("(no test cases found for validation)")
        return

    correct = 0
    total   = min(len(test_inputs), len(test_outputs))

    for inp_path, out_path in zip(test_inputs[:total], test_outputs[:total]):
        with open(inp_path)  as f: test_in  = json.load(f)
        with open(out_path)  as f: test_out = json.load(f)
        predicted = predict_race(test_in, params)
        if predicted == test_out["finishing_positions"]:
            correct += 1

    print(f"\n{'='*50}")
    print(f"Test Case Validation:  {correct}/{total}  ({100*correct/total:.1f}%)")
    print(f"{'='*50}")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    races = load_historical_races(max_races=5000)
    print(f"Loaded {len(races)} historical races from {HISTORICAL_DIR}/")

    # Quick sanity check with initial params
    initial_params = [-2.5, 0.0, 2.5, 0.04, 0.02, 0.01, 0.01, 2.0]
    init_acc = exact_match_rate(initial_params, races[:200])
    print(f"Initial parameter accuracy (200 races): {init_acc*100:.1f}%")

    best_params = run_optimisation(races)

    final_acc = exact_match_rate(best_params, races)
    print(f"\nFinal accuracy on {len(races)} historical races: {final_acc*100:.1f}%")

    # ── Print discovered parameters ──
    cb_soft, cb_med, cb_hard = best_params[0], best_params[1], best_params[2]
    dg_soft, dg_med, dg_hard = best_params[3], best_params[4], best_params[5]
    temp_factor, deg_power   = best_params[6], best_params[7]

    print("\n" + "="*50)
    print("DISCOVERED PARAMETERS — paste into race_simulator.py")
    print("="*50)
    print(f'COMPOUND_BASE = {{"SOFT": {cb_soft:.6f}, "MEDIUM": {cb_med:.6f}, "HARD": {cb_hard:.6f}}}')
    print(f'DEGRADATION   = {{"SOFT": {dg_soft:.6f}, "MEDIUM": {dg_med:.6f}, "HARD": {dg_hard:.6f}}}')
    print(f'TEMP_FACTOR   = {temp_factor:.8f}')
    print(f'DEG_POWER     = {deg_power:.6f}')
    print("="*50)

    # ── Save to JSON so race_simulator.py can auto-load ──
    os.makedirs(os.path.dirname(PARAMS_OUT), exist_ok=True)
    discovered = {
        "COMPOUND_BASE": {"SOFT": cb_soft, "MEDIUM": cb_med, "HARD": cb_hard},
        "DEGRADATION":   {"SOFT": dg_soft, "MEDIUM": dg_med, "HARD": dg_hard},
        "TEMP_FACTOR":   temp_factor,
        "DEG_POWER":     deg_power,
    }
    with open(PARAMS_OUT, "w") as f:
        json.dump(discovered, f, indent=2)
    print(f"\nParameters saved to: {PARAMS_OUT}")

    # ── Validate against test cases ──
    validate_on_test_cases(best_params)


if __name__ == "__main__":
    main()
