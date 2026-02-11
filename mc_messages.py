import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import re
import socket
import json
import sys

# ---------------- CONFIG (DA FILE JSON) ----------------

CONFIG_FILE = "config_messages.json"

try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError:
    messagebox.showerror("Errore", f"File di configurazione mancante: {CONFIG_FILE}")
    sys.exit(1)
except json.JSONDecodeError as e:
    messagebox.showerror("Errore", f"Errore nel file JSON:\n{e}")
    sys.exit(1)

DB_PATH = config.get("DB_PATH", "meshcom.db")
POLL_INTERVAL = config.get("POLL_INTERVAL", 10)

SERVER_IP = config.get("SERVER_IP", "127.0.0.1")
SERVER_PORT = config.get("SERVER_PORT", 1703)
UDP_PREFIX = config.get("UDP_PREFIX", "MSG_OUT:")

# ---------------- APP ----------------

class MeshcomViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MeshCom – Messaggi v0.090126-b by IK5XMK")
        self.geometry("1100x500")

        self.last_id = 0

        self._setup_ui()
        self._setup_db()
        self.load_last_record()
        self.poll_messages()

    # ---------------- UI ----------------

    def _setup_ui(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=5, pady=5)

        tk.Label(top, text="Filtro DST (cifre o *):").pack(side="left")
        self.filter_entry = tk.Entry(top, width=10)
        self.filter_entry.pack(side="left", padx=5)

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True)

        columns = ("time", "src", "dst", "msg")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")

        self.tree.heading("time", text="TIME")
        self.tree.heading("src", text="SRC")
        self.tree.heading("dst", text="DST")
        self.tree.heading("msg", text="MSG")

        self.tree.column("time", width=160)
        self.tree.column("src", width=140)
        self.tree.column("dst", width=120)
        self.tree.column("msg", width=600)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Button-1>", self.on_tree_click)

    # ---------------- DB ----------------

    def _setup_db(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def _build_dst_filter(self):
        pattern = self.filter_entry.get().strip()

        if not re.fullmatch(r"[\d*]{0,5}", pattern):
            return "", []

        if pattern == "" or pattern == "*":
            return "", []

        return " AND dst LIKE ? ", [pattern.replace("*", "%")]

    def load_last_record(self):
        cur = self.conn.cursor()
        filter_sql, params = self._build_dst_filter()

        sql = f"""
            SELECT id, time, src, dst, msg
            FROM msg
            WHERE 1=1 {filter_sql}
            ORDER BY id DESC
            LIMIT 1
        """

        cur.execute(sql, params)
        row = cur.fetchone()
        if row:
            self.tree.insert("", 0, values=(row["time"], row["src"], row["dst"], row["msg"]))
            self.last_id = row["id"]

    def poll_messages(self):
        cur = self.conn.cursor()
        filter_sql, params = self._build_dst_filter()
        params = [self.last_id] + params

        sql = f"""
            SELECT id, time, src, dst, msg
            FROM msg
            WHERE id > ? {filter_sql}
            ORDER BY id ASC
        """

        cur.execute(sql, params)

        for row in cur.fetchall():
            self.tree.insert("", 0, values=(row["time"], row["src"], row["dst"], row["msg"]))
            self.last_id = row["id"]

        self.after(POLL_INTERVAL * 1000, self.poll_messages)

    # ---------------- CLICK DST ----------------

    def on_tree_click(self, event):
        if self.tree.identify("region", event.x, event.y) != "cell":
            return

        if self.tree.identify_column(event.x) != "#3":  # DST
            return

        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        dst = self.tree.item(row_id, "values")[2]
        self.open_send_window(dst)

    # ---------------- SEND WINDOW ----------------

    def open_send_window(self, dst):
        win = tk.Toplevel(self)
        win.title(f"Invia messaggio a {dst}")
        win.geometry("400x180")
        win.transient(self)
        win.grab_set()

        tk.Label(win, text=f"DST: {dst}").pack(pady=5)

        tk.Label(win, text="Messaggio:").pack()
        msg_entry = tk.Entry(win, width=45)
        msg_entry.pack(padx=10, pady=5)
        msg_entry.focus()

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame,
            text="Invia",
            command=lambda: self.send_message(dst, msg_entry.get(), win)
        ).pack(side="left", padx=10)

        ttk.Button(
            btn_frame,
            text="Annulla",
            command=win.destroy
        ).pack(side="left", padx=10)

    # ---------------- UDP SEND ----------------

    def send_message(self, dst, text, window):
        if not text.strip():
            messagebox.showwarning("Errore", "Il messaggio è vuoto")
            return

        command = f"{UDP_PREFIX}{{{dst}}}{text[:150]}"

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            sock.sendto(command.encode("utf-8"), (SERVER_IP, SERVER_PORT))
            sock.close()
            window.destroy()

        except Exception as e:
            messagebox.showerror("Errore invio", str(e))


# ---------------- MAIN ----------------

if __name__ == "__main__":
    app = MeshcomViewer()
    app.mainloop()
