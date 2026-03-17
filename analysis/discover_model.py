#!/usr/bin/env python3
"""
Box Box Box - Model Discovery Script
=====================================
Run this from the project root:
    python3 analysis/discover_model.py

This script reverse-engineers the hidden lap time formula by:
1. Exploring historical race data
2. Running a grid search over parameter combinations
3. Validating the best parameters on 500+ races
"""

import json
import sys
from pathlib import Path
from itertools import product

# ── helper ──────────────────────────────────────────────────────────────────

def simulate_race(race, compound_base, deg_rate, temp_factor, deg_power):
    """Simulate one race and return sorted driver list (fastest first)."""
    config = race['race_config']
    base       = config['base_lap_time']
    pit_time   = config['pit_lane_time']
    track_temp = config['track_temp']
    total_laps = config['total_laps']

    results = []
    for strat in race['strategies'].values():
        driver_id    = strat['driver_id']
        current_tire = strat['starting_tire']
        total_time   = 0.0
        tire_age     = 0          # reset on fresh set
        pit_idx      = 0
        stops        = strat.get('pit_stops', [])

        for lap in range(1, total_laps + 1):
            # Regulations §Tire Age Tracking:
            # "At the start of each lap, tire age increments by 1 BEFORE calculating"
            # → first lap on fresh tires = age 1
            tire_age += 1

            lap_time = (
                base
                + compound_base[current_tire]
                + deg_rate[current_tire] * (tire_age ** deg_power)
                + temp_factor * track_temp
            )
            total_time += lap_time

            # Pit stop at END of this lap
            if pit_idx < len(stops) and stops[pit_idx]['lap'] == lap:
                total_time  += pit_time
                current_tire = stops[pit_idx]['to_tire']
                tire_age     = 0          # fresh set → next lap = age 1
                pit_idx     += 1

        results.append((driver_id, total_time))

    return [d[0] for d in sorted(results, key=lambda x: x[1])]


def score_params(races, compound_base, deg_rate, temp_factor, deg_power, n=100):
    correct = 0
    for race in races[:n]:
        if simulate_race(race, compound_base, deg_rate, temp_factor, deg_power) == race['finishing_positions']:
            correct += 1
    return correct

# ── load historical data ─────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / 'data' / 'historical_races'
print("Loading historical races …", flush=True)
races = json.load(open(DATA_DIR / 'races_00000-00999.json'))
print(f"Loaded {len(races)} races.\n")

# ── Step 1: show first race details ─────────────────────────────────────────

race = races[0]
config = race['race_config']
print("=== RACE 0 CONFIG ===")
print(f"  Track: {config['track']}, Laps: {config['total_laps']}, "
      f"Base: {config['base_lap_time']}, Temp: {config['track_temp']}, "
      f"Pit: {config['pit_lane_time']}")
print(f"  Actual result: {race['finishing_positions']}")
print()

# ── Step 2: grid search ─────────────────────────────────────────────────────

print("=== GRID SEARCH (patience ~2-3 min) ===", flush=True)

SOFT_BASES   = [-3.0, -2.5, -2.0, -1.5, -1.0]
HARD_BASES   = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
DEG_SOFTS    = [0.02, 0.03, 0.04, 0.05, 0.06, 0.08]
DEG_MEDS     = [0.01, 0.015, 0.02, 0.025, 0.03]
DEG_HARDS    = [0.005, 0.008, 0.01, 0.012, 0.015]
TEMP_FACTORS = [0.005, 0.01, 0.015, 0.02, 0.025]
DEG_POWERS   = [1.0, 1.5, 2.0, 2.5, 3.0]

best_score  = -1
best_params = None

# First pass: use a small sample (50 races) to quickly find candidates
QUICK_N = 50

for soft_b in SOFT_BASES:
    for hard_b in HARD_BASES:
        for deg_s in DEG_SOFTS:
            for deg_m in DEG_MEDS:
                for deg_h in DEG_HARDS:
                    for temp_f in TEMP_FACTORS:
                        for deg_pow in DEG_POWERS:
                            cb = {'SOFT': soft_b, 'MEDIUM': 0.0, 'HARD': hard_b}
                            dr = {'SOFT': deg_s,  'MEDIUM': deg_m,  'HARD': deg_h}
                            s = score_params(races, cb, dr, temp_f, deg_pow, n=QUICK_N)
                            if s > best_score:
                                best_score  = s
                                best_params = (soft_b, hard_b, deg_s, deg_m, deg_h, temp_f, deg_pow)
                                print(f"  ✓ new best {s}/{QUICK_N}: "
                                      f"soft={soft_b}, hard={hard_b}, "
                                      f"deg=({deg_s},{deg_m},{deg_h}), "
                                      f"temp={temp_f}, pow={deg_pow}",
                                      flush=True)

print(f"\n=== QUICK BEST: {best_score}/{QUICK_N} ===")
soft_b, hard_b, deg_s, deg_m, deg_h, temp_f, deg_pow = best_params

# ── Step 3: validate best params on 500 races ───────────────────────────────

print("\nValidating on 500 races …", flush=True)
cb = {'SOFT': soft_b, 'MEDIUM': 0.0, 'HARD': hard_b}
dr = {'SOFT': deg_s,  'MEDIUM': deg_m,  'HARD': deg_h}

score_500 = score_params(races, cb, dr, temp_f, deg_pow, n=500)
print(f"Score on 500 races: {score_500}/500  ({100*score_500//500}%)")

# ── Step 4: print final params ───────────────────────────────────────────────

print("\n=== BEST PARAMETERS ===")
print(f"  COMPOUND_BASE = {{'SOFT': {soft_b}, 'MEDIUM': 0.0, 'HARD': {hard_b}}}")
print(f"  DEGRADATION   = {{'SOFT': {deg_s}, 'MEDIUM': {deg_m}, 'HARD': {deg_h}}}")
print(f"  TEMP_FACTOR   = {temp_f}")
print(f"  DEG_POWER     = {deg_pow}")

print("\nNow paste these values into solution/race_simulator.py and run ./test_runner.sh")
