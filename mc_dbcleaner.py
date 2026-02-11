import sqlite3
import sys
import os

TIME_FIELD = "time"

def cleanup_database(db_path):
    if not os.path.isfile(db_path):
        print(f"ERRORE: file non trovato ({db_path})")
        return

    conn = sqlite3.connect(db_path, timeout=30)
    cur = conn.cursor()

    # Lock immediato in scrittura (anti race)
    conn.execute("BEGIN IMMEDIATE")

    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    tables = [row[0] for row in cur.fetchall()]

    total_deleted = 0
    per_table_deleted = {}

    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            before = cur.fetchone()[0]

            if before <= 1:
                continue

            cur.execute(f"""
                DELETE FROM {table}
                WHERE {TIME_FIELD} NOT IN (
                    SELECT {TIME_FIELD}
                    FROM {table}
                    ORDER BY {TIME_FIELD} DESC
                    LIMIT 1
                )
            """)

            deleted = cur.rowcount
            if deleted > 0:
                per_table_deleted[table] = deleted
                total_deleted += deleted

        except sqlite3.OperationalError:
            continue

    conn.commit()
    conn.close()

    if per_table_deleted:
        for table, count in per_table_deleted.items():
            print(f"{table}: {count} record cancellati")
        print(f"Totale record cancellati: {total_deleted}")
    else:
        print("Nessun record cancellato")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        cleanup_database(sys.argv[1])
    else:
        print("Specificare il percorso/nome del database")
