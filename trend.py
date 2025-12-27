import sqlite3

def show_trend(project):
    conn = sqlite3.connect("health.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT scanned_at, score
    FROM scans
    WHERE project_path = ?
    ORDER BY scanned_at
    """, (project,))

    rows = cur.fetchall()
    conn.close()

    if len(rows) < 2:
        print("Not enough scans for trend.")
        return

    print("\nHealth Trend:")
    for date, score in rows:
        print(f"{date}: {score}")
