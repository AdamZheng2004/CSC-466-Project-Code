"""
Simulation Parameters
"""

from dataclasses import dataclass

# Event times measured in seconds since the daily reset (t = 0 is the reset at 12UTC).
SECONDS_PER_DAY = 86_400
PLAYER_COUNTS = [10_000, 100_000, 1_000_000]

# Message Arrival Behavior:
# Session starts mixed, gentle day/night wave (normal play) with a spike right after the reset (players rushing to use refreshed attacks).
# TT2 has a global player base so it will span time zones, thus the wave is mild.
DIURNAL_PEAK_TO_TROUGH = 1.5        # busiest hour vs quietest hour.
DIURNAL_PEAK_HOUR = 12              # hours after reset to shift the wave.
SPIKE_MEAN_DELAY_SECONDS = 20 * 60

# Sessions:
# All of a session's reports fall within this 20min window per player per session.
SESSION_WINDOW_SECONDS = 20 * 60

# Message Parameters:
# Overhead (HTTP/TLS framing, auth) is once per message, so sending fewer messages saves more bandwidth than sending smaller ones.
MSG_OVERHEAD_BYTES = 200
REPORT_PAYLOAD_BYTES = 40 
BATCH_PAYLOAD_BYTES = 48            # summed batch (value + count).


@dataclass(frozen=True)
class EventConfig:
    """
    Things that can differ between events. 
    The simulation code should be able to handle all three EventConfigs.
    """
    name: str
    reports_min: int                # reports per player per day (all sessions combined), uniform in [min, max].
    reports_max: int
    sessions_per_player: int
    spike_fraction: float           # share of session starts that fall in the reset spike.

    # For hardcore players who make extra reports packed into one short window (For Prestige Race only).
    burst_fraction: float = 0.0     # share of players who are hardcore/grinders.
    burst_min: int = 0              # extra reports per grinder.
    burst_max: int = 0
    burst_window_seconds: int = 60


EVENTS = {
    # Global Raids:
    # 3 attacks/day, done in one sitting. Global reset refreshes attacks for everyone. Assuming 25% of players rush in right after it.
    "raids": EventConfig("Global Raids (Phase 3)", 3, 3, 1, spike_fraction=0.25),

    # Season Rankings:
    # 15-20 point sources per day (each report is one source, worth ~5-10 points). Count varies in game with other active events.
    # Assuming 2 sessions/day.
    "season": EventConfig("Season Rankings", 15, 20, 2, spike_fraction=0.0),

    # Prestige Races:
    # Around 5 points/session and around 4 sessions a day when this event is live, so about 20 points/day total.
    # Maybe 10% of players burst 5-10 extra points.
    "prestige": EventConfig("Prestige Races", 15, 25, 4, spike_fraction=0.0,
                            burst_fraction=0.10, burst_min=5, burst_max=10),
}