"""
Turns results_summary.csv (written by main.py) into comparison graphs.
Run main.py first, then run this file. Plots are saved as PNGs in the graphs/ folder.

Kept separate from main.py so graphs can be tweaked and redrawn instantly without re-running the ~2 minute simulation.
"""

import csv
import os

import matplotlib.pyplot as plt
import numpy as np

SUMMARY_CSV = "results_summary.csv"
OUT_DIR = "graphs"

EVENTS = ["Global Raids", "Season Rankings", "Prestige Races"]
METHODS = ["Method 1", "Method 2", "Method 3"]
METHOD_LABELS = {
    "Method 1": "Method 1 (report per action)",
    "Method 2": "Method 2 (batch per session)",
    "Method 3": "Method 3 (regional servers)",
}
COLORS = {"Method 1": "#4C72B0", "Method 2": "#DD8452", "Method 3": "#55A868"}


def load_summary(path):
    """
    Reads results_summary.csv into {(event, players, method): {column: float}}.
    Blank cells (e.g. regional columns for Methods 1 and 2) become NaN.
    """
    data = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            clean = {}
            for k, v in row.items():
                if k in ("event", "method"):
                    continue
                clean[k] = float(v) if v not in ("", None) else float("nan")
            clean["pct_lost"] = 100 - clean["pct_delivered"]
            clean["pct_lost_std"] = clean["pct_delivered_std"]
            data[(row["event"], int(row["players"]), row["method"])] = clean
    return data


def val(data, event, players, method, metric):
    return data[(event, players, method)].get(metric, float("nan"))


def fmt_players(n):
    return f"{n // 1_000_000}M" if n >= 1_000_000 else f"{n // 1_000}k"


