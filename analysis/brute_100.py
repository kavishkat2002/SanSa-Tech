import json
from pathlib import Path
from itertools import product
import time

def get_order(stats, s_off, h_off, s_r, m_r, h_r, t_f, p):
    results = []
    # stats: list of (id, grid, const, nS, nM, nH, S_pow, M_pow, H_pow, temp_part)
    for s in stats:
        t = (s[2] + 
             s_off * s[3] + 
             h_off * s[5] + 
             s_r * s[6] + 
             m_r * s[7] + 
             h_r * s[8] + 
             t_f * s[9])
        results.append((s[0], t, s[1]))
    # Sort consistent with engine: (round(time, 10), grid)
    return [x[0] for x in sorted(results, key=lambda x: (round(x[1], 10), x[2]))]

def run():
    path = Path("data/historical_races/races_00000-00999.json")
    r0 = json.load(open(path))[0]
    target = r0["finishing_positions"]
    
    # Precalculate for speed: (id, grid, const, nS, nM, nH, S_pow, M_pow, H_pow, sum_temp)
    # SUM_TEMP = track_temp * total_laps
    p = 2.0
    cfg = r0["race_config"]
    stats = []
    for pk, st in r0["strategies"].items():
        g = int(pk[3:])
        id = st["driver_id"]
        c = cfg["base_lap_time"] * cfg["total_laps"] + len(st.get("pit_stops", [])) * cfg["pit_lane_time"]
        ns, nm, nh = 0, 0, 0
        sp, mp, hp = 0.0, 0.0, 0.0
        age = 0
        cur = st["starting_tire"]
        ps = {x["lap"]: x["to_tire"] for x in st.get("pit_stops", [])}
        for l in range(1, cfg["total_laps"]+1):
            age += 1
            if cur == "SOFT": ns += 1; sp += (age**p)
            elif cur == "MEDIUM": nm += 1; mp += (age**p)
            elif cur == "HARD": nh += 1; hp += (age**p)
            if l in ps: cur = ps[l]; age = 0
        stats.append((id, g, c, ns, nm, nh, sp, mp, hp, float(cfg["track_temp"] * cfg["total_laps"])))

    print("🚀 Brute forcing Race 0 with WIDE GRID...")
    
    # Grid: (Step 0.1 for offsets, 0.001 for rates)
    # To keep it fast, we use nested loops and pruning
    for s_o in [-3.0, -2.5, -2.0]:
        for h_o in [2.0, 2.5, 3.0]:
            print(f"Checking so={s_o}, ho={h_o}")
            for s_r in [0.03, 0.04, 0.05, 0.06]:
                for m_r in [0.015, 0.02, 0.025]:
                    for h_r in [0.005, 0.01]:
                        for t_f in [0.0, 0.01, 0.02]:
                            if get_order(stats, s_o, h_o, s_r, m_r, h_r, t_f, p) == target:
                                print(f"  ✓ FOUND MATCH: so={s_o}, ho={h_o}, sr={s_r}, mr={m_r}, hr={h_r}, tf={t_f}")
                                return

if __name__ == "__main__":
    run()
