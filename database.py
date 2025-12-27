import sqlite3

def init_db():
    conn = sqlite3.connect("health.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY,
        project_path TEXT,
        score INTEGER,
        scanned_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS suggestions (
        scan_id INTEGER,
        severity TEXT,
        message TEXT
    )
    """)

    conn.commit()
    conn.close()


def store_scan(project, score, suggestions):
    conn = sqlite3.connect("health.db")
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO scans (project_path, score, scanned_at) VALUES (?, ?, datetime('now'))",
        (project, score)
    )

    scan_id = cur.lastrowid

    for s in suggestions:
        sev = s["severity"]
        msg = f"{s['title']} | {s['how']}"
        cur.execute(
            "INSERT INTO suggestions VALUES (?, ?, ?)",
            (scan_id, sev, msg)
        )


    conn.commit()
    conn.close()
