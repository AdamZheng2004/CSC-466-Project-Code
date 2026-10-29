"""
Workload generator:

Produces one table with a row per report. 
All three methods receive the same table, so they are compared on identical player behavior.
"""

from dataclasses import dataclass
import numpy as np
import config
from config import EventConfig


@dataclass
class Reports:
    """
    Reports as parallel numpy arrays, sorted by time. 
    Using arrays to handle the potential 20M reports in some scenarios.
    """
    player_id: np.ndarray    # 0 .. N-1.
    session_id: np.ndarray   # unique per (player, session). Method 2 with batch on this.
    action_time: np.ndarray  # seconds since reset.

    @property
    def count(self) -> int:
        return len(self.action_time)


def _build_diurnal_cdf() -> np.ndarray:
    """
    Lookup table for drawing normal play session start times.

    Start probability follows a cosine wave over the day, highest at the peak hour. 
    The amplitude a is chosen so busiest/quietest = DIURNAL_PEAK_TO_TROUGH, since (1 + a) / (1 - a) = ratio. 
    The result is a cumulative distribution (CDF) so we can sample from it with a uniform random number.
    """
    ratio = config.DIURNAL_PEAK_TO_TROUGH
    a = (ratio - 1.0) / (ratio + 1.0)

    # Starts stop one session window before midnight. 
    latest_start = config.SECONDS_PER_DAY - config.SESSION_WINDOW_SECONDS
    t = np.arange(latest_start)
    peak = config.DIURNAL_PEAK_HOUR * 3600
    density = 1.0 + a * np.cos(2.0 * np.pi * (t - peak) / config.SECONDS_PER_DAY)

    cdf = np.cumsum(density)
    return cdf / cdf[-1]


_DIURNAL_CDF = _build_diurnal_cdf()


def _sample_session_starts(rng, n, spike_fraction):
    """
    Draw n session start times: a spike_fraction share right after the reset,
    the rest from the day/night wave.
    """
    # Inverse-transform sampling (Learned in 446): 
    # where a uniform number lands in the CDF is the start second (busy hours cover more of the CDF, so they get picked more).
    normal = np.searchsorted(_DIURNAL_CDF, rng.random(n)) + rng.random(n)

    spike = rng.exponential(config.SPIKE_MEAN_DELAY_SECONDS, n)
    spike = np.minimum(spike, config.SECONDS_PER_DAY - config.SESSION_WINDOW_SECONDS)

    return np.where(rng.random(n) < spike_fraction, spike, normal)


def generate_reports(event: EventConfig, n_players: int, seed: int) -> Reports:
    """
    All reports for one event-day. 
    Same (event, n_players, seed) always gives the same output, so runs are reproducible and fair for the 3 methods.
    """
    rng = np.random.default_rng(seed)
    S = event.sessions_per_player

    # How many reports each player makes today.
    reports_per_player = rng.integers(event.reports_min, event.reports_max + 1, n_players)

    # starts[p, s] is the start time of player p's session s.
    starts = _sample_session_starts(rng, n_players * S, event.spike_fraction)
    starts = starts.reshape(n_players, S)

    # One entry per report: 
    # np.repeat writes each player's id once per report.
    # Each report goes in a random session of its player, at a random point in that session's window.
    player = np.repeat(np.arange(n_players), reports_per_player)
    session = rng.integers(0, S, len(player))
    time = starts[player, session] + rng.random(len(player)) * config.SESSION_WINDOW_SECONDS

    # Grinder/Harcore Players bursts (Prestige): 
    # Extra reports packed into a short window right after one randomly chosen session start of each grinder.
    if event.burst_fraction > 0:
        grinder = rng.random(n_players) < event.burst_fraction
        n_extra = np.where(grinder, rng.integers(event.burst_min, event.burst_max + 1, n_players), 0)
        p_extra = np.repeat(np.arange(n_players), n_extra)
        burst_session = rng.integers(0, S, n_players)[p_extra]
        t_extra = starts[p_extra, burst_session] + rng.random(len(p_extra)) * event.burst_window_seconds

        player = np.concatenate([player, p_extra])
        session = np.concatenate([session, burst_session])
        time = np.concatenate([time, t_extra])

    # Starts stop one window early, so nothing should fall outside the day.
    assert time.max() < config.SECONDS_PER_DAY

    order = np.argsort(time, kind="stable")
    return Reports(
        player_id=player[order].astype(np.int32),
        session_id=(player * S + session)[order].astype(np.int64),  # unique across players
        action_time=time[order],
    )
