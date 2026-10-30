"""
Workload generator:

Produces one table with a row per report. All three methods receive the same
table, so they are compared on identical player behavior.
"""

from dataclasses import dataclass

import numpy as np

import config
from config import EventConfig


@dataclass
class Reports:
    """Reports as parallel numpy arrays, sorted by time. Arrays are used
    because 1M players can produce ~20M reports."""
    player_id: np.ndarray    # 0 .. N-1
    session_id: np.ndarray   # unique per (player, session); Method 2 batches on this
    action_time: np.ndarray  # seconds since reset

    @property
    def count(self) -> int:
        return len(self.action_time)


def _sample_session_starts(rng, n, spike_fraction, latest_start):
    """Draw n session start times. A spike_fraction share start shortly after the
    reset, the rest are spread evenly over the day (up to latest_start)."""
    normal = rng.random(n) * latest_start

    spike = rng.exponential(config.SPIKE_MEAN_DELAY_SECONDS, n)
    spike = np.minimum(spike, latest_start)

    return np.where(rng.random(n) < spike_fraction, spike, normal)


def generate_reports(event: EventConfig, n_players: int, seed: int) -> Reports:
    """
    All reports for one event-day. Same (event, n_players, seed) always gives
    the same output, so runs are reproducible.
    """
    rng = np.random.default_rng(seed)
    S = event.sessions_per_player

    # Sessions can't start so late that they run past the end of the day.
    longest_session = max(config.SESSION_WINDOW_SECONDS, event.grinder_session_seconds)
    latest_start = config.SECONDS_PER_DAY - longest_session

    # How many reports each player makes today.
    reports_per_player = rng.integers(event.reports_min, event.reports_max + 1, n_players)

    # starts[p, s] is the start time of player p's session s.
    starts = _sample_session_starts(rng, n_players * S, event.spike_fraction, latest_start)
    starts = starts.reshape(n_players, S)

    # One entry per report: np.repeat writes each player's id once per report.
    # Each report goes in a random session of its player, at a random point in
    # that session's window.
    player = np.repeat(np.arange(n_players), reports_per_player)
    session = rng.integers(0, S, len(player))
    time = starts[player, session] + rng.random(len(player)) * config.SESSION_WINDOW_SECONDS

    # Grinders (Prestige): extra reports spread over one long session, picked at
    # random from the grinder's sessions.
    if event.grinder_fraction > 0:
        grinder = rng.random(n_players) < event.grinder_fraction
        n_extra = np.where(grinder, rng.integers(event.grinder_extra_min, event.grinder_extra_max + 1, n_players), 0)
        p_extra = np.repeat(np.arange(n_players), n_extra)
        long_session = rng.integers(0, S, n_players)[p_extra]
        t_extra = starts[p_extra, long_session] + rng.random(len(p_extra)) * event.grinder_session_seconds

        player = np.concatenate([player, p_extra])
        session = np.concatenate([session, long_session])
        time = np.concatenate([time, t_extra])

    # latest_start leaves room for the longest session, so nothing falls outside the day.
    assert time.max() < config.SECONDS_PER_DAY

    order = np.argsort(time, kind="stable")
    return Reports(
        player_id=player[order].astype(np.int32),
        session_id=(player * S + session)[order].astype(np.int64),  # unique across players
        action_time=time[order],
    )
