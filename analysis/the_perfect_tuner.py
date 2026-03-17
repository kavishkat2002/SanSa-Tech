import json
from pathlib import Path
from itertools import product
import time

def precalculate_race_stats(race, powers):
    cfg        = race['race_config']
    base       = cfg['base_lap_time']
    # Sometimes it's pit_time, sometimes pit_lane_time. Let's stick with pit_lane_time as in discover_and_fix.py
    pit_time   = cfg.get('pit_lane_time', cfg.get('pit_time', 0))
    track_temp = cfg['track_temp']
    total_laps = cfg['total_laps']

    drivers_stats = []
    for pos_key, strategy in race['strategies'].items():
        grid_pos = int(pos_key[3:])
        driver_id = strategy['driver_id']
        current_tire = strategy['starting_tire']
        
        stats = {
            'id': driver_id,
            'grid': grid_pos,
            'const': base * total_laps + len(strategy.get('pit_stops', [])) * pit_time,
            'n': {"SOFT": 0, "MEDIUM": 0, "HARD": 0},
            'age_pow': {p: {"SOFT": 0.0, "MEDIUM": 0.0, "HARD": 0.0} for p in powers},
            'track_temp': float(track_temp),
            'total_laps': float(total_laps)
        }

        age = 0
        pit_stops = {p['lap']: p['to_tire'] for p in strategy.get('pit_stops', [])}
        for lap in range(1, total_laps + 1):
            age += 1 # Age increments before calculation
            stats['n'][current_tire] += 1
            for p in powers:
                stats['age_pow'][p][current_tire] += (age ** p)
            
            if lap in pit_stops:
                current_tire = pit_stops[lap]
                age = 0
        
        drivers_stats.append(stats)
    return drivers_stats

def get_order(stats_list, s_off, h_off, s_r, m_r, h_r, t_f, p):
    results = []
    for s in stats_list:
        total_time = (
            s['const'] +
            s_off * s['n']["SOFT"] +
            h_off * s['n']["HARD"] +
            s_r * s['age_pow'][p]["SOFT"] +
            m_r * s['age_pow'][p]["MEDIUM"] +
            h_r * s['age_pow'][p]["HARD"] +
            t_f * s['track_temp'] * s['total_laps']
        )
        results.append((s['id'], total_time, s['grid']))
    
    # Matching deterministic Engine sort: (round(time, 10), grid)
    return [x[0] for x in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def run():
    path = Path("data/historical_races/races_00000-00999.json")
    races = json.load(open(path))[:100]
    targets = [r["finishing_positions"] for r in races]

    # Grid from discover_and_fix.py
    S_B = [-4.0, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0]
    H_B = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    D_S = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10]
    D_M = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04]
    D_H = [0.001, 0.003, 0.005, 0.008, 0.01, 0.012, 0.015, 0.02]
    T_F = [0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03]
    POWERS = [1.0, 1.5, 2.0, 2.5, 3.0]

    print("Precalculating stats...")
    all_stats = [precalculate_race_stats(r, POWERS) for r in races]

    print("🚀 Super-fast search (Filtered by Race 0)...")
    start = time.time()
    for p, t_f in product(POWERS, T_F):
        print(f"Checking power {p}, temp={t_f}...")
        for s_off, h_off, s_r, m_r, h_r in product(S_B, H_B, D_S, D_M, D_H):
            # Check Race 0
            if get_order(all_stats[0], s_off, h_off, s_r, m_r, h_r, t_f, p) == targets[0]:
                score = 1
                # Check Race 1-4
                for i in range(1, 5):
                    if get_order(all_stats[i], s_off, h_off, s_r, m_r, h_r, t_f, p) == targets[i]:
                        score += 1
                    else: break
                
                if score >= 3:
                    print(f"  ✓ Candidate with score {score}/5 found: p={p}, s={s_off}, h={h_off}, s_r={s_r}, m_r={m_r}, h_r={h_r}, t={t_f}")
                    # check all 100
                    final_score = score
                    for i in range(score, 100):
                        if get_order(all_stats[i], s_off, h_off, s_r, m_r, h_r, t_f, p) == targets[i]: final_score += 1
                        else: break
                    print(f"    FINAL SCORE: {final_score}/100")
                    if final_score == 100:
                        print("\n🎉 PERFECT MATCH FOUND!")
                        return

if __name__ == "__main__":
    run()
