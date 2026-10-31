"""
Metrics I will compare on in report.
"""

import numpy as np

import config
from methods import Delivery
from workload import Reports


def _peak_per_second(times: np.ndarray) -> int:
    """
    Busiest 1-second window.
    """
    per_second = np.bincount(times.astype(np.int64), minlength=config.SECONDS_PER_DAY)
    return int(per_second.max())


def compute_metrics(delivery: Delivery, reports: Reports) -> dict:
    """
    Metrics for one run (one event, player count, method, and seed).

    Central server load (what the methods are trying to reduce):
        peak_msgs_per_s    Busiest second of messages arriving at the central server.
        total_messages     Messages received over the whole day.
        msgs_per_report    Messages needed per report (1.0 for Method 1, lower is better).
        total_data_mb      All message bytes (overhead + contents) in MB.

    Timeliness and accuracy (the price of aggregating):
        staleness_mean_s   Average delay between a report being made and reaching the central server.
        staleness_p95_s    95% of reports arrive within this many seconds.
        pct_delivered      Share of reports that reached the central server at all.

    Method 3 only:
        regional_peak_msgs_per_s   Busiest second across the regional servers' incoming messages.
    """
    # Reports with NaN delivery time never arrived.
    arrived = ~np.isnan(delivery.report_delivery_time)
    staleness = delivery.report_delivery_time[arrived] - reports.action_time[arrived]

    result = {
        "peak_msgs_per_s": _peak_per_second(delivery.msg_time),
        "total_messages": len(delivery.msg_time),
        "msgs_per_report": len(delivery.msg_time) / reports.count,
        "total_data_mb": float(delivery.msg_bytes.sum() / 1e6),
        "staleness_mean_s": float(staleness.mean()) if arrived.any() else np.nan,
        "staleness_p95_s": float(np.percentile(staleness, 95)) if arrived.any() else np.nan,
        "pct_delivered": float(100 * arrived.mean()),
    }

    # Total load across all regional servers.
    if delivery.regional_msg_time is not None:
        result["regional_peak_msgs_per_s"] = _peak_per_second(delivery.regional_msg_time)

    return result