def grouped_bars(data, metric, ylabel, title, filename, log=False, symlog=False,
                 methods=METHODS, scale=1.0, percent_fmt=False):
    """
    One panel per event, x = player count, one bar per method, error bars = seed-to-seed std.
    """
    players = sorted({k[1] for k in data})
    fig, axes = plt.subplots(1, len(EVENTS), figsize=(15, 4.6), sharey=True)
    width = 0.8 / len(methods)
    x = np.arange(len(players))

    for ax, event in zip(axes, EVENTS):
        for i, m in enumerate(methods):
            vals = np.array([val(data, event, p, m, metric) for p in players]) * scale
            errs = np.array([val(data, event, p, m, metric + "_std") for p in players]) * scale
            pos = x + (i - (len(methods) - 1) / 2) * width
            ax.bar(pos, vals, width, yerr=errs, capsize=2, color=COLORS[m], label=METHOD_LABELS[m])
        ax.set_title(event)
        ax.set_xticks(x)
        ax.set_xticklabels([fmt_players(p) for p in players])
        ax.set_xlabel("Players")
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        if log:
            ax.set_yscale("log")
        elif symlog:
            ax.set_yscale("symlog", linthresh=1)
    axes[0].set_ylabel(ylabel)
    if percent_fmt:
        axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}%"))

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(methods), frameon=False)
    fig.suptitle(title, fontsize=13)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    path = os.path.join(OUT_DIR, filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("saved", path)


def central_vs_system_messages(data):
    """
    Method 3's central-server savings come with extra regional-tier messages, so show central vs whole-system load.
    """
    players = sorted({k[1] for k in data})
    fig, axes = plt.subplots(1, len(EVENTS), figsize=(15, 4.6), sharey=True)
    x = np.arange(len(players))
    width = 0.2
    series = [
        ("Method 1", "total_messages", "Method 1 (central)", COLORS["Method 1"], None),
        ("Method 2", "total_messages", "Method 2 (central)", COLORS["Method 2"], None),
        ("Method 3", "total_messages", "Method 3 (central only)", COLORS["Method 3"], None),
        ("Method 3", "system_total_messages", "Method 3 (central + regional)", COLORS["Method 3"], "//"),
    ]
    for ax, event in zip(axes, EVENTS):
        for i, (m, col, label, color, hatch) in enumerate(series):
            heights = [val(data, event, p, m, col) for p in players]
            errs = [val(data, event, p, m, col + "_std") for p in players]
            ax.bar(x + (i - 1.5) * width, heights, width, yerr=errs, capsize=2,
                   color=color, hatch=hatch, edgecolor="white" if hatch else None, label=label)
        ax.set_title(event)
        ax.set_xticks(x)
        ax.set_xticklabels([fmt_players(p) for p in players])
        ax.set_xlabel("Players")
        ax.set_yscale("log")
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Messages per day (log scale)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.suptitle("Central-server vs whole-system messages (Method 3 savings are not free)", fontsize=13)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    path = os.path.join(OUT_DIR, "system_vs_central_messages.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("saved", path)


def tradeoff_scatter(data, players):
    """
    Load vs timeliness: one panel per event at a single player count. Down-and-left is better.
    """
    fig, axes = plt.subplots(1, len(EVENTS), figsize=(15, 4.6))
    for ax, event in zip(axes, EVENTS):
        for m in METHODS:
            row = data[(event, players, m)]
            ax.scatter(row["staleness_p95_s"], row["peak_msgs_per_s"], s=140, color=COLORS[m],
                       label=METHOD_LABELS[m], zorder=3)
            ax.annotate(f"{row['pct_delivered']:.1f}% delivered", (row["staleness_p95_s"], row["peak_msgs_per_s"]),
                        textcoords="offset points", xytext=(8, 6), fontsize=8)
        ax.set_title(event)
        ax.set_xscale("symlog", linthresh=1)
        ax.set_yscale("log")
        ax.set_xlabel("p95 staleness (s, symlog)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Peak central msgs/s (log)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    fig.suptitle(f"Load vs timeliness trade-off at {fmt_players(players)} players (lower-left is better)", fontsize=13)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    path = os.path.join(OUT_DIR, f"tradeoff_{fmt_players(players)}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("saved", path)


def main():
    if not os.path.exists(SUMMARY_CSV):
        raise SystemExit(f"{SUMMARY_CSV} not found. Run main.py first.")
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_summary(SUMMARY_CSV)

    # Central-server load.
    grouped_bars(df, "peak_msgs_per_s", "Peak messages/s at central server (log)",
                 "Central-server peak load", "central_peak_msgs_per_s.png", log=True)
    grouped_bars(df, "total_messages", "Messages per day (log)",
                 "Central-server total messages per day", "central_total_messages.png", log=True)
    grouped_bars(df, "total_data_mb", "Data per day (MB, log)",
                 "Central-server total bandwidth per day", "central_total_data_mb.png", log=True)
    central_vs_system_messages(df)

    # Price of aggregating: timeliness and accuracy.
    grouped_bars(df, "staleness_mean_s", "Mean staleness (s, symlog)",
                 "Mean delay before a report reaches the central server", "staleness_mean.png", symlog=True)
    grouped_bars(df, "staleness_p95_s", "p95 staleness (s, symlog)",
                 "95th-percentile delay before a report reaches the central server", "staleness_p95.png", symlog=True)
    grouped_bars(df, "pct_lost", "Reports lost (%)",
                 "Accuracy: share of reports never counted (Method 2 app close/crash)", "reports_lost.png",
                 percent_fmt=True)

    # Method 3 regional tier cost.
    m3 = {k: v for k, v in df.items() if k[2] == "Method 3"}
    grouped_bars(m3, "regional_peak_utilization_pct", "Peak utilization of busiest regional server (%)",
                 "Method 3 regional tier: peak utilization (over 100% = overloaded)",
                 "regional_utilization.png", methods=["Method 3"], percent_fmt=True)
    grouped_bars(m3, "regional_max_queue_delay_s", "Max queue delay (s)",
                 "Method 3 regional tier: longest queue wait", "regional_queue_delay.png", methods=["Method 3"])

    # Load vs timeliness summary at the largest scale.
    tradeoff_scatter(df, max(k[1] for k in df))

    print(f"\nAll graphs saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()