"""
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
    What reaches the central server: Messages(one row per message, what the server has to process):
    """
    msg_time: np.ndarray       # When each message arrives at the central server (seconds since reset).
    msg_reports: np.ndarray    # How many reports each message carries.
    msg_bytes: np.ndarray      # Size of each message in bytes.

    # Reports (one row per report, same order as the Reports table, used for timeliness and accuracy).
    report_delivery_time: np.ndarray

    # Method 3 only: the messages that devices send to their regional server (one per report).
    # Lets us check the regional servers' load. None for Methods 1 and 2.
    regional_msg_time: Optional[np.ndarray] = None
    regional_server: Optional[np.ndarray] = None   # which regional server each of those messages went to


def method1(reports: Reports) -> Delivery:
    """
    Method 1: 

    Every device sends its report to the central server immediately after the action.
    One report = one message, sent the moment the player acts. 
    There is no waiting and no grouping, so this is the baseline the other two methods are compared against.
    Network travel time is ignored for every method, so a report arrives at the same time it was made (staleness is 0).
    """
    n = reports.count

    # Each message arrives when the report is made.
    msg_time = reports.action_time.copy()

    # Every message carries exactly one report.
    msg_reports = np.ones(n, dtype=np.int32)

    # Every message has the fixed overhead plus one report's contents for size.
    msg_bytes = np.full(n, config.MSG_OVERHEAD_BYTES + config.REPORT_PAYLOAD_BYTES, dtype=np.int32)

    # No delay, each report is delivered at the time it was made.
    report_delivery_time = reports.action_time.copy()

    return Delivery(msg_time, msg_reports, msg_bytes, report_delivery_time)


def method2(reports: Reports) -> Delivery:
    """
    Method 2: 

    Each device groups all the reports from a gaming session and sends them together at the end of the session.
    One session = one message, carrying the summed total of that session's reports.
    The session is treated as ending at its last report. 
    Real sessions end a bit after the last action, so this slightly understates how long reports wait.
    A report's delay is the time from when it was made until its session ends.
    """
    # Group reports by session. `inverse` gives each report the index of its session.
    sessions, inverse, counts = np.unique(reports.session_id, return_inverse=True, return_counts=True)

    # The message is sent at the session's latest report time.
    send_time = np.zeros(len(sessions))
    np.maximum.at(send_time, inverse, reports.action_time)

    # One message per session, carrying one summed batch.
    msg_bytes = np.full(len(sessions), config.MSG_OVERHEAD_BYTES + config.BATCH_PAYLOAD_BYTES, dtype=np.int32)

    # Every report in a session is delivered when that session's message is sent.
    report_delivery_time = send_time[inverse]

    return Delivery(send_time, counts.astype(np.int32), msg_bytes, report_delivery_time)


def method3(reports: Reports) -> Delivery:
    """
    Method 3: 
    
    Devices send each report straight away to a regional server with players split evenly between regions (Globl Game).
    The regional server adds the reports up and sends the central server one combined message every FLUSH_INTERVAL_SECONDS (if it received anything). 
    Each server sends at its own offset within the interval, so the central server doesn't get every server's message in the same second. 
    A report waits for its server's next send.
    """
    T = config.FLUSH_INTERVAL_SECONDS
    n_servers = max(1, reports.n_players // config.PLAYERS_PER_REGIONAL_SERVER)

    # Which regional server each report goes to, and when that server sends (offset spread evenly over T).
    server = reports.player_id % n_servers
    offset = np.arange(n_servers) * T / n_servers

    # The report waits for its server's next send: slot m is the send at offset + m*T.
    slot = np.ceil((reports.action_time - offset[server]) / T).astype(np.int64)
    report_delivery_time = offset[server] + slot * T

    # One message per (server, slot) that had at least one report.
    slots_per_day = config.SECONDS_PER_DAY // T + 2
    keys, counts = np.unique(server * slots_per_day + slot, return_counts=True)
    msg_time = offset[keys // slots_per_day] + (keys % slots_per_day) * T

    # Each message carries one summed batch for that server and interval.
    msg_bytes = np.full(len(keys), config.MSG_OVERHEAD_BYTES + config.BATCH_PAYLOAD_BYTES, dtype=np.int32)

    return Delivery(msg_time, counts.astype(np.int32), msg_bytes, report_delivery_time,
                    regional_msg_time=reports.action_time.copy(), regional_server=server)