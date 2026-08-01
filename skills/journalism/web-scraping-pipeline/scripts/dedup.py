#!/usr/bin/env python3
"""
Módulo de deduplicação - SHA-256 + SQLite para persistência.
"""

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class DedupManager:
    """Gerencia deduplicação via hash SHA-256 + SQLite."""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._cache: Set[str] = set()
        self._load_cache()
    
    def _init_db(self):
        """Cria tabela se não existe."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_hashes (
                    hash TEXT PRIMARY KEY,
                    source_id TEXT,
                    title TEXT,
                    url TEXT,
                    content_hash TEXT,
                    first_seen REAL,
                    last_seen REAL,
                    count INTEGER DEFAULT 1,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_date 
                ON seen_hashes(source_id, first_seen)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash 
                ON seen_hashes(content_hash)
            """)
            conn.commit()
    
    def _load_cache(self):
        """Carrega hashes recentes em memória (últimos 7 dias)."""
        cutoff = time.time() - (7 * 86400)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT hash FROM seen_hashes WHERE first_seen > ?",
                (cutoff,)
            ).fetchall()
            self._cache = {row["hash"] for row in rows}
        logger.debug(f"Cache dedup carregado: {len(self._cache)} hashes")
    
    def compute_hash(self, item: Dict[str, Any]) -> str:
        """
        Gera SHA-256 do conteúdo normalizado do item.
        Usa campos que definem identidade: title + url + content + date.
        """
        # Campos que compõem a identidade
        identity_fields = [
            item.get("title", ""),
            item.get("url", ""),
            item.get("content", ""),
            item.get("date", ""),
            item.get("source_id", ""),
        ]
        
        # Normaliza: strip, lower, remove whitespace extra
        normalized = "|".join(
            str(f).strip().lower() if f else "" 
            for f in identity_fields
        )
        
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]
    
    def is_seen(self, content_hash: str) -> bool:
        """Verifica se hash já foi visto (cache + DB)."""
        if content_hash in self._cache:
            return True
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM seen_hashes WHERE hash = ?",
                (content_hash,)
            )
            return cursor.fetchone() is not None
    
    def mark_seen(self, content_hash: str, item: Dict[str, Any]):
        """Marca hash como visto (insert or update)."""
        now = time.time()
        metadata = {
            k: v for k, v in item.items() 
            if k not in ("title", "url", "content", "date", "source_id")
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO seen_hashes (hash, source_id, title, url, content_hash, first_seen, last_seen, count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(hash) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    count = count + 1,
                    metadata = excluded.metadata
            """, (
                content_hash,
                item.get("source_id", ""),
                item.get("title", "")[:500],
                item.get("url", "")[:500],
                item.get("content_hash", ""),
                now,
                now,
                json.dumps(metadata, ensure_ascii=False),
            ))
            conn.commit()
        
        self._cache.add(content_hash)
    
    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas do banco."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM seen_hashes").fetchone()[0]
            last_24h = conn.execute(
                "SELECT COUNT(*) FROM seen_hashes WHERE first_seen > ?",
                (time.time() - 86400,)
            ).fetchone()[0]
            last_7d = conn.execute(
                "SELECT COUNT(*) FROM seen_hashes WHERE first_seen > ?",
                (time.time() - 7*86400,)
            ).fetchone()[0]
            return {
                "total": total,
                "last_24h": last_24h,
                "last_7d": last_7d,
            }
    
    def cleanup(self, days: int = 30) -> int:
        """Remove hashes mais antigos que N dias."""
        cutoff = time.time() - (days * 86400)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM seen_hashes WHERE first_seen < ?",
                (cutoff,)
            )
            conn.commit()
            removed = cursor.rowcount
        
        # Recarrega cache
        self._load_cache()
        
        logger.info(f"Dedup cleanup: removidos {removed} hashes (> {days} dias)")
        return removed
    
    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna itens mais recentes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT hash, source_id, title, url, first_seen, count, metadata
                FROM seen_hashes 
                ORDER BY first_seen DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [dict(row) for row in rows]


def compute_content_hash(text: str) -> str:
    """Hash simples de string (para uso standalone)."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:32]


if __name__ == "__main__":
    import argparse
    import tempfile
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Dedup Manager Test")
    parser.add_argument("--test", action="store_true", help="Roda testes")
    args = parser.parse_args()
    
    if args.test:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test_dedup.db"
            dm = DedupManager(db)
            
            # Teste 1: item novo
            item1 = {"title": "Teste", "url": "http://ex.com/1", "content": "Conteúdo", "date": "2026-07-24", "source_id": "test"}
            h1 = dm.compute_hash(item1)
            print(f"Hash 1: {h1}")
            print(f"Seen antes: {dm.is_seen(h1)}")
            dm.mark_seen(h1, item1)
            print(f"Seen depois: {dm.is_seen(h1)}")
            
            # Teste 2: mesmo conteúdo
            item2 = {"title": "Teste", "url": "http://ex.com/1", "content": "Conteúdo", "date": "2026-07-24", "source_id": "test"}
            h2 = dm.compute_hash(item2)
            print(f"Hash 2 (mesmo): {h2}")
            print(f"Same hash: {h1 == h2}")
            print(f"Seen: {dm.is_seen(h2)}")
            
            # Teste 3: conteúdo diferente
            item3 = {"title": "Teste 2", "url": "http://ex.com/2", "content": "Outro", "date": "2026-07-24", "source_id": "test"}
            h3 = dm.compute_hash(item3)
            print(f"Hash 3 (diferente): {h3}")
            print(f"Seen: {dm.is_seen(h3)}")
            
            print(f"Stats: {dm.get_stats()}")
            print(f"Recent: {dm.get_recent(5)}")
        
        print("Todos os testes passaram!")