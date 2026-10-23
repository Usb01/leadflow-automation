"""Remembers which people were already pushed, so re-running on an overlapping export doesn't
re-create or re-notify them."""
import sqlite3
from datetime import datetime, timezone


class Ledger:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path))
        self.conn.execute("""CREATE TABLE IF NOT EXISTS seen (
            key TEXT PRIMARY KEY, name TEXT, grade TEXT, first_seen TEXT NOT NULL)""")

    @staticmethod
    def keys(lead) -> list[str]:
        return [k for k in (f"email:{lead.email}" if lead.email else None,
                            f"phone:{lead.phone}" if lead.phone else None) if k]

    def split_new(self, leads):
        new, known = [], []
        for lead in leads:
            ks = self.keys(lead)
            hit = self.conn.execute(f"SELECT 1 FROM seen WHERE key IN ({','.join('?' * len(ks))})", ks).fetchone()
            (known if hit else new).append(lead)
        return new, known

    def record(self, leads) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.conn:
            for lead in leads:
                for k in self.keys(lead):
                    self.conn.execute("INSERT OR IGNORE INTO seen VALUES (?,?,?,?)", (k, lead.name, lead.grade, now))
