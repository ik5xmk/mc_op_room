import sqlite3
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import json
import sys
import os
import subprocess
from datetime import datetime

# ---------------- CONFIG ----------------

CONFIG_FILE = "config_listener.json"

try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
except Exception as e:
    print(f"Errore config: {e}")
    sys.exit(1)

DB_PATH = config.get("DB_PATH", "meshcom.db")
POLL_INTERVAL = config.get("POLL_INTERVAL", 10)

DST_GROUP = str(config.get("DST_GROUP", ""))

AUTHORIZED_SRCS = config.get("AUTHORIZED_SRCS", [])        
AUTHORIZED_SRCS = [s.upper() for s in AUTHORIZED_SRCS]     

KEEP_ALIVE = config.get("KEEP_ALIVE_SECONDS", 60)

COMMANDS = config.get("COMMANDS", [])
CMD_CASE_INSENSITIVE = config.get("COMMAND_CASE_INSENSITIVE", False)  

IS_WINDOWS = os.name == "nt"

# ---------------- APP ----------------

class MeshComCommandListener(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("MeshCom – Command Listener v0.12012026 by IK5XMK")
        self.geometry("950x420")

        self.last_id = 0

        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

        self._setup_ui()
        self._startup_log()
        self.poll_messages()

    # ---------------- UI ----------------

    def _setup_ui(self):
        self.logbox = ScrolledText(self, state="disabled", font=("Consolas", 10))
        self.logbox.pack(fill="both", expand=True, padx=6, pady=6)

    def log(self, text):
        self.logbox.configure(state="normal")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logbox.insert("end", f"[{ts}] {text}\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def _startup_log(self):
        self.log("Listener avviato")
        self.log(f"DST_GROUP abilitato : {DST_GROUP}")
        self.log(f"SRC autorizzati     : {', '.join(AUTHORIZED_SRCS)}")
        self.log(f"Keep-alive          : {KEEP_ALIVE}s")
        self.log(f"Polling DB          : {POLL_INTERVAL}s")
        self.log(f"Command case-insens.: {CMD_CASE_INSENSITIVE}")

    # ---------------- DB POLLING ----------------

    def poll_messages(self):
        cur = self.conn.cursor()

        sql = """
            SELECT id, time, src, dst, msg
            FROM msg
            WHERE id > ?
            ORDER BY id ASC
        """

        cur.execute(sql, (self.last_id,))
        rows = cur.fetchall()

        for row in rows:
            self.last_id = row["id"]
            self.process_message(row)

        self.after(POLL_INTERVAL * 1000, self.poll_messages)

    # ---------------- MESSAGE PROCESS ----------------

    def process_message(self, row):
        dst = str(row["dst"])
        msg = row["msg"]
        msg_time = self.parse_time(row["time"])

        # 1) DST GROUP
        if dst != DST_GROUP:
            return

        # 2) SRC autorizzato (PRIMO CALLSIGN)
        src_raw = row["src"]
        src_first = src_raw.split(",")[0].strip().upper()

        if src_first not in AUTHORIZED_SRCS:
            self.log(f"Messaggio ignorato (SRC non autorizzato): {src_first}")
            return

        # 3) TIME VALIDATION
        if not msg_time:
            self.log("Formato data non valido, messaggio scartato")
            return

        age = (datetime.now() - msg_time).total_seconds()
        if age > KEEP_ALIVE:
            self.log(f"Messaggio scaduto ({int(age)}s): {msg}")
            return

        # 4) COMMAND MATCH
        for cmd in COMMANDS:
            cmd_key = cmd["command"]

            if CMD_CASE_INSENSITIVE:
                if cmd_key.upper() in msg.upper():
                    self.execute_command(cmd, msg)
                    return
            else:
                if cmd_key in msg:
                    self.execute_command(cmd, msg)
                    return

    # ---------------- COMMAND EXEC ----------------

    def execute_command(self, cmd, msg):
        script = cmd["windows"] if IS_WINDOWS else cmd["unix"]

        #if not os.path.exists(script):
        #    self.log(f"Script non trovato: {script}")
        #    return

        self.log(f"COMANDO RICEVUTO: {cmd['command']}")
        self.log(f"Esecuzione script: {script}")

        try:
            if IS_WINDOWS:
                subprocess.Popen(script, shell=True)
            else:
                subprocess.Popen(["/bin/bash", script])
        except Exception as e:
            self.log(f"Errore esecuzione: {e}")

    # ---------------- UTILS ----------------

    def parse_time(self, t):
        try:
            return datetime.strptime(t, "%d/%m/%Y %H:%M:%S")
        except Exception:
            return None

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app = MeshComCommandListener()
    app.mainloop()
