"""
Spawns several bot.py processes locally, each with its own name/sandbox,
so you don't have to open N terminals by hand.

Usage:
    python spawn_bots.py bot1 bot2 bot3
    python spawn_bots.py --count 3        (auto-names bot1..bot3)

Run controller_gui.py (or controller_cli.py) FIRST, then run this.
Close the window / press Ctrl+C here to stop all spawned bots.
"""

import argparse
import subprocess
import sys
import time

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", help="explicit bot names")
    parser.add_argument("--count", type=int, default=0, help="spawn N auto-named bots")
    args = parser.parse_args()

    names = list(args.names)
    if args.count:
        names += [f"bot{i+1}" for i in range(args.count)]
    if not names:
        names = ["bot1", "bot2", "bot3"]

    procs = []
    for n in names:
        p = subprocess.Popen([sys.executable, "bot.py", "--name", n])
        procs.append(p)
        time.sleep(0.3)  # stagger connections a bit

    print(f"Spawned {len(procs)} bot(s): {', '.join(names)}")
    print("Press Ctrl+C to stop all of them.")
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\nStopping all bots...")
        for p in procs:
            p.terminate()
