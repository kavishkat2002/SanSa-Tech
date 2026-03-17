import json
from pathlib import Path
from itertools import product
import time

def precalculate_race_stats(race, p):
    cfg        = race['race_config']
    base       = cfg['base_lap_time']
    # Many users use pit_lane_time, let's verify again
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
            'age_pow_sum': 0.0,
            'S_age_pow': 0.0, 'M_age_pow': 0.0, 'H_age_pow': 0.0,
            'temp_part': float(track_temp * total_laps)
        }

        tire_age = 0
        pit_stops = {p['lap']: p['to_tire'] for p in strategy.get('pit_stops', [])}
        for lap in range(1, total_laps + 1):
            tire_age += 1
            term = (tire_age ** p)
            if current_tire == 'SOFT':
                stats['nS'] += 1
                stats['S_age_pow'] += term
            elif current_tire == 'MEDIUM':
                stats['nM'] += 1
                stats['M_age_pow'] += term
            elif current_tire == 'HARD':
                stats['nH'] += 1
                stats['H_age_pow'] += term
            
            if lap in pit_stops:
                current_tire = pit_stops[lap]
                tire_age = 0
        
        drivers_stats.append(stats)
    return drivers_stats

def is_match(stats_list, target, s_off, h_off, s_r, m_r, h_r, t_f):
    results = []
    for s in stats_list:
        total_time = (
            s['const'] +
            s_off * s['nS'] +
            h_off * s['nH'] +
            s_r * s['S_age_pow'] +
            m_r * s['M_age_pow'] +
            h_r * s['H_age_pow'] +
            t_f * s['temp_part']
        )
        results.append((s['driver_id'], total_time, s['grid_pos']))
    
    # Using simple x[1] sort
    pred = [d[0] for d in sorted(results, key=lambda x: x[1])]
    return pred == target

def run():
    path = Path("data/historical_races/races_00000-00999.json")
    races = json.load(open(path))[:10]
    targets = [r["finishing_positions"] for r in races]

    SOFT_BASES   = [-4.0, -3.5, -3.0, -2.8, -2.5, -2.0, -1.5, -1.0]
    HARD_BASES   = [1.0, 1.5, 2.0, 2.5, 3.0, 3.2, 3.5, 4.0, 5.0]
    DEG_SOFTS    = [0.02, 0.03, 0.035, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10]
    DEG_MEDS     = [0.005, 0.01, 0.015, 0.018, 0.02, 0.025, 0.03, 0.04]
    DEG_HARDS    = [0.001, 0.003, 0.005, 0.008, 0.009, 0.01, 0.012, 0.015, 0.02]
    TEMP_FACTORS = [0.0, 0.005, 0.01, 0.012, 0.015, 0.02, 0.025, 0.03]
    POWERS       = [1.8, 1.9, 2.0, 2.1, 2.2]

    print("🚀 Exhaustive search for parameters matching Race 1-3...")

    start = time.time()
    for p in POWERS:
        print(f"Checking power {p}...")
        race1_stats = precalculate_race_stats(races[0], p)
        candidates = []
        for soft_b, hard_b, deg_s, deg_m, deg_h, temp_f in product(SOFT_BASES, HARD_BASES, DEG_SOFTS, DEG_MEDS, DEG_HARDS, TEMP_FACTORS):
            if is_match(race1_stats, targets[0], soft_b, hard_b, deg_s, deg_m, deg_h, temp_f):
                candidates.append((soft_b, hard_b, deg_s, deg_m, deg_h, temp_f))
        
        print(f"  Found {len(candidates)} candidates matching Race 1 at power {p}")
        
        # Now check these candidates on next 9 races
        other_stats = [precalculate_race_stats(r, p) for r in races[1:]]
        for c in candidates:
            score = 1
            for i in range(1, 10):
                if is_match(other_stats[i-1], targets[i], *c):
                    score += 1
                else:
                    break
            
            if score >= 5:
                # Validate on 50 more races
                print(f"    🔥 Candidate with score {score}/10: {c}")
                if score == 10:
                    print("\n🎉 PERFECT MATCH FOUND!")
                    print(f'POW: {p}, Params: {c}')
                    return

    print(f"\nTime: {time.time()-start:.1f}s")
if __name__ == "__main__":
    run()
