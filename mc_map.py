import tkinter as tk
from tkinter import ttk
import tkintermapview
import sqlite3
import math
import json
from datetime import datetime

# ---------------- CONFIG ----------------

CONFIG_FILE = "config_map.json"

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

DB_PATH = CONFIG.get("DB_PATH", "meshcom.db")
POLL_INTERVAL = int(CONFIG.get("POLL_INTERVAL", 10))
RADIUS_KM = float(CONFIG.get("RADIUS_KM", 20))

# ---------------- UTILS ----------------

def normalize_src(src):
    return src.split(",")[0].strip()


def convert_coord(value, direction):
    value = float(value)
    if direction in ("S", "W"):
        value = -value
    return value


def calculate_zoom(radius_km):
    if radius_km <= 5:
        return 12
    elif radius_km <= 10:
        return 11
    elif radius_km <= 20:
        return 10
    elif radius_km <= 50:
        return 9
    return 8


def load_latest_positions():
    """
    Ritorna una LISTA ordinata dal più recente al più vecchio
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = """
        SELECT src, time, lat, lat_dir, long, long_dir
        FROM pos
        WHERE lat IS NOT NULL AND long IS NOT NULL
        ORDER BY rowid DESC
    """

    cur.execute(query)

    seen = set()
    nodes = []

    for src, time, lat, lat_dir, lon, lon_dir in cur.fetchall():
        callsign = normalize_src(src)

        if callsign in seen:
            continue

        try:
            ts = datetime.strptime(time, "%d/%m/%Y %H:%M:%S")
        except ValueError:
            continue

        seen.add(callsign)

        nodes.append({
            "callsign": callsign,
            "lat": convert_coord(lat, lat_dir),
            "lon": convert_coord(lon, lon_dir),
            "time": time,
            "ts": ts
        })

    conn.close()
    return nodes

# ---------------- GUI ----------------

class MapApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("MeshCom – Mappa nodi v0.100126 by IK5XMK")
        self.geometry("1100x700")

        self.nodes = []
        self.nodes_by_cs = {}

        # ---- Layout ----
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main, width=240)
        left.pack(side="left", fill="y")

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        # ---- Listbox ----
        ttk.Label(left, text="Nodi disponibili").pack(pady=5)

        self.listbox = tk.Listbox(left)
        self.listbox.pack(fill="y", expand=True, padx=5)

        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # ---- Mappa ----
        self.map_widget = tkintermapview.TkinterMapView(
            right,
            corner_radius=0
        )
        self.map_widget.pack(fill="both", expand=True)

        self.marker = None

        # primo caricamento
        self.refresh_nodes(initial=True)

    # ---------------- REFRESH ----------------

    def refresh_nodes(self, initial=False):
        previous_selection = None
        if self.listbox.curselection():
            previous_selection = self.listbox.get(self.listbox.curselection())

        self.nodes = load_latest_positions()
        self.nodes_by_cs = {n["callsign"]: n for n in self.nodes}

        self.listbox.delete(0, "end")
        for n in self.nodes:
            self.listbox.insert("end", n["callsign"])

        if previous_selection and previous_selection in self.nodes_by_cs:
            idx = list(self.nodes_by_cs.keys()).index(previous_selection)
            self.listbox.selection_set(idx)
        elif self.nodes:
            self.listbox.selection_set(0)

        if initial or self.listbox.curselection():
            self.on_select()

        # pianifica prossimo refresh
        self.after(POLL_INTERVAL * 1000, self.refresh_nodes)

    # ---------------- EVENT ----------------

    def on_select(self, event=None):
        if not self.listbox.curselection():
            return

        callsign = self.listbox.get(self.listbox.curselection())
        node = self.nodes_by_cs.get(callsign)

        if not node:
            return

        lat = node["lat"]
        lon = node["lon"]
        time = node["time"]

        self.map_widget.set_position(lat, lon)
        self.map_widget.set_zoom(calculate_zoom(RADIUS_KM))

        if self.marker:
            self.marker.delete()

        # marker = punto blu minimale
        self.marker = self.map_widget.set_marker(
            lat,
            lon,
            text=f"{callsign}\n{time}",
            marker_color_circle="blue",
            marker_color_outside="blue",
            text_color="black"
        )

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app = MapApp()
    app.mainloop()
