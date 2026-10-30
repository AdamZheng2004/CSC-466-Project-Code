import config
from workload import generate_reports
from methods import method1
from metrics import compute_metrics

reports = generate_reports(
    config.EVENTS["raids"],
    n_players=1000,
    seed=42
)

results = compute_metrics(method1(reports), reports)

print(f"Generated reports: {reports.count}")
print(results)