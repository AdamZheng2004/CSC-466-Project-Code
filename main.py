"""
Runs every simulation and prints the results.
Each event is run at each player count with each method.
"""

import csv
import time

import config
from workload import generate_reports
from methods import method1
from metrics import compute_metrics

SEED = 42
METHODS = {"Method 1": method1}

# Run everything. 
# The same Reports table is shared by all methods for a given event and player count.
results = []
start = time.time()
for event in config.EVENTS.values():
    for n_players in config.PLAYER_COUNTS:
        reports = generate_reports(event, n_players, SEED)
        for method_name, method in METHODS.items():
            metrics = compute_metrics(method(reports), reports)
            results.append({"event": event.name, "players": n_players, "method": method_name,
                            "reports": reports.count, **metrics})
        print(f"done: {event.name}, {n_players:,} players")
print(f"\nFinished {len(results)} runs in {time.time() - start:.0f}s")

# Print one table per event.
header = (f"{'Players':>10} {'Method':<9} {'Reports':>12} {'Peak msg/s':>11} {'Messages':>12} "
          f"{'Data (MB)':>10} {'Stale mean':>11} {'Stale p95':>10} {'Delivered':>10}")
for event in config.EVENTS.values():
    print(f"\n{event.name}")
    print(header)
    print("-" * len(header))
    for r in results:
        if r["event"] != event.name:
            continue
        print(f"{r['players']:>10,} {r['method']:<9} {r['reports']:>12,} {r['peak_msgs_per_s']:>11,} "
              f"{r['total_messages']:>12,} {r['total_data_mb']:>10,.1f} {r['staleness_mean_s']:>10.1f}s "
              f"{r['staleness_p95_s']:>9.1f}s {r['pct_delivered']:>9.1f}%")

# Save to a CSV for later plotting.
# Might put plotting code here if not too crowded.
with open("results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)
print("\nSaved results.csv")