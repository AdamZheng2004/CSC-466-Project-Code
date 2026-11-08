"""
Runs every simulation and prints the results.
Each event is run at each player count with each method, once per seed in config.SEEDS.
Saves every individual run (results.csv) and the average across seeds (results_summary.csv).
"""

import csv
import time

import numpy as np

import config
from workload import generate_reports
from methods import method1, method2, method3
from metrics import compute_metrics

METHODS = {"Method 1": method1, "Method 2": method2, "Method 3": method3}


def write_csv(path, rows):
    # Method 3 has extra columns, so use every key that appears (blank where a row doesn't have it).
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader()
        writer.writerows(rows)


# Run everything. 
# The same Reports table is shared by all methods for a given event, player count and seed.
results = []
start = time.time()
for seed in config.SEEDS:
    for event in config.EVENTS.values():
        for n_players in config.PLAYER_COUNTS:
            reports = generate_reports(event, n_players, seed)
            for method_name, method in METHODS.items():
                # Separate random stream for the methods (Method 2's crashes) so it never changes the workload.
                rng = np.random.default_rng([seed, 2])
                metrics = compute_metrics(method(reports, rng), reports)
                results.append({"seed": seed, "event": event.name, "players": n_players, "method": method_name,
                                "reports": reports.count, **metrics})
            print(f"done: seed {seed}, {event.name}, {n_players:,} players")
print(f"\nFinished {len(results)} runs in {time.time() - start:.0f}s")

# Average over seeds for each (event, players, method). Also keep the standard deviation (_std) to show seed-to-seed noise.
groups = {}
for r in results:
    groups.setdefault((r["event"], r["players"], r["method"]), []).append(r)

metric_keys = [k for k in dict.fromkeys(k for r in results for k in r)
               if k not in ("seed", "event", "players", "method")]
summary = []
for (event_name, n_players, method_name), runs in groups.items():
    row = {"event": event_name, "players": n_players, "method": method_name, "seeds": len(runs)}
    for k in metric_keys:
        vals = [r[k] for r in runs if k in r]
        if vals:
            row[k] = float(np.mean(vals))
            row[k + "_std"] = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
    summary.append(row)

# Print one table per event (averages over seeds).
header = (f"{'Players':>10} {'Method':<9} {'Peak msg/s':>11} {'Central msgs':>13} {'System msgs':>13} "
          f"{'Data (MB)':>10} {'Stale mean':>11} {'Stale p95':>10} {'Lost %':>7} {'Reg peak/s':>11}")
print(f"\nAverages over {len(config.SEEDS)} seeds")
for event in config.EVENTS.values():
    print(f"\n{event.name}")
    print(header)
    print("-" * len(header))
    for r in summary:
        if r["event"] != event.name:
            continue
        reg = f"{r['regional_peak_msgs_per_s']:>11,.1f}" if "regional_peak_msgs_per_s" in r else f"{'-':>11}"
        print(f"{r['players']:>10,} {r['method']:<9} {r['peak_msgs_per_s']:>11,.0f} {r['total_messages']:>13,.0f} "
              f"{r['system_total_messages']:>13,.0f} {r['total_data_mb']:>10,.1f} {r['staleness_mean_s']:>10.1f}s "
              f"{r['staleness_p95_s']:>9.1f}s {100 - r['pct_delivered']:>6.2f}% {reg}")

# Save to CSVs for later plotting.
write_csv("results.csv", results)
write_csv("results_summary.csv", summary)
print("\nSaved results.csv (every run) and results_summary.csv (averages over seeds)")