import json
from pathlib import Path
from itertools import product
import time

def precalculate_race_stats(race, p):
    cfg        = race['race_config']
    base       = cfg['base_lap_time']
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
            'S_age_pow': 0.0, 'M_age_pow': 0.0, 'H_age_pow': 0.0,
            'track_temp': float(track_temp)
        }

        tire_age = 0
        pit_stops = {p['lap']: p['to_tire'] for p in strategy.get('pit_stops', [])}
        for lap in range(1, total_laps + 1):
            tire_age += 1
            # Using (age - 1) as stint_laps
            term = ((tire_age - 1) ** p)
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

def get_order(stats_list, s_off, h_off, s_r, m_r, h_r, t_f):
    results = []
    for s in stats_list:
        # Multiplicative: Deg * (1 + t_f * track_temp)
        factor = (1 + t_f * s['track_temp'])
        total_time = (
            s['const'] +
            s_off * s['nS'] +
            h_off * s['nH'] +
            s_r * factor * s['S_age_pow'] +
            m_r * factor * s['M_age_pow'] +
            h_r * factor * s['H_age_pow']
        )
        results.append((s['driver_id'], total_time, s['grid_pos']))
    
    return [d[0] for d in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def run():
    path = Path("data/historical_races/races_00000-00999.json")
    races = json.load(open(path))[:100]
    targets = [r["finishing_positions"] for r in races]

    SOFT_BASES   = [-3.0, -2.5, -2.0, -1.5, -1.0]
    HARD_BASES   = [1.0, 1.5, 2.0, 2.5, 3.0]
    DEG_SOFTS    = [0.03, 0.04, 0.05]
    DEG_MEDS     = [0.015, 0.02, 0.025]
    DEG_HARDS    = [0.005, 0.008, 0.01]
    TEMP_FACTORS = [0.001, 0.005, 0.01, 0.02]
    p = 2.0

    print("🚀 Multiplicative search...")
    race_stats = [precalculate_race_stats(r, p) for r in races]

    for s_off, h_off, s_r, m_r, h_r, t_f in product(SOFT_BASES, HARD_BASES, DEG_SOFTS, DEG_MEDS, DEG_HARDS, TEMP_FACTORS):
        if get_order(race_stats[0], s_off, h_off, s_r, m_r, h_r, t_f) == targets[0]:
            print(f"  ✓ Match on Race 0: s={s_off}, h={h_off}, deg=({s_r},{m_r},{h_r}), t={t_f}")
            # check more...

if __name__ == "__main__":
    run()
