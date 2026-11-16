# CSC-466-Project-Code
Code repository for my CSC 466 Networking Class. Simulating different types of traffic aggregation methods with Tap Titans 2 Global Events to see which aggregation methods work best for each particular event at different player amounts.

## How to run
1. Install the dependencies (Python 3.9+):
   ```
   py -m pip install -r requirements.txt
   ```
   (On macOS/Linux use `python3 -m pip install -r requirements.txt`.)
2. Run the simulation:
   ```
   py main.py
   ```
   Takes roughly 2 minutes. It runs every event x player count x method once per seed in config.SEEDS and saves:
   - results.csv: one row per individual run (includes a seed column)
   - results_summary.csv: the average over seeds for each scenario (metric columns hold the mean, `_std` columns hold the seed-to-seed standard deviation)
3. Make the graphs:
   ```
   py graph.py
   ```
   Reads results_summary.csv (run main.py first) and saves PNG charts to a `graphs/` folder. This is separate from main.py so charts can be redrawn instantly without re-running the simulation.

## Files
- config.py: all simulation parameters and the three event definitions (Global Raids, Season Rankings, Prestige Races)
- workload.py: generates the stream of player reports for one day
- methods.py: the three aggregation methods (Method 1: report per action, Method 2: batch per session, Method 3: regional servers)
- metrics.py: computes central-server load, timeliness, accuracy, and regional-tier cost
- main.py: runs all scenarios and writes the CSVs
- graph.py: plots the results

## Graphs produced
- Central-server peak messages/s, total messages, and total data (MB)
- Central-server vs whole-system messages (so Method 3's savings are not counted as free)
- Mean and p95 staleness, and share of reports lost
- Method 3 regional tier peak utilization and queue delay
- Load vs timeliness trade-off at the largest player count

## Modelling assumptions worth knowing (all tunable in config.py)
- Method 2 loses a whole session's batch if the app is closed before sending or the game crashes (APP_CLOSED_BEFORE_SEND_PROB, CRASH_PROB).
- Method 3 tracks the regional tier's own load (messages/s per regional server, queueing delay if it is overloaded, REGIONAL_SERVICE_RATE) and the extra regional -> central network leg (REGIONAL_FORWARD_SECONDS). `system_total_messages` adds the regional tier's messages to the central server's so Method 3's savings are not counted as free.
- Many parameters (loss probabilities, service rate, session behaviour) are my own estimates rather than measured data.

Code was written with the assistence of Claude and GitHub Copilot.