# CSC-466-Project-Code
Code repository for my CSC 466 Networking Class. Simulating different types of traffic aggregation methods with Tap Titans 2 Global Events to see which aggregation methods work best for each particular event at different player amounts.

Please run main.py (takes roughly 2 minutes). It runs every event x player count x method once per seed in config.SEEDS and saves:
- results.csv: one row per individual run (includes a seed column)
- results_summary.csv: the average over seeds for each scenario (metric columns hold the mean, `_std` columns hold the seed-to-seed standard deviation)

Modelling assumptions worth knowing (all tunable in config.py):
- Method 2 loses a whole session's batch if the app is closed before sending or the game crashes (APP_CLOSED_BEFORE_SEND_PROB, CRASH_PROB).
- Method 3 tracks the regional tier's own load (messages/s per regional server, queueing delay if it is overloaded, REGIONAL_SERVICE_RATE) and the extra regional -> central network leg (REGIONAL_FORWARD_SECONDS). `system_total_messages` adds the regional tier's messages to the central server's so Method 3's savings are not counted as free.

Code was written with the assistence of Claude and GitHub Copilot.