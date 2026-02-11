import json
import sqlite3
import serial
import os
import socket
import threading
from datetime import datetime
from typing import Dict, Any

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

CONFIG_FILE = "config.json"
UDP_PORT = 1703
UDP_PREFIX = "MSG_OUT:"


def load_config() -> Dict[str, Any]:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------
# TIME (formato italiano)
# --------------------------------------------------

def italian_timestamp() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


# --------------------------------------------------
# DATABASE HANDLER
# --------------------------------------------------

class SQLiteHandler:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def ensure_table(self, table: str, fields: Dict[str, Any]):
        cur = self.conn.cursor()

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT
            )
        """)

        cur.execute(f"PRAGMA table_info({table})")
        existing_cols = {row["name"] for row in cur.fetchall()}

        for field in fields.keys():
            if field not in existing_cols:
                cur.execute(
                    f"ALTER TABLE {table} ADD COLUMN {field} TEXT"
                )

        self.conn.commit()

    def insert(self, table: str, data: Dict[str, Any]):
        self.ensure_table(table, data)

        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        values = [str(v) for v in data.values()]

        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        self.conn.execute(query, values)
        self.conn.commit()


# --------------------------------------------------
# FRAME PROCESSOR
# --------------------------------------------------

class FrameProcessor:
    def __init__(self, db: SQLiteHandler, local_callsign: str):
        self.db = db
        self.local_callsign = local_callsign

    def process(self, frame: Dict[str, Any]):
        frame_type = frame.get("type", "unknown")

        if "src" not in frame or not frame["src"]:
            frame["src"] = self.local_callsign

        frame["time"] = italian_timestamp()
        self.db.insert(frame_type, frame)


# --------------------------------------------------
# SERIAL HANDLER
# --------------------------------------------------

class SerialHandler:
    def __init__(self, port: str, baudrate: int, timeout: int):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout
        )
        self.lock = threading.Lock()

    def read_line(self) -> str:
        return self.ser.readline().decode("utf-8", errors="ignore").strip()

    def send_message(self, msg: str):
        with self.lock:
            self.ser.write(msg.encode("utf-8") + b"\n")
            self.ser.flush()


# --------------------------------------------------
# JSON extractor
# --------------------------------------------------

def extract_json(payload: str) -> dict | None:
    start = payload.find("{")
    end = payload.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(payload[start:end + 1])
    except json.JSONDecodeError:
        return None


# --------------------------------------------------
# UDP LISTENER
# --------------------------------------------------

def udp_listener(serial_handler: SerialHandler):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))

    print(f"📨 Listener UDP attivo su porta {UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(2048)
        text = data.decode("utf-8", errors="ignore").strip()

        if text.startswith(UDP_PREFIX):
            payload = text[len(UDP_PREFIX):].strip()
            if payload:
                out_msg = f"::{payload}"
                serial_handler.send_message(out_msg)
                print(f"➡ Inviato a MeshCom da UDP {addr}: {out_msg}")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    config = load_config()

    serial_cfg = config["serial"]
    db_cfg = config["database"]
    node_cfg = config["node"]

    db_path = db_cfg["path"]
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)

    db = SQLiteHandler(db_path)
    processor = FrameProcessor(db, node_cfg["callsign"])

    serial_handler = SerialHandler(
        serial_cfg["port"],
        serial_cfg.get("baudrate", 115200),
        serial_cfg.get("timeout", 1)
    )

    # Thread UDP
    udp_thread = threading.Thread(
        target=udp_listener,
        args=(serial_handler,),
        daemon=True
    )
    udp_thread.start()

    print("📡 MeshCom serial logger avviato...v0.090126 by IK5XMK")

    while True:
        line = serial_handler.read_line()
        if not line:
            continue

        frame = extract_json(line)
        if frame is None:
            continue

        try:
            processor.process(frame)

            frame_type = frame.get("type")
            src = frame.get("src", "?")

            # output base
            out = f"✔ Frame acquisito: {frame_type[0:3]}"

            # messaggio testuale
            if frame_type == "msg":
                msg = frame.get("msg") or frame.get("text") or frame.get("message", "")
                dst = frame.get("dst", "?")
                out += f" | DST: {dst} | DA: {src} | TESTO: {msg}"

            # posizione
            elif frame_type == "pos":
                lat = frame.get("lat", "?")
                lat_dir = frame.get("lat_dir", "?")
                long = frame.get("long", "?")
                long_dir = frame.get("long_dir", "?")
                out += f" | NODO: {src} | LAT: {lat} {lat_dir} | LON: {long} {long_dir}"

            # telemetria
            elif frame_type == "tele":
                out += " | " + " | ".join(
                    f"{k.upper()}: {v}"
                    for k, v in frame.items()
                    if k not in ("type", "time")
                )
    
            print(out)

        except Exception as e:
            print("❌ Errore processamento frame:", e)


if __name__ == "__main__":
    main()
