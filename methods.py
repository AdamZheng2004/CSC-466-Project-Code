"""
Aggregation Methods:

Each method takes the Reports table from workload.py and returns a Delivery describing what the central server receives. 
All three methods should return the same format, so the metrics code can treat them identically.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

import config
from workload import Reports


@dataclass
class Delivery:
    """
    What reaches the central server.
    Messages (one row per message, what the server has to process)
    """
    msg_time: np.ndarray       # when each message arrives at the central server (seconds since reset).
    msg_reports: np.ndarray    # how many reports each message carries.
    msg_bytes: np.ndarray      # size of each message in bytes.

    # Reports (one row per report, same order as the Reports table, used for timeliness and accuracy):
    # When the report reached the central server (NaN = never arrived).
    report_delivery_time: np.ndarray   

    # Method 3 only: arrival times of the messages that devices send to the regional servers.
    regional_msg_time: Optional[np.ndarray] = None


def method1(reports: Reports) -> Delivery:
    """
    Method 1: 
    
    Every device sends its report to the central server immediately after the action.
    One report = one message, sent the moment the player acts. 
    There is no waiting or grouping, so this is the baseline the other two methods are compared against.
    Network travel time is ignored for every method, so a report arrives at the same time it was made (staleness is 0).
    """
    n = reports.count

    # Each message arrives when the report is made.
    msg_time = reports.action_time.copy()

    # Every message carries exactly one report.
    msg_reports = np.ones(n, dtype=np.int32)

    # Every message pays the fixed overhead plus one report's contents.
    msg_bytes = np.full(n, config.MSG_OVERHEAD_BYTES + config.REPORT_PAYLOAD_BYTES, dtype=np.int32)

    # No delay, so each report is delivered at the time it was made.
    report_delivery_time = reports.action_time.copy()

    return Delivery(msg_time, msg_reports, msg_bytes, report_delivery_time)


def method2(reports: Reports) -> Delivery:
    """
    Method 2
    """


def method3(reports: Reports) -> Delivery:
    """
    Method 3
    """
