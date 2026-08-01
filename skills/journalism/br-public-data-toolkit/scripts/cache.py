#!/usr/bin/env python3
"""
Cache Manager - SQLite + Parquet cache local para SIDRA, TSE, DATASUS, etc.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class CacheManager:
    """Gerencia cache local: metadados em SQLite, dados em Parquet."""
    
    def __init__(self, cache_dir: str = "/opt/data/br-public-data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite para metadados (chave -> valor serializado)
        self.db_path = self.cache_dir / "metadata.db"
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL,
                    size_bytes INTEGER
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires 
                ON cache_entries(expires_at)
            """)
    
    def _serialize(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)
    
    def _deserialize(self, text: str) -> Any:
        return json.loads(text)
    
    def get(self, key: str) -> Optional[Any]:
        """Recupera valor do cache se não expirado."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT value, expires_at FROM cache_entries WHERE key = ?", 
                (key,)
            ).fetchone()
            
            if not row:
                return None
            
            if row["expires_at"] and time.time() > row["expires_at"]:
                # Expirado - remove
                self.delete(key)
                return None
            
            return json.loads(row["value"])
    
    def set(self, key: str, value: Any, ttl_days: int = 7):
        """Armazena valor com TTL em dias."""
        expires_at = time.time() + (ttl_days * 86400)
        value_str = json.dumps(value, ensure_ascii=False)
        size_bytes = len(value_str.encode("utf-8"))
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries (key, value, created_at, expires_at, size_bytes)
                VALUES (?, ?, ?, ?, ?)
            """, (key, json.dumps(value), time.time(), time.time() + (ttl_days * 86400), size_bytes))
    
    def delete(self, key: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
    
    def cleanup_expired(self) -> int:
        """Remove entradas expiradas."""
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cache_entries WHERE expires_at < ?", (time.time(),))
            return cursor.rowcount
    
    def get_stats(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
            expired = conn.execute("SELECT COUNT(*) FROM cache_entries WHERE expires_at < ?", (time.time(),)).fetchone()[0]
            size = conn.execute("SELECT SUM(size_bytes) FROM cache_entries").fetchone()[0] or 0
            return {
                "total_entries": total,
                "expired": expired,
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 2),
            }


class ParquetCache:
    """Cache de DataFrames em arquivos Parquet particionados."""
    
    def __init__(self, base_dir: str = "/opt/data/br-public-data/processed"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, df: pd.DataFrame, dataset: str, partition_by: List[str] = None, **kwargs):
        """Salva DataFrame particionado."""
        out_dir = self.base_dir / dataset
        out_dir.mkdir(parents=True, exist_ok=True)
        
        if partition_by and all(col in df.columns for col in partition_by):
            df.to_parquet(out_dir, partition_cols=partition_by, index=False, **kwargs)
        else:
            # Arquivo único
            path = out_dir / f"data_{pd.Timestamp.now().strftime('%Y%m%d')}.parquet"
            df.to_parquet(path, index=False, **kwargs)
        
        logger.info(f"Parquet salvo: {dataset} ({len(df)} linhas)")
    
    def load(self, dataset: str, filters: Dict[str, Any] = None, **kwargs) -> pd.DataFrame:
        """Carrega DataFrame com filtros opcionais."""
        dataset_dir = self.base_dir / dataset
        
        if not dataset_dir.exists():
            return pd.DataFrame()
        
        # Se tem partições, usa pyarrow dataset
        try:
            import pyarrow.dataset as ds
            import pyarrow.parquet as pq
            
            dataset_ds = ds.dataset(dataset_dir, format="parquet")
            table = dataset_ds.to_table(filter=filters, **kwargs)
            return table.to_pandas()
        except Exception:
            # Fallback: lê todos os arquivos
            files = list(dataset_dir.rglob("*.parquet"))
            if not files:
                return pd.DataFrame()
            dfs = [pd.read_parquet(f, **kwargs) for f in files]
            return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


class MetadataManager:
    """Gerencia metadados de fontes: última atualização, schemas, etc."""
    
    def __init__(self, meta_dir: str = "/opt/data/br-public-data/metadata"):
        self.meta_dir = Path(meta_dir)
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self.sources_file = self.meta_dir / "sources.yaml"
        self.schemas_dir = self.meta_dir / "schemas"
        self.schemas_dir.mkdir(exist_ok=True)
    
    def load_sources(self) -> Dict:
        import yaml
        if self.sources_file.exists():
            with open(self.sources_file) as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def save_sources(self, sources: Dict):
        import yaml
        with open(self.sources_file, "w") as f:
            yaml.dump(sources, f, allow_unicode=True)
    
    def update_source_timestamp(self, source_id: str):
        """Atualiza timestamp da última coleta bem-sucedida."""
        sources = self.load_sources()
        if source_id in sources:
            sources[source_id]["last_fetched"] = pd.Timestamp.now().isoformat()
            self.save_sources(sources)
    
    def save_schema(self, name: str, schema: Dict):
        """Salva schema de validação (Pydantic-like)."""
        import yaml
        path = self.schemas_dir / f"{name}.yaml"
        with open(path, "w") as f:
            yaml.dump(schema, f, allow_unicode=True)
    
    def load_schema(self, name: str) -> Optional[Dict]:
        import yaml
        path = self.schemas_dir / f"{name}.yaml"
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return None


# Instâncias globais para uso simples
_global_cache: Optional[CacheManager] = None
_global_parquet: Optional[ParquetCache] = None
_global_meta: Optional[MetadataManager] = None


def get_cache() -> CacheManager:
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache


def get_parquet_cache() -> ParquetCache:
    global _global_parquet
    if _global_parquet is None:
        _global_parquet = ParquetCache()
    return _global_parquet


def get_metadata() -> MetadataManager:
    global _global_meta
    if _global_meta is None:
        _global_meta = MetadataManager()
    return _global_meta


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Teste
    cache = CacheManager("/tmp/test_cache")
    cache.set("test_key", {"teste": "valor", "numero": 123}, ttl_days=1)
    print("Get:", cache.get("test_key"))
    print("Stats:", cache.get_stats())
    
    # Teste Parquet
    import pandas as pd
    import numpy as np
    df = pd.DataFrame({"A": [1, 2, 3], "B": ["a", "b", "c"]})
    parquet = ParquetCache("/tmp/test_parquet")
    parquet.save(df, "teste", partition_by=[])
    loaded = parquet.load("teste")
    print("Parquet loaded:", loaded.shape)