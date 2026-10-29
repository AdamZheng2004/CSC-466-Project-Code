"""
Simulation Parameters
"""

from dataclasses import dataclass

# Event times measured in seconds since the daily reset (t = 0 is the reset at 12UTC).
SECONDS_PER_DAY = 86_400
PLAYER_COUNTS = [10_000, 100_000, 1_000_000]

# Message Arrival Behavior:
# TT2 has a global player base spread across time zones, so normal play is modeled as constant over the day.
# The only peak is a spike right after the daily reset (players rushing to use refreshed attacks).
# Spiked sessions start at reset + a random delay with this average.
SPIKE_MEAN_DELAY_SECONDS = 20 * 60

# Sessions:
# All of a session's reports fall within this 20min window per player per session.
SESSION_WINDOW_SECONDS = 20 * 60

# Message Parameters:
# Overhead (HTTP/TLS framing, auth) is once per message, so sending fewer messages saves more bandwidth than sending smaller ones.
MSG_OVERHEAD_BYTES = 200
REPORT_PAYLOAD_BYTES = 40           # one report
BATCH_PAYLOAD_BYTES = 48            # one summed batch (value + count)


@dataclass(frozen=True)
class EventConfig:
    """
    Everything that differs between events.
    The simulation code is the same for all three, should just receive different EventConfig.
    """
    name: str
    reports_min: int                # reports per player per DAY (all sessions combined), uniform in [min, max]
    reports_max: int
    sessions_per_player: int
    spike_fraction: float           # share of session starts that fall in the reset spike

    # For hardcore players who play one longer session and make extra reports in it (For Prestige Race only).
    grinder_fraction: float = 0.0   # share of players who are grinders
    grinder_extra_min: int = 0      # extra reports per grinder
    grinder_extra_max: int = 0
    grinder_session_seconds: int = 0  # length of the grinder's long session


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
    # reports_min/max are per DAY, so 15-25 (mean 20), not per session.
    # Maybe 10% of players are grinders: they play one session of 30-40min (35min used) and pick up 5-10 extra points in it.
    "prestige": EventConfig("Prestige Races", 15, 25, 4, spike_fraction=0.0,
                            grinder_fraction=0.10, grinder_extra_min=5, grinder_extra_max=10,
                            grinder_session_seconds=35 * 60),
}
