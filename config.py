"""
Simulation Parameters.
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
# My best guess is that a report's payload is 40 bytes (player id, session id, action time, action type, action value), add 8 for the batched to track count.
MSG_OVERHEAD_BYTES = 200
REPORT_PAYLOAD_BYTES = 40
BATCH_PAYLOAD_BYTES = 48

# For method3, the regional server flushes its reports to the central server every 5 seconds.
PLAYERS_PER_REGIONAL_SERVER = 20_000
FLUSH_INTERVAL_SECONDS = 5

# Seeds:
# Every (event, player count, method) is run once per seed, then averaged.
SEEDS = [42, 43, 44, 45, 46]

# Method 2 data loss:
# A device's batch only exists in memory until the session ends, so if the app dies first, the WHOLE session's reports are lost.
# A session is lost if the player closes/swipes away the app before it sends, or if the game crashes mid-session.
# Both numbers are my guesses (no real data), so they are worth varying in a sensitivity check.
APP_CLOSED_BEFORE_SEND_PROB = 0.03   # per session
CRASH_PROB = 0.01                    # per session

# Method 3 regional server costs:
# Each regional server has to process one incoming message per report, so the work moves to the regional tier instead of disappearing.
# REGIONAL_SERVICE_RATE is how many incoming messages/s one regional server can process (a guess).
# If arrivals exceed it, a backlog builds and reports wait in a queue before being aggregated.
REGIONAL_SERVICE_RATE = 1_000
# The extra network leg (regional -> central) that Methods 1 and 2 don't have.
# The device -> regional leg is assumed to cost the same as device -> central, which is ignored for all methods.
REGIONAL_FORWARD_SECONDS = 0.05

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
    "raids": EventConfig("Global Raids", 3, 3, 1, spike_fraction=0.25),

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