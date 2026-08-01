#!/usr/bin/env python3
"""
Deduplicação de proposições - SHA-256 + SQLite.
"""

import hashlib
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DedupManager:
    """Gerencia deduplicação via SQLite."""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_hashes (
                    hash TEXT PRIMARY KEY,
                    id_externo TEXT,
                    casa TEXT,
                    ementa TEXT,
                    autor TEXT,
                    data_apresentacao TEXT,
                    content_hash TEXT,
                    first_seen REAL,
                    last_seen REAL,
                    count INTEGER DEFAULT 1,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_casa_date 
                ON seen_hashes(casa, first_seen)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash 
                ON seen_hashes(content_hash)
            """)
            conn.commit()
    
    def compute_hash(self, item: Dict[str, Any]) -> str:
        """Gera SHA-256 do conteúdo normalizado."""
        # Campos que definem identidade única
        identity_fields = [
            item.get("id_externo", ""),
            item.get("ementa", ""),
            item.get("autor", ""),
            item.get("data_apresentacao", ""),
        ]
        normalized = "|".join(
            str(f).strip().lower() if f else "" 
            for f in identity_fields
        )
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]
    
    def is_seen(self, content_hash: str) -> bool:
        """Verifica se hash já foi visto."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM seen_hashes WHERE hash = ?", (content_hash,)
            )
            return cursor.fetchone() is not None
    
    def mark_seen(self, content_hash: str, item: Dict[str, Any]):
        """Marca hash como visto (insert or update)."""
        now = time.time()
        metadata = {
            k: v for k, v in item.items() 
            if k not in ("id_externo", "ementa", "autor", "data_apresentacao")
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO seen_hashes (hash, id_externo, casa, ementa, autor, data_apresentacao, content_hash, first_seen, last_seen, count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(hash) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    count = count + 1,
                    metadata = excluded.metadata
            """, (
                content_hash,
                item.get("id_externo", ""),
                item.get("casa", ""),
                item.get("ementa", "")[:500],
                item.get("autor", "")[:200],
                item.get("data_apresentacao", ""),
                item.get("content_hash", "")[:64],
                now,
                now,
                json.dumps(metadata, ensure_ascii=False)
            ))
            conn.commit()
    
    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas do banco."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM seen_hashes").fetchone()[0]
            now = time.time()
            last_24h = conn.execute(
                "SELECT COUNT(*) FROM seen_hashes WHERE first_seen > ?", 
                (now - 86400,)
            ).fetchone()[0]
            last_7d = conn.execute(
                "SELECT COUNT(*) FROM seen_hashes WHERE first_seen > ?", 
                (now - 604800,)
            ).fetchone()[0]
            return {
                "total": total,
                "last_24h": last_24h,
                "last_7d": last_7d
            }
    
    def cleanup(self, days: int) -> int:
        """Remove hashes mais antigos que N dias."""
        cutoff = time.time() - (days * 86400)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM seen_hashes WHERE first_seen < ?", (cutoff,)
            )
            conn.commit()
            return cursor.rowcount
    
    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna itens mais recentes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT hash, id_externo, casa, ementa, autor, first_seen, count 
                FROM seen_hashes 
                ORDER BY first_seen DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        dm = DedupManager(db)
        
        item1 = {"id_externo": "PL-1234/2026", "ementa": "Teste", "autor": "Fulano", "data_apresentacao": "2026-07-24"}
        h1 = dm.compute_hash(item1)
        print(f"Hash 1: {h1}")
        print(f"Seen: {dm.is_seen(h1)}")
        dm.mark_seen(h1, item1)
        print(f"Seen after mark: {dm.is_seen(h1)}")
        
        item2 = {"id_externo": "PL-1234/2026", "ementa": "Teste", "autor": "Fulano", "data_apresentacao": "2026-07-24"}
        h2 = dm.compute_hash(item2)
        print(f"Hash 2 (mesmo conteúdo): {h2}")
        print(f"Same hash: {h1 == h2}")
        
        print(f"Stats: {dm.get_stats()}")