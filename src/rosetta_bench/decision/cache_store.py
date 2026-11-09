"""SQLite storage for Rosetta canonical decision-cache entries. The key, entry format and
validity rules live in rosetta_core.decision.cache; this module only stores entries."""
import json
import sqlite3
from pathlib import Path

_SCHEMA = """CREATE TABLE IF NOT EXISTS entries (
    key TEXT PRIMARY KEY, entry_json TEXT NOT NULL, created_at TEXT, expires_at TEXT, hits INTEGER NOT NULL DEFAULT 0)"""


class DecisionCache:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(self.path)
        self._con.execute(_SCHEMA)
        self._con.commit()

    def get(self, key: str) -> dict | None:
        row = self._con.execute("SELECT entry_json FROM entries WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, entry: dict) -> None:
        self._con.execute(
            "INSERT INTO entries (key, entry_json, created_at, expires_at, hits) VALUES (?, ?, ?, ?, 0) "
            "ON CONFLICT(key) DO UPDATE SET entry_json = excluded.entry_json, created_at = excluded.created_at, "
            "expires_at = excluded.expires_at",
            (entry["key"], json.dumps(entry, ensure_ascii=False), entry.get("created_at"), entry.get("expires_at")),
        )
        self._con.commit()

    def record_hit(self, key: str) -> None:
        self._con.execute("UPDATE entries SET hits = hits + 1 WHERE key = ?", (key,))
        self._con.commit()

    def stats(self) -> dict:
        entries, hits = self._con.execute("SELECT COUNT(*), COALESCE(SUM(hits), 0) FROM entries").fetchone()
        return {"entries": entries, "hits": hits}

    def close(self) -> None:
        self._con.close()
