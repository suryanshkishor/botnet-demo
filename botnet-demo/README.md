⚠️️ Disclaimer: This project is a Command and Control (C2) simulation developed strictly for educational purposes and academic research. It features hardcoded ethical sandboxing to prevent interaction with real host operating systems. Do not use this code maliciously or on unauthorized networks.
# Botnet Simulation (Sandboxed Educational Demo)

This is a safe, self-contained simulation of botnet command-and-control (C&C)
mechanics, built to accompany the case study report "Botnet" (CV Raman Global
University, CSE Dept).

**Safety design — read this first**

Every "bot" creates its own folder, `demo_target_<name>`, the moment it
starts. Every file operation the bot can be told to perform (create, list,
read, delete, "destroy") is checked with `os.path.commonpath()` against that
one folder before it runs. If a command would touch anything outside that
folder, the bot refuses and reports an error back to the controller instead.
There is no command that accepts an arbitrary absolute path, and there is no
"lock arbitrary file" feature — that's intentionally left out, because
remote file-locking is literally how ransomware works, and nothing in this
project can function like that.

In short: **this cannot touch, lock, or delete anything on your laptop
outside the demo_target_<name> folders it creates itself.** You can safely
run multiple bots and send them destructive commands — the worst case is
those sandbox folders get deleted, same as deleting any other test folder.

## Files

| File | Purpose |
|---|---|
| `bot.py` | The bot (client). Connects to controller, creates its sandbox, listens for commands. |
| `controller_gui.py` | Tkinter GUI C&C server — the one that looks like the screenshot in the report. |
| `controller_cli.py` | Console-only version of the same controller, if you prefer a terminal. |
| `spawn_bots.py` | Launches several `bot.py` processes at once so you don't need N terminals. |

## Requirements

- Python 3.8+ (Tkinter ships with the standard Windows installer — no extra install needed)
- No third-party packages required (everything used is in the standard library)

## How to run (VS Code, Windows)

1. Unzip this project and open the folder in VS Code (`File > Open Folder`).
2. Open a terminal in VS Code (`` Ctrl+` ``).
3. **Start the controller first.** Either:
   ```
   python controller_gui.py
   ```
   or, for the console version:
   ```
   python controller_cli.py
   ```
   The GUI window (or console) will show `[controller] listening on 127.0.0.1:9000`.

4. **Open a second terminal** (click the `+` in VS Code's terminal panel) and start one or more bots:
   ```
   python bot.py --name bot1
   ```
   Open additional terminals for more bots (`--name bot2`, `--name bot3`, ...),
   or use the helper to launch several at once:
   ```
   python spawn_bots.py bot1 bot2 bot3
   ```
   Each bot will print the path to its own `demo_target_<name>` sandbox folder.

5. Back in the controller, click **Refresh** to see connected bots in the
   "Connected Bots" list, select one, and either type a raw command or use
   the button grid.

## Command reference

Type these into the "Raw command" box (GUI) or after `send <bot>` (CLI):

| Command | Effect |
|---|---|
| `PING` | Bot replies `STATUS <name> OK` |
| `TIME` | Bot replies with its local time |
| `ECHO <text>` | Bot echoes the text back |
| `CREATE_FILE <name>` | Creates an empty file inside the bot's sandbox |
| `CREATE_FOLDER <name>` | Creates a subfolder inside the sandbox |
| `LIST [subfolder]` | Lists contents of the sandbox (or a subfolder of it) |
| `READ <name>` | Reads back the contents of a file in the sandbox (first 2000 chars) |
| `DELETE_FILE <name>` | Deletes one file inside the sandbox |
| `DELETE_FOLDER <name>` | Deletes one subfolder inside the sandbox (not the sandbox root itself) |
| `DESTROY` | Simulates a destructive payload: logs the "attack", then deletes the bot's entire sandbox folder and disconnects |
| `SHUTDOWN` | Bot disconnects without destroying anything |
| Creating a New File | CREATE warning.txt Your system has been compromised. |
| Changing / Modifying that File | CREATE warning.txt Pay 100 Bitcoin to unlock your files.|
| APPEND command| APPEND warning.txt User opened the bank app.|

In the GUI, **Broadcast** sends whatever is in the raw command box to every
connected bot at once — this is what demonstrates the "one controller, many
bots" nature of a real botnet for your report/demo.

## Suggested demo flow for your report/presentation

1. Start controller, spawn 2–3 bots → show the "Connected Bots" list populating (this is the rallying/connection phase from your report's lifecycle diagram).
2. `PING` each bot individually → show C&C round-trip.
3. `CREATE_FOLDER logs` then `CREATE_FILE logs/entry1.txt` on one bot → show file-system commands being issued remotely.
4. `LIST` and `READ` to show the controller can retrieve state/data from a bot (mirrors the "data theft" attack type from your report, safely).
5. `Broadcast PING` → show one command reaching every bot simultaneously (mirrors a coordinated DDoS-style broadcast, safely).
6. `DESTROY` on one bot → show the staged "attack" messages, the DESTROYED.log it writes, and the sandbox folder disappearing — then point out in your presentation that this is confined entirely to a folder the bot made for itself, which is exactly the control you'd want a real defender to have and exactly what real malware does NOT respect.

## Cleaning up

Each bot leaves a `demo_target_<name>` folder next to `bot.py` once it's
run (unless you `DESTROY`ed it). These are just ordinary folders with dummy
`.txt` files in them — delete them manually any time, like any other test
output.
