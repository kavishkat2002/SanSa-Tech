#!/usr/bin/env python3
"""
discover_params.py  –  Box Box Box Parameter Discovery (Optimized)
==================================================================
Optimized version for faster execution using pre-processing and parallelization.
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

COMPOUND_IDX = {"SOFT": 0, "MEDIUM": 1, "HARD": 2}

def load_historical_races(max_races=5000):
    races = []
    pattern = os.path.join(HISTORICAL_DIR, "races_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
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
    print(f"Loaded {len(races)} historical races.")
    return races[:max_races]

def preprocess_races(races):
    print("Pre-processing race data for speed...")
    processed = []
    for race in races:
        config = race["race_config"]
        base = config["base_lap_time"]
        pit_time = config["pit_lane_time"]
        track_temp = config["track_temp"]
        total_laps = config["total_laps"]
        
        actual = race["finishing_positions"]
        actual_rank = {driver: i for i, driver in enumerate(actual)}
        
        drivers_data = []
        for strat in race["strategies"].values():
            did = strat["driver_id"]
            starting_tire = COMPOUND_IDX[strat["starting_tire"]]
            stops = []
            for s in strat.get("pit_stops", []):
                stops.append((s["lap"], COMPOUND_IDX[s["to_tire"]]))
            drivers_data.append((did, starting_tire, stops))
            
        ranking_pairs = []
        n = len(drivers_data)
        for i in range(n):
            for j in range(i + 1, n):
                a_did = drivers_data[i][0]
                b_did = drivers_data[j][0]
                if actual_rank[a_did] < actual_rank[b_did]:
                    ranking_pairs.append((i, j)) # i finishes before j
                else:
                    ranking_pairs.append((j, i)) # j finishes before i
                    
        processed.append({
            "base": base,
            "pit_time": pit_time,
            "track_temp": track_temp,
            "total_laps": total_laps,
            "drivers": drivers_data,
            "pairs": ranking_pairs
        })
    return processed

def compute_times_fast(race_data, cb, dg, temp_factor, deg_power):
    base = race_data["base"]
    pit_time = race_data["pit_time"]
    track_temp = race_data["track_temp"]
    total_laps = race_data["total_laps"]
    
    times = []
    for did, tire, stops in race_data["drivers"]:
        total_time = 0.0
        tire_age = 0
        pit_idx = 0
        num_stops = len(stops)
        
        for lap in range(1, total_laps + 1):
            tire_age += 1
            total_time += (
                base
                + cb[tire]
                + dg[tire] * (tire_age ** deg_power)
                + temp_factor * track_temp
            )
            
            if pit_idx < num_stops and stops[pit_idx][0] == lap:
                total_time += pit_time
                tire = stops[pit_idx][1]
                tire_age = 0
                pit_idx += 1
        times.append(total_time)
    return times

def loss_func(params, processed_races):
    cb = [params[0], params[1], params[2]]
    dg = [params[3], params[4], params[5]]
    temp_factor = params[6]
    deg_power = max(1.0, min(4.0, params[7]))
    
    loss = 0.0
    margin = 0.5
    for race in processed_races:
        times = compute_times_fast(race, cb, dg, temp_factor, deg_power)
        for first_idx, second_idx in race["pairs"]:
            diff = times[second_idx] - times[first_idx]
            if diff < margin:
                loss += (margin - diff) ** 2
    return loss

def exact_match_rate(params, processed_races):
    cb = [params[0], params[1], params[2]]
    dg = [params[3], params[4], params[5]]
    temp_factor = params[6]
    deg_power = params[7]
    
    correct = 0
    for race in processed_races:
        times = compute_times_fast(race, cb, dg, temp_factor, deg_power)
        # Check if the ordering of times matches the order implied by pairs
        # Actually simplest: predict order and compare
        # In our pre-processing, we don't have driver IDs in correct order easily, 
        # but we know drivers[i][0] is the ID.
        results = []
        for i, time_val in enumerate(times):
            results.append((race["drivers"][i][0], time_val))
        predicted = [d[0] for d in sorted(results, key=lambda x: x[1])]
        
        # We need the actual positions to compare
        # (Could have stored them in processed)
        # Let's just use the original ranking pairs to verify
        is_correct = True
        for first_idx, second_idx in race["pairs"]:
            if times[first_idx] > times[second_idx]:
                is_correct = False
                break
        if is_correct:
            correct += 1
    return correct / len(processed_races)

def run_optimisation(processed_races):
    print(f"\nFitting parameters on {len(processed_races)} races...")
    
    # Phase 1: Global search (subset)
    print("Phase 1: Global search (differential evolution, 200 races)...")
    sample = processed_races[:200]
    
    bounds = [
        (-6.0,  0.0),   # cb_soft
        (-3.0,  3.0),   # cb_med
        ( 0.0,  6.0),   # cb_hard
        ( 0.001, 0.5),  # dg_soft
        ( 0.001, 0.3),  # dg_med
        ( 0.001, 0.2),  # dg_hard
        (-0.1,   0.1),  # temp_factor
        ( 1.0,   4.0),  # deg_power
    ]
    
    t0 = time.time()
    de_result = differential_evolution(
        loss_func,
        bounds,
        args=(sample,),
        seed=42,
        maxiter=100, # Reduced
        popsize=8,   # Reduced
        tol=1e-4,
        disp=True,
        workers=-1 # Parallel!
    )
    print(f"Phase 1 done in {time.time()-t0:.1f}s loss={de_result.fun:.4f}")
    x1 = de_result.x
    
    # Phase 2: Local refinement (all)
    print(f"\nPhase 2: Local refinement (Nelder-Mead, {len(processed_races)} races)...")
    t0 = time.time()
    nm_result = minimize(
        loss_func,
        x1,
        args=(processed_races,),
        method="Nelder-Mead",
        options={"maxiter": 1000, "adaptive": True}
    )
    print(f"Phase 2 done in {time.time()-t0:.1f}s loss={nm_result.fun:.4f}")
    return nm_result.x

def main():
    races = load_historical_races(max_races=1000) # Use 1000 for reasonable time
    processed = preprocess_races(races)
    
    best_params = run_optimisation(processed)
    
    acc = exact_match_rate(best_params, processed)
    print(f"\nFinal accuracy on training set: {acc*100:.1f}%")
    
    cb_soft, cb_med, cb_hard = best_params[0], best_params[1], best_params[2]
    dg_soft, dg_med, dg_hard = best_params[3], best_params[4], best_params[5]
    temp_factor, deg_power   = best_params[6], best_params[7]
    
    print("\n" + "="*50)
    print("DISCOVERED PARAMETERS")
    print("="*50)
    print(f'COMPOUND_BASE = {{"SOFT": {cb_soft:.6f}, "MEDIUM": {cb_med:.6f}, "HARD": {cb_hard:.6f}}}')
    print(f'DEGRADATION   = {{"SOFT": {dg_soft:.6f}, "MEDIUM": {dg_med:.6f}, "HARD": {dg_hard:.6f}}}')
    print(f'TEMP_FACTOR   = {temp_factor:.8f}')
    print(f'DEG_POWER     = {deg_power:.6f}')
    print("="*50)
    
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

if __name__ == "__main__":
    main()
