"""
Botnet Simulation - Controller (command-line)
-----------------------------------------------
EDUCATIONAL / SANDBOXED DEMO ONLY. Same C&C server as controller_gui.py,
console interface instead of Tkinter. See bot.py for the sandboxing
that keeps every bot action confined to its own demo folder.
"""

import socket
import threading

HOST = "127.0.0.1"
PORT = 9000

clients = {}
clients_lock = threading.Lock()


def handle_client(conn, addr):
    with conn:
        name = conn.recv(1024).decode().strip()
        with clients_lock:
            clients[name] = conn
        print(f"[+] {name} connected from {addr}")
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                for line in data.decode(errors="replace").strip().splitlines():
                    print(f"[{name}] -> {line}")
        finally:
            with clients_lock:
                clients.pop(name, None)
            print(f"[-] {name} disconnected")


def accept_loop(sock):
    while True:
        conn, addr = sock.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()


HELP = """Controller interactive console. Commands:
  list                         - show connected bots
  send <bot> <cmd> [arg]       - send a command to one bot
      e.g. send bot1 PING
      e.g. send bot1 CREATE_FILE notes.txt
      e.g. send bot1 CREATE_FOLDER logs
      e.g. send bot1 LIST
      e.g. send bot1 READ notes.txt
      e.g. send bot1 DELETE_FILE notes.txt
      e.g. send bot1 DELETE_FOLDER logs
  broadcast <cmd> [arg]        - send a command to ALL bots
  destroy <bot>                - wipe that bot's own sandbox folder
  quit                         - shut down the controller
"""


def interactive():
    print(HELP)
    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nShutting down controller.")
            break
        if not cmd:
            continue
        if cmd == "list":
            with clients_lock:
                for name in clients:
                    print(" -", name)
        elif cmd == "help":
            print(HELP)
        elif cmd.startswith("send "):
            parts = cmd.split(" ", 2)
            if len(parts) < 3:
                print("usage: send <bot> <cmd> [arg]")
                continue
            target, payload = parts[1], parts[2]
            with clients_lock:
                conn = clients.get(target)
            if conn:
                try:
                    conn.sendall((payload + "\n").encode())
                except Exception as e:
                    print("send failed:", e)
            else:
                print("no such bot:", target)
        elif cmd.startswith("broadcast "):
            payload = cmd.split(" ", 1)[1]
            with clients_lock:
                targets = list(clients.items())
            for name, conn in targets:
                try:
                    conn.sendall((payload + "\n").encode())
                except Exception as e:
                    print(f"failed to send to {name}: {e}")
        elif cmd.startswith("destroy "):
            target = cmd.split(" ", 1)[1].strip()
            with clients_lock:
                conn = clients.get(target)
            if conn:
                try:
                    conn.sendall(b"DESTROY\n")
                    print(f"[controller] DESTROY sent to {target}")
                except Exception as e:
                    print("send failed:", e)
            else:
                print("no such bot:", target)
        elif cmd == "quit":
            print("Shutting down controller.")
            break
        else:
            print("unknown command, type 'help'")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(20)
    print(f"[controller] listening on {HOST}:{PORT}")

    t = threading.Thread(target=accept_loop, args=(sock,), daemon=True)
    t.start()

    interactive()
    try:
        sock.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
