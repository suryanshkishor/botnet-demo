"""
Botnet Simulation - Bot (client) script
----------------------------------------
EDUCATIONAL / SANDBOXED DEMO ONLY.

Safety design (read this before you modify anything):
Every single file operation this bot performs is validated against
SANDBOX_DIR, a folder the bot creates for *itself* on startup
(./demo_target_<name>). Before any create/read/delete, the resolved
absolute path is checked with os.path.commonpath([...]) to confirm it
is still inside SANDBOX_DIR. If a command ever tries to point outside
that folder, the bot refuses and reports an error back to the
controller instead of performing the action.

This means: no matter what command a controller sends, this bot
physically cannot touch any file on your machine outside its own
demo folder. That containment is the entire point of the exercise -
it's what makes this a safe demonstration of botnet C&C mechanics
instead of an actual malicious tool.
"""

import socket
import argparse
import threading
import time
import os
import shutil

HOST = "127.0.0.1"
PORT = 9000


class SandboxViolation(Exception):
    pass


def make_sandbox_dir(name):
    cwd = os.getcwd()
    sandbox = os.path.join(cwd, f"demo_target_{name}")
    os.makedirs(sandbox, exist_ok=True)
    # seed with a couple of harmless demo files
    for i in range(1, 3):
        p = os.path.join(sandbox, f"dummy_file_{i}.txt")
        if not os.path.exists(p):
            with open(p, "w") as f:
                f.write(f"This is a harmless demo file {i} for {name}\n")
    return sandbox


def safe_resolve(sandbox_dir, relative_path):
    """
    Resolve relative_path against sandbox_dir and guarantee the result
    is still inside sandbox_dir. Raises SandboxViolation otherwise.
    This is the ONLY function allowed to produce a path that gets
    passed to open()/os.remove()/shutil.rmtree().
    """
    sandbox_abs = os.path.abspath(sandbox_dir)
    candidate = os.path.abspath(os.path.join(sandbox_abs, relative_path))
    try:
        common = os.path.commonpath([sandbox_abs, candidate])
    except ValueError:
        # happens on Windows if paths are on different drives
        raise SandboxViolation(f"Path '{relative_path}' is outside the sandbox")
    if common != sandbox_abs:
        raise SandboxViolation(f"Path '{relative_path}' is outside the sandbox")
    return candidate


def send(sock, msg):
    try:
        sock.sendall((msg + "\n").encode())
    except Exception:
        pass


def cmd_create_file(sock, name, sandbox, arg):
    try:
        path = safe_resolve(sandbox, arg)
        if os.path.isdir(path):
            send(sock, f"{name} ERROR create_file: '{arg}' is a directory")
            return
        with open(path, "a"):
            os.utime(path, None)
        send(sock, f"{name} CREATED_FILE {arg}")
    except SandboxViolation as e:
        send(sock, f"{name} BLOCKED: {e}")


def cmd_create_folder(sock, name, sandbox, arg):
    try:
        path = safe_resolve(sandbox, arg)
        os.makedirs(path, exist_ok=True)
        send(sock, f"{name} CREATED_FOLDER {arg}")
    except SandboxViolation as e:
        send(sock, f"{name} BLOCKED: {e}")


def cmd_list(sock, name, sandbox, arg):
    try:
        target = safe_resolve(sandbox, arg) if arg else sandbox
        if not os.path.isdir(target):
            send(sock, f"{name} ERROR list: '{arg}' is not a folder")
            return
        entries = os.listdir(target)
        if not entries:
            send(sock, f"{name} LIST {arg or '.'} -> (empty)")
        else:
            send(sock, f"{name} LIST {arg or '.'} -> {', '.join(entries)}")
    except SandboxViolation as e:
        send(sock, f"{name} BLOCKED: {e}")


def cmd_read(sock, name, sandbox, arg):
    try:
        path = safe_resolve(sandbox, arg)
        if not os.path.isfile(path):
            send(sock, f"{name} ERROR read: '{arg}' is not a file")
            return
        with open(path, "r", errors="replace") as f:
            content = f.read(2000)  # cap what we send back
        send(sock, f"{name} CONTENT {arg} -> {content!r}")
    except SandboxViolation as e:
        send(sock, f"{name} BLOCKED: {e}")


