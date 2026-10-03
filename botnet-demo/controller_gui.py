"""
Botnet Simulation - Controller (GUI)
--------------------------------------
EDUCATIONAL / SANDBOXED DEMO ONLY. See bot.py for the safety design -
this controller can only ever send commands; it has no way to reach
outside a connected bot's own sandbox folder, because the bot itself
enforces that boundary.

Run this FIRST, then run bot.py in one or more separate terminals.
"""

import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import queue
import time

HOST = "127.0.0.1"
PORT = 9000

clients = {}
clients_lock = threading.Lock()
msg_queue = queue.Queue()


def accept_loop(server_sock, stop_event):
    server_sock.listen(20)
    while not stop_event.is_set():
        try:
            server_sock.settimeout(1.0)
            conn, addr = server_sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()


def handle_client(conn, addr):
    with conn:
        try:
            name = conn.recv(1024).decode().strip()
        except Exception:
            return
        if not name:
            return
        with clients_lock:
            clients[name] = conn
        msg_queue.put((name, f"[connected] {addr}"))

        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                text = data.decode(errors="replace").strip()
                if text:
                    for line in text.splitlines():
                        msg_queue.put((name, line))
        except Exception:
            pass
        finally:
            with clients_lock:
                clients.pop(name, None)
            msg_queue.put((name, "[disconnected]"))


class ControllerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Botnet Demo - Controller (GUI)")
        self.geometry("1000x600")
        self.minsize(820, 480)

        self._build_ui()

        self.server_sock = None
        self.server_thread = None
        self.server_stop = threading.Event()

        self.after(150, self._poll_messages)
        self._start_server()

    # ---------- UI ----------
    def _build_ui(self):
        main = ttk.Frame(self, padding=(8, 8, 8, 8))
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8), pady=4)

        ttk.Label(left, text="Connected Bots", font=(None, 11, "bold")).pack(anchor=tk.W)
        self.bot_list = tk.Listbox(left, height=24, width=26)
        self.bot_list.pack(pady=(6, 6), fill=tk.Y, expand=False)

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_bots).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Show Sandbox Path", command=self.show_sandbox_path).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(right, text="Controller Log", font=(None, 11, "bold")).pack(anchor=tk.W)
        self.log = scrolledtext.ScrolledText(right, width=90, height=24, state="disabled")
        self.log.pack(pady=(6, 8), fill=tk.BOTH, expand=True)

        # quick command row (raw command, sent to selected bot)
        cmd_row = ttk.Frame(right)
        cmd_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(cmd_row, text="Raw command:").pack(side=tk.LEFT, padx=(0, 6))
        self.cmd_entry = ttk.Entry(cmd_row)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(cmd_row, text="Send to Selected", command=self.send_to_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(cmd_row, text="Broadcast", command=self.broadcast_cmd).pack(side=tk.LEFT, padx=2)

        # helper button grid for the sandboxed file commands
        grid = ttk.LabelFrame(right, text="Sandbox file commands (selected bot)")
        grid.pack(fill=tk.X, pady=(6, 6))

        def row(parent):
            r = ttk.Frame(parent)
            r.pack(fill=tk.X, pady=2)
            return r

        r1 = row(grid)
        ttk.Button(r1, text="Create File", command=lambda: self._prompt_and_send("CREATE_FILE", "Filename (e.g. notes.txt)")).pack(side=tk.LEFT, padx=3)
        ttk.Button(r1, text="Create Folder", command=lambda: self._prompt_and_send("CREATE_FOLDER", "Folder name")).pack(side=tk.LEFT, padx=3)
        ttk.Button(r1, text="List Contents", command=lambda: self._prompt_and_send("LIST", "Subfolder (blank = root)", allow_blank=True)).pack(side=tk.LEFT, padx=3)
        ttk.Button(r1, text="Read File", command=lambda: self._prompt_and_send("READ", "Filename to read")).pack(side=tk.LEFT, padx=3)

        r2 = row(grid)
        ttk.Button(r2, text="Delete File", command=lambda: self._prompt_and_send("DELETE_FILE", "Filename to delete")).pack(side=tk.LEFT, padx=3)
        ttk.Button(r2, text="Delete Folder", command=lambda: self._prompt_and_send("DELETE_FOLDER", "Folder to delete")).pack(side=tk.LEFT, padx=3)
        ttk.Button(r2, text="DESTROY Sandbox", command=self.destroy_selected).pack(side=tk.LEFT, padx=3)

        bottom = ttk.Frame(main)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(bottom, text="Quit", command=self._on_quit).pack(side=tk.RIGHT, padx=6, pady=6)

    # ---------- server ----------
    def _start_server(self):
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((HOST, PORT))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to bind server socket on {HOST}:{PORT}: {e}")
            return

        self.server_stop.clear()
        self.server_thread = threading.Thread(target=accept_loop, args=(self.server_sock, self.server_stop), daemon=True)
        self.server_thread.start()
        self.log_write(f"[controller] listening on {HOST}:{PORT}")

    # ---------- bot list ----------
    def refresh_bots(self):
        with clients_lock:
            names = sorted(clients.keys())
        sel = None
        try:
            sel = self.bot_list.get(self.bot_list.curselection())
        except Exception:
            sel = None
        self.bot_list.delete(0, tk.END)
        for n in names:
            self.bot_list.insert(tk.END, n)
        if sel:
            try:
                idx = names.index(sel)
                self.bot_list.selection_set(idx)
                self.bot_list.see(idx)
            except ValueError:
                pass

    def _selected_name(self):
        sel = self.bot_list.curselection()
        if not sel:
            messagebox.showinfo("No bot selected", "Select a bot from the list.")
            return None
        return self.bot_list.get(sel[0])

    # ---------- commands ----------
    def send_to_selected(self):
        name = self._selected_name()
        if not name:
            return
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            messagebox.showinfo("No command", "Type a command first.")
            return
        self._send_to_bot(name, cmd)

    def broadcast_cmd(self):
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            messagebox.showinfo("No command", "Type a command to broadcast.")
            return
        with clients_lock:
            names = list(clients.keys())
        for name in names:
            self._send_to_bot(name, cmd)
        self.log_write(f"[controller] broadcast: {cmd}")

    def _prompt_and_send(self, base_cmd, prompt, allow_blank=False):
        name = self._selected_name()
        if not name:
            return
        val = simpledialog.askstring("Input", prompt, parent=self)
        if val is None:
            return
        val = val.strip()
        if not val and not allow_blank:
            return
        full = f"{base_cmd} {val}".strip()
        self._send_to_bot(name, full)

    def destroy_selected(self):
        name = self._selected_name()
        if not name:
            return
        if messagebox.askyesno(
            "Confirm",
            f"Send DESTROY to {name}? This wipes ONLY that bot's own\n"
            f"'demo_target_{name}' sandbox folder - nothing else on disk.",
        ):
            self._send_to_bot(name, "DESTROY")
            self.log_write(f"[controller] DESTROY sent to {name}")

    def show_sandbox_path(self):
        name = self._selected_name()
        if not name:
            return
        messagebox.showinfo(
            "Sandbox folder",
            f"demo_target_{name}\n(created next to bot.py, in the folder bot.py was launched from)",
        )

    def _send_to_bot(self, name, payload):
        with clients_lock:
            conn = clients.get(name)
        if not conn:
            messagebox.showerror("Error", f"Bot {name} not connected")
            self.refresh_bots()
            return
        try:
            conn.sendall((payload + "\n").encode())
            self.log_write(f"[to {name}] {payload}")
        except Exception as e:
            self.log_write(f"[error] failed to send to {name}: {e}")

    # ---------- log / polling ----------
    def log_write(self, text):
        self.log.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{ts}] {text}\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _poll_messages(self):
        while True:
            try:
                name, text = msg_queue.get_nowait()
            except queue.Empty:
                break
            if text.startswith("[connected]") or text == "[disconnected]":
                self.refresh_bots()
            self.log_write(f"[{name}] {text}")
        self.after(150, self._poll_messages)

    def _on_quit(self):
        if messagebox.askyesno("Quit", "Stop server and quit?"):
            try:
                self.server_stop.set()
                if self.server_sock:
                    try:
                        self.server_sock.close()
                    except Exception:
                        pass
            except Exception:
                pass
            self.destroy()


if __name__ == "__main__":
    app = ControllerGUI()
    app.mainloop()
