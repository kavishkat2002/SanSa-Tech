import json
import sys
from pathlib import Path
from itertools import product
import time

def precalculate_race_stats(race, power_list):
    cfg        = race['race_config']
    base       = cfg['base_lap_time']
    # pit_lane_time field name in data_format.md is pit_lane_time
    # Let's check the json again... it is pit_lane_time.
    pit_time   = cfg['pit_lane_time']
    track_temp = cfg['track_temp']
    total_laps = cfg['total_laps']

    drivers_stats = []
    for pos_key, strategy in race['strategies'].items():
        grid_pos = int(pos_key[3:])
        driver_id = strategy['driver_id']
        current_tire = strategy['starting_tire']
        
        stats = {
            'driver_id': driver_id,
            'grid_pos': grid_pos,
            'const': base * total_laps + len(strategy.get('pit_stops', [])) * pit_time,
            'nS': 0, 'nM': 0, 'nH': 0,
            'S_age_pow': {p: 0.0 for p in power_list},
            'M_age_pow': {p: 0.0 for p in power_list},
            'H_age_pow': {p: 0.0 for p in power_list},
            'temp_part': float(track_temp * total_laps)
        }

        # Regulations §Tire Age Tracking: tire_age resets to 0, increments to 1 for first lap
        tire_age = 0
        pit_stops = {p['lap']: p['to_tire'] for p in strategy.get('pit_stops', [])}
        for lap in range(1, total_laps + 1):
            tire_age += 1
            if current_tire == 'SOFT':
                stats['nS'] += 1
                for p in power_list: stats['S_age_pow'][p] += (tire_age ** p)
            elif current_tire == 'MEDIUM':
                stats['nM'] += 1
                for p in power_list: stats['M_age_pow'][p] += (tire_age ** p)
            elif current_tire == 'HARD':
                stats['nH'] += 1
                for p in power_list: stats['H_age_pow'][p] += (tire_age ** p)
            
            if lap in pit_stops:
                current_tire = pit_stops[lap]
                tire_age = 0
        
        drivers_stats.append(stats)
    return drivers_stats

def fast_score(all_stats, targets, s_off, h_off, s_r, m_r, h_r, t_f, p, n):
    correct = 0
    for i in range(n):
        stats_list = all_stats[i]
        results = []
        for s in stats_list:
            total_time = (
                s['const'] +
                s_off * s['nS'] +
                h_off * s['nH'] +
                s_r * s['S_age_pow'][p] +
                m_r * s['M_age_pow'][p] +
                h_r * s['H_age_pow'][p] +
                t_f * s['temp_part']
            )
            results.append((s['driver_id'], total_time, s['grid_pos']))
        
        # Sort by total_time and grid_pos
        pred = [d[0] for d in sorted(results, key=lambda x: x[1])]
        if pred == targets[i]:
            correct += 1
    return correct

def run():
    print("Loading data...")
    path = Path("data/historical_races/races_00000-00999.json")
    races = json.load(open(path))
    targets = [r["finishing_positions"] for r in races]

    print("Precalculating...")
    powers = [1.0, 1.5, 2.0, 2.5, 3.0]
    all_stats = [precalculate_race_stats(r, powers) for r in races[:100]]

    # Grid from discover_and_fix.py
    SOFT_BASES   = [-4.0, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0]
    HARD_BASES   = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    DEG_SOFTS    = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10]
    DEG_MEDS     = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04]
    DEG_HARDS    = [0.001, 0.003, 0.005, 0.008, 0.01, 0.012, 0.015, 0.02]
    TEMP_FACTORS = [0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03]
    
    total = len(SOFT_BASES) * len(HARD_BASES) * len(DEG_SOFTS) * len(DEG_MEDS) * len(DEG_HARDS) * len(TEMP_FACTORS) * len(powers)
    print(f"Searching {total:,} combinations...")

    best_score = -1
    best_params = None
    
    start = time.time()
    for p in powers:
        print(f"Checking power {p}...")
        for soft_b, hard_b, deg_s, deg_m, deg_h, temp_f in product(SOFT_BASES, HARD_BASES, DEG_SOFTS, DEG_MEDS, DEG_HARDS, TEMP_FACTORS):
            # Sample check on 10 races
            score = fast_score(all_stats, targets, soft_b, hard_b, deg_s, deg_m, deg_h, temp_f, p, 10)
            
            if score > best_score:
                # Re-check on 50 races
                score = fast_score(all_stats, targets, soft_b, hard_b, deg_s, deg_m, deg_h, temp_f, p, 50)
                if score > best_score:
                    best_score = score
                    best_params = (soft_b, hard_b, deg_s, deg_m, deg_h, temp_f, p)
                    print(f"  ✓ [{best_score}/50] Found: s={soft_b}, h={hard_b}, deg=({deg_s},{deg_m},{deg_h}), t={temp_f}, p={p}")

                    if score == 50:
                        print("\n🎉 PERFECT MATCH FOUND!")
                        return

    print(f"\nFinished. Best: {best_score}")

if __name__ == "__main__":
    run()