def cmd_delete_file(sock, name, sandbox, arg):
    try:
        path = safe_resolve(sandbox, arg)
        if not os.path.isfile(path):
            send(sock, f"{name} ERROR delete_file: '{arg}' is not a file")
            return
        os.remove(path)
        send(sock, f"{name} DELETED_FILE {arg}")
    except SandboxViolation as e:
        send(sock, f"{name} BLOCKED: {e}")


def cmd_delete_folder(sock, name, sandbox, arg):
    try:
        path = safe_resolve(sandbox, arg)
        if path == os.path.abspath(sandbox):
            send(sock, f"{name} ERROR delete_folder: use DESTROY to wipe the whole sandbox")
            return
        if not os.path.isdir(path):
            send(sock, f"{name} ERROR delete_folder: '{arg}' is not a folder")
            return
        shutil.rmtree(path)
        send(sock, f"{name} DELETED_FOLDER {arg}")
    except SandboxViolation as e:
        send(sock, f"{name} BLOCKED: {e}")


def simulate_destroy(sock, name, sandbox):
    """Wipes the bot's OWN sandbox folder only. Nothing outside it is touched."""
    sandbox_abs = os.path.abspath(sandbox)
    cwd_abs = os.path.abspath(os.getcwd())
    if not sandbox_abs.startswith(cwd_abs) or not os.path.basename(sandbox_abs).startswith("demo_target_"):
        send(sock, f"{name} ABORT: unsafe sandbox path: {sandbox_abs}")
        return

    steps = [
        "STEP 1: Overwriting metadata...",
        "STEP 2: Removing file entries...",
        "STEP 3: Zeroing placeholders...",
        "FINALIZING: Cleaning demo folder...",
    ]
    for s in steps:
        print(f"[{name}] {s}")
        send(sock, f"{name} {s}")
        time.sleep(0.4)

    try:
        log_path = os.path.join(sandbox, "DESTROYED.log")
        with open(log_path, "w") as lf:
            lf.write(f"This folder was SIMULATED_DESTROYED by controller command at {time.ctime()}\n")
        send(sock, f"{name} wrote DESTROYED.log")
    except Exception as e:
        send(sock, f"{name} failed to write DESTROYED.log: {e}")

    try:
        shutil.rmtree(sandbox)
        print(f"[{name}] demo folder removed: {sandbox}")
        send(sock, f"{name} demo folder removed")
    except Exception as e:
        send(sock, f"{name} failed to remove demo folder: {e}")

    send(sock, f"STATUS {name} DESTROY_COMPLETE")


def listen_for_commands(sock, name, sandbox):
    with sock:
        while True:
            try:
                data = sock.recv(4096).decode()
            except Exception:
                break
            if not data:
                print(f"[{name}] disconnected from controller")
                break
            line = data.strip()
            if not line:
                continue
            print(f"[{name}] received command: {line}")

            parts = line.split(" ", 1)
            cmd = parts[0].upper()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "PING":
                send(sock, f"STATUS {name} OK")
            elif cmd == "TIME":
                send(sock, f"{name} TIME {time.ctime()}")
            elif cmd == "ECHO":
                send(sock, f"{name} ECHO -> {arg}")
            elif cmd == "CREATE_FILE":
                cmd_create_file(sock, name, sandbox, arg)
            elif cmd == "CREATE_FOLDER":
                cmd_create_folder(sock, name, sandbox, arg)
            elif cmd == "LIST":
                cmd_list(sock, name, sandbox, arg)
            elif cmd == "READ":
                cmd_read(sock, name, sandbox, arg)
            elif cmd == "DELETE_FILE":
                cmd_delete_file(sock, name, sandbox, arg)
            elif cmd == "DELETE_FOLDER":
                cmd_delete_folder(sock, name, sandbox, arg)
            elif cmd == "DESTROY":
                simulate_destroy(sock, name, sandbox)
                break
            elif cmd == "SHUTDOWN":
                print(f"[{name}] shutting down (local demo only)")
                break
            else:
                send(sock, f"{name} UNKNOWN_COMMAND {cmd}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="bot", help="bot name")
    args = parser.parse_args()
    name = args.name

    sandbox = make_sandbox_dir(name)
    print(f"[{name}] sandbox ready at: {sandbox}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    sock.sendall((name + "\n").encode())

    try:
        listen_for_commands(sock, name, sandbox)
    finally:
        try:
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
