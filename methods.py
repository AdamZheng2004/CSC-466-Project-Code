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
    # NaN means the report never reached the central server (lost).
    report_delivery_time: np.ndarray

    # Method 3 only: the cost of the regional tier (None for Methods 1 and 2).
    regional_servers: Optional[int] = None               # How many regional servers are needed.
    regional_msgs: Optional[int] = None                  # Messages the regional tier receives from devices (one per report).
    regional_peak_msgs_per_s: Optional[int] = None       # Busiest second on the busiest single regional server.
    regional_max_queue_delay_s: Optional[float] = None   # Longest a report waited in a regional server's queue.
    regional_mean_queue_delay_s: Optional[float] = None  # Average queue wait per report.


def method1(reports: Reports, rng=None) -> Delivery:
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


def method2(reports: Reports, rng: np.random.Generator) -> Delivery:
    """
    Method 2: 

    Each device groups all the reports from a gaming session and sends them together at the end of the session.
    One session = one message, carrying the summed total of that session's reports.
    The session is treated as ending at its last report. 
    Real sessions end a bit after the last action, so this slightly understates how long reports wait.
    A report's delay is the time from when it was made until its session ends.

    Data loss: the batch is only in memory until it is sent, so a session can be lost entirely 
    (app closed before the send, or the game crashed). A lost session sends no message and 
    all its reports are never delivered.
    """
    # Group reports by session. `inverse` gives each report the index of its session.
    sessions, inverse, counts = np.unique(reports.session_id, return_inverse=True, return_counts=True)

    # The message is sent at the session's latest report time.
    send_time = np.zeros(len(sessions))
    np.maximum.at(send_time, inverse, reports.action_time)

    # A session is lost if either failure happens (treated as independent).
    p_lost = 1 - (1 - config.APP_CLOSED_BEFORE_SEND_PROB) * (1 - config.CRASH_PROB)
    lost = rng.random(len(sessions)) < p_lost
    sent = ~lost

    # One message per surviving session, carrying one summed batch.
    msg_bytes = np.full(int(sent.sum()), config.MSG_OVERHEAD_BYTES + config.BATCH_PAYLOAD_BYTES, dtype=np.int32)

    # Every report in a surviving session is delivered when that session's message is sent, reports in lost sessions never arrive.
    report_delivery_time = np.where(lost[inverse], np.nan, send_time[inverse])

    return Delivery(send_time[sent], counts[sent].astype(np.int32), msg_bytes, report_delivery_time)


def _regional_queue(arrival_time: np.ndarray, server: np.ndarray, n_servers: int):
    """
    Models each regional server as a queue that processes REGIONAL_SERVICE_RATE messages per second.
    Each second, the server's backlog grows by what arrived and shrinks by what it can process.
    A report arriving in a second waits (backlog / service rate) before it is processed.

    Returns (per-report queue delay in seconds, busiest second on any one server).
    """
    mu = config.REGIONAL_SERVICE_RATE
    horizon = config.SECONDS_PER_DAY
    second = arrival_time.astype(np.int64)

    # arrivals[s, t] = messages arriving at regional server s during second t.
    arrivals = np.bincount(server.astype(np.int64) * horizon + second,
                           minlength=n_servers * horizon).reshape(n_servers, horizon)
    peak = int(arrivals.max())

    # If no server is ever asked to do more than it can handle in a second, nothing ever queues.
    if peak <= mu:
        return np.zeros(len(arrival_time)), peak

    delay = np.zeros((n_servers, horizon))
    backlog = np.zeros(n_servers)
    for t in range(horizon):
        backlog = np.maximum(0.0, backlog + arrivals[:, t] - mu)
        delay[:, t] = backlog / mu
    return delay[server, second], peak


def method3(reports: Reports, rng=None) -> Delivery:
    """
    Method 3: 
    
    Devices send each report straight away to a regional server with players split evenly between regions (Global Game).
    The regional server adds the reports up and sends the central server one combined message every FLUSH_INTERVAL_SECONDS (if it received anything). 
    Each server sends at its own offset within the interval, so the central server doesn't get every server's message in the same second. 
    A report waits for its server's next send.

    Regional tier costs: every report is still one message to a regional server, so that load is tracked (peak msgs/s per server, 
    queueing delay if a server is overloaded). Reports also take an extra network leg (regional -> central).
    """
    T = config.FLUSH_INTERVAL_SECONDS
    n_servers = max(1, reports.n_players // config.PLAYERS_PER_REGIONAL_SERVER)

    # Which regional server each report goes to, and when that server sends (offset spread evenly over T).
    server = reports.player_id % n_servers
    offset = np.arange(n_servers) * T / n_servers

    # Reports may wait in the regional server's queue before it processes them.
    queue_delay, regional_peak = _regional_queue(reports.action_time, server, n_servers)
    processed_time = reports.action_time + queue_delay

    # The report waits for its server's next send: slot m is the send at offset + m*T.
    slot = np.ceil((processed_time - offset[server]) / T).astype(np.int64)
    send_time = offset[server] + slot * T
    report_delivery_time = send_time + config.REGIONAL_FORWARD_SECONDS

    # One message per (server, slot) that had at least one report.
    slots_per_server = int(slot.max()) + 2
    keys, counts = np.unique(server.astype(np.int64) * slots_per_server + slot, return_counts=True)
    msg_time = offset[keys // slots_per_server] + (keys % slots_per_server) * T + config.REGIONAL_FORWARD_SECONDS

    # Each message carries one summed batch for that server and interval.
    msg_bytes = np.full(len(keys), config.MSG_OVERHEAD_BYTES + config.BATCH_PAYLOAD_BYTES, dtype=np.int32)

    return Delivery(msg_time, counts.astype(np.int32), msg_bytes, report_delivery_time,
                    regional_servers=n_servers,
                    regional_msgs=reports.count,
                    regional_peak_msgs_per_s=regional_peak,
                    regional_max_queue_delay_s=float(queue_delay.max()),
                    regional_mean_queue_delay_s=float(queue_delay.mean()))