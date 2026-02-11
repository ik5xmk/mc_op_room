import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import math
import json
import sys

# ---------------- CONFIG (DA FILE JSON) ----------------

CONFIG_FILE = "config_nodes.json"

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
MY_CALLSIGN = config.get("MY_CALLSIGN", "IK5XMK-98")
SHOW_ONLY_TODAY = config.get("SHOW_ONLY_TODAY", True)

# ---------------- UTILS ----------------

def to_float(v):
    try:
        return float(v)
    except:
        return None


def dms_to_decimal(value, direction):
    v = to_float(value)
    if v is None:
        return None
    if direction in ("S", "W"):
        v = -v
    return v


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------- DATABASE ----------------

def get_position_by_callsign(callsign):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT lat, lat_dir, long, long_dir
        FROM pos
        WHERE src LIKE ?
        ORDER BY id DESC
        LIMIT 1
    """, (f"{callsign}%",))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    lat = dms_to_decimal(row["lat"], row["lat_dir"])
    lon = dms_to_decimal(row["long"], row["long_dir"])

    if lat is None or lon is None:
        return None

    return lat, lon


def get_latest_positions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    today = datetime.now().strftime("%d/%m/%Y")

    query = """
        SELECT *
        FROM pos
        WHERE id IN (
            SELECT MAX(id)
            FROM pos
            GROUP BY src
        )
    """

    if SHOW_ONLY_TODAY:
        query += " AND time LIKE ?"
        cur.execute(query, (f"{today}%",))
    else:
        cur.execute(query)

    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------- GUI ----------------

class App:

    def __init__(self, root):
        self.root = root
        self.root.title("MeshCom - Posizioni v0.090126-b by IK5XMK")

        self.ref_callsign = None
        self.ref_position = None

        frame = ttk.Frame(root)
        frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            frame,
            columns=("cs", "lat", "lon", "time", "dist"),
            show="headings",
            selectmode="browse"
        )

        for c, t, w in [
            ("cs", "Callsign", 150),
            ("lat", "Lat", 90),
            ("lon", "Lon", 90),
            ("time", "Time", 160),
            ("dist", "Km", 80),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("me", background="#d6f5d6")
        self.tree.tag_configure("ref", background="#ffe0b3")
        self.tree.tag_configure("normal", background="white")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.items = {}

        self.poll()

    # ---------------- EVENT ----------------

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return

        item = sel[0]
        callsign = self.tree.item(item, "values")[0]

        pos = get_position_by_callsign(callsign)
        if pos:
            self.ref_callsign = callsign
            self.ref_position = pos
            self.update()

    # ---------------- UPDATE ----------------

    def poll(self):
        self.update()
        self.root.after(POLL_INTERVAL * 1000, self.poll)

    def update(self):
        if self.ref_position:
            ref_pos = self.ref_position
        else:
            ref_pos = get_position_by_callsign(MY_CALLSIGN)

        rows = get_latest_positions()
        seen = set()

        for r in rows:
            src = r["src"].split(",")[0]
            seen.add(src)

            lat = dms_to_decimal(r["lat"], r["lat_dir"])
            lon = dms_to_decimal(r["long"], r["long_dir"])
            if lat is None or lon is None:
                continue

            dist = ""
            if ref_pos and src != self.ref_callsign:
                dist = f"{haversine(ref_pos[0], ref_pos[1], lat, lon):.2f}"

            if self.ref_callsign:
                tag = "ref" if src == self.ref_callsign else "normal"
            else:
                tag = "me" if src.startswith(MY_CALLSIGN) else "normal"

            values = (
                src,
                f"{lat:.5f}",
                f"{lon:.5f}",
                r["time"],
                dist
            )

            if src in self.items:
                self.tree.item(self.items[src], values=values, tags=(tag,))
                if src != self.ref_callsign:
                    self.tree.move(self.items[src], "", 0)
            else:
                self.items[src] = self.tree.insert(
                    "", 0 if src != self.ref_callsign else "end",
                    values=values,
                    tags=(tag,)
                )

        for cs in list(self.items):
            if cs not in seen:
                self.tree.delete(self.items[cs])
                del self.items[cs]


# ---------------- MAIN ----------------

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
