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
        reports_lost       Reports that never reached the central server (Method 2 crashes/closed apps).

    Whole-system load (so Method 3's savings aren't counted as free):
        system_total_messages   Central messages + messages into the regional tier.
        system_total_data_mb    Same, in MB.

    Method 3 only (regional tier cost):
        regional_servers, regional_total_messages, regional_total_data_mb,
        regional_peak_msgs_per_s       Busiest second on the busiest single regional server.
        regional_peak_utilization_pct  That peak as a % of REGIONAL_SERVICE_RATE (over 100 = overloaded).
        regional_max_queue_delay_s, regional_mean_queue_delay_s
    """
    # Reports with NaN delivery time never arrived.
    arrived = ~np.isnan(delivery.report_delivery_time)
    staleness = delivery.report_delivery_time[arrived] - reports.action_time[arrived]

    central_mb = float(delivery.msg_bytes.sum() / 1e6)
    result = {
        "peak_msgs_per_s": _peak_per_second(delivery.msg_time),
        "total_messages": len(delivery.msg_time),
        "msgs_per_report": len(delivery.msg_time) / reports.count,
        "total_data_mb": central_mb,
        "staleness_mean_s": float(staleness.mean()) if arrived.any() else np.nan,
        "staleness_p95_s": float(np.percentile(staleness, 95)) if arrived.any() else np.nan,
        "pct_delivered": float(100 * arrived.mean()),
        "reports_lost": int((~arrived).sum()),
    }

    # Without a regional tier, the system's load is just the central server's.
    system_msgs = len(delivery.msg_time)
    system_mb = central_mb

    if delivery.regional_servers is not None:
        # Each device -> regional message is the same size as a Method 1 message.
        regional_mb = delivery.regional_msgs * (config.MSG_OVERHEAD_BYTES + config.REPORT_PAYLOAD_BYTES) / 1e6
        result["regional_servers"] = delivery.regional_servers
        result["regional_total_messages"] = delivery.regional_msgs
        result["regional_total_data_mb"] = regional_mb
        result["regional_peak_msgs_per_s"] = delivery.regional_peak_msgs_per_s
        result["regional_peak_utilization_pct"] = 100 * delivery.regional_peak_msgs_per_s / config.REGIONAL_SERVICE_RATE
        result["regional_max_queue_delay_s"] = delivery.regional_max_queue_delay_s
        result["regional_mean_queue_delay_s"] = delivery.regional_mean_queue_delay_s
        system_msgs += delivery.regional_msgs
        system_mb += regional_mb

    result["system_total_messages"] = system_msgs
    result["system_total_data_mb"] = system_mb
    return result