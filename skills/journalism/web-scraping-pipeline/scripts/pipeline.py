#!/usr/bin/env python3
"""
Orquestrador principal do pipeline de web scraping.
Coordena fetch → parse → dedup → enrich → alert → store.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from fetch import fetch_source, FetchError
from parse import parse_content
from dedup import DedupManager
from enrich import enrich_batch
from alert import AlertManager, DigestGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
SOURCES_FILE = BASE_DIR / "templates" / "sources.yaml"
DATA_DIR = Path("/opt/data/web-scraping")
DATA_DIR.mkdir(parents=True, exist_ok=True)


class ScrapingPipeline:
    """Pipeline completo de web scraping para jornalismo inclusivo."""
    
    def __init__(
        self,
        config_path: Path = SOURCES_FILE,
        data_dir: Path = DATA_DIR,
        dry_run: bool = False,
    ):
        self.config_path = Path(config_path)
        self.data_dir = Path(data_dir)
        self.dry_run = dry_run
        
        self.sources = self._load_sources()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "digest").mkdir(exist_ok=True)
        (self.data_dir / "raw").mkdir(exist_ok=True)
        
        # Gerenciadores
        self.dedup = DedupManager(self.data_dir / "seen_hashes.db")
        self.alert_mgr = AlertManager(self.data_dir)
        self.digest_gen = DigestGenerator(self.data_dir)
        
        # Stats
        self.stats = {
            "started_at": datetime.now().isoformat(),
            "sources_processed": 0,
            "items_fetched": 0,
            "items_parsed": 0,
            "items_new": 0,
            "items_duplicate": 0,
            "alerts_sent": 0,
            "errors": 0,
        }
    
    def _load_sources(self) -> List[Dict[str, Any]]:
        """Carrega configuração de fontes do YAML."""
        if not self.config_path.exists():
            logger.warning(f"Sources file não encontrado: {self.config_path}")
            return []
        
        with open(self.config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        sources = config.get("sources", [])
        enabled = [s for s in sources if s.get("enabled", True)]
        logger.info(f"Carregadas {len(enabled)} fontes habilitadas de {len(sources)} total")
        return enabled
    
    def get_source_config(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Retorna config de uma fonte pelo ID."""
        for s in self.sources:
            if s["id"] == source_id:
                return s
        return None
    
    async def process_source(self, source_id: str) -> Dict[str, Any]:
        """Processa uma única fonte completa."""
        source = self.get_source_config(source_id)
        if not source:
            return {"error": f"Fonte não encontrada: {source_id}"}
        
        logger.info(f"=== Iniciando fonte: {source['name']} ({source_id}) ===")
        
        result = {
            "source_id": source_id,
            "source_name": source["name"],
            "fetched": 0,
            "parsed": 0,
            "new": 0,
            "duplicates": 0,
            "alerts": 0,
            "errors": [],
        }
        
        try:
            # 1. FETCH
            logger.info(f"[{source_id}] Fetching...")
            raw_content = await fetch_source(source)
            result["fetched"] = 1 if raw_content else 0
            self.stats["items_fetched"] += result["fetched"]
            
            if not raw_content:
                result["errors"].append("Fetch retornou vazio")
                return result
            
            # Salva raw
            if not self.dry_run:
                raw_path = self.data_dir / "raw" / f"{source_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                raw_path.write_bytes(raw_content if isinstance(raw_content, bytes) else raw_content.encode())
            
            # 2. PARSE
            logger.info(f"[{source_id}] Parsing...")
            items = parse_content(raw_content, source)
            result["parsed"] = len(items)
            self.stats["items_parsed"] += len(items)
            
            if not items:
                result["errors"].append("Parse retornou zero itens")
                return result
            
            # 3. DEDUP + ENRICH
            new_items = []
            for item in items:
                item["source_id"] = source_id
                item["source_name"] = source["name"]
                
                content_hash = self.dedup.compute_hash(item)
                
                if self.dry_run:
                    is_new = not self.dedup.is_seen(content_hash)
                else:
                    is_new = not self.dedup.is_seen(content_hash)
                    if is_new:
                        self.dedup.mark_seen(content_hash, item)
                
                if is_new:
                    new_items.append(item)
                    result["new"] += 1
                else:
                    result["duplicates"] += 1
            
            self.stats["items_new"] += result["new"]
            self.stats["items_duplicate"] += result["duplicates"]
            
            if not new_items:
                logger.info(f"[{source_id}] Nenhum item novo")
                return result
            
            # 4. ENRICH
            logger.info(f"[{source_id}] Enriquecendo {len(new_items)} itens...")
            enriched = enrich_batch(new_items, source)
            
            # 5. ALERT (itens alta relevância)
            high_relevance = [i for i in enriched if i.get("relevance_score", 0) >= 50]
            if high_relevance and not self.dry_run:
                logger.info(f"[{source_id}] Enviando {len(high_relevance)} alertas...")
                sent = await self.alert_mgr.send_alerts(high_relevance, source)
                result["alerts"] = sent
                self.stats["alerts_sent"] += sent
            
            # 6. STORE JSONL
            if not self.dry_run:
                jsonl_path = self.data_dir / "items.jsonl"
                with open(jsonl_path, "a", encoding="utf-8") as f:
                    for item in enriched:
                        item["processed_at"] = datetime.now().isoformat()
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
            logger.info(f"[{source_id}] Concluído: {result}")
            
        except FetchError as e:
            result["errors"].append(f"Fetch: {e}")
            self.stats["errors"] += 1
        except Exception as e:
            logger.exception(f"[{source_id}] Erro inesperado")
            result["errors"].append(f"Unexpected: {e}")
            self.stats["errors"] += 1
        
        self.stats["sources_processed"] += 1
        return result
    
    async def run_all(self) -> Dict[str, Any]:
        """Executa pipeline para todas as fontes habilitadas."""
        logger.info("=== Iniciando pipeline completo ===")
        
        all_results = []
        
        for source in self.sources:
            source_id = source["id"]
            result = await self.process_source(source_id)
            all_results.append(result)
        
        # Digest diário
        if not self.dry_run:
            logger.info("Gerando digest diário...")
            await self.digest_gen.generate_daily()
        
        self.stats["finished_at"] = datetime.now().isoformat()
        
        summary = {
            "stats": self.stats,
            "results": all_results,
        }
        
        # Salva summary
        summary_path = self.data_dir / f"pipeline_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"=== Pipeline concluído: {self.stats} ===")
        return summary
    
    async def run_sources(self, source_ids: List[str]) -> Dict[str, Any]:
        """Executa pipeline para fontes específicas."""
        logger.info(f"=== Executando fontes: {source_ids} ===")
        
        all_results = []
        for source_id in source_ids:
            result = await self.process_source(source_id)
            all_results.append(result)
        
        self.stats["finished_at"] = datetime.now().isoformat()
        
        return {
            "stats": self.stats,
            "results": all_results,
        }


async def main():
    parser = argparse.ArgumentParser(description="Web Scraping Pipeline - Jornalista Inclusivo")
    parser.add_argument("--source", "-s", help="ID da fonte específica (ou 'all')")
    parser.add_argument("--sources", help="Lista de fontes separadas por vírgula")
    parser.add_argument("--all", action="store_true", help="Executa todas as fontes")
    parser.add_argument("--dry-run", action="store_true", help="Não salva nem alerta")
    parser.add_argument("--config", default=str(SOURCES_FILE), help="Arquivo sources.yaml")
    parser.add_argument("--list", action="store_true", help="Lista fontes disponíveis")
    args = parser.parse_args()
    
    pipeline = ScrapingPipeline(
        config_path=Path(args.config),
        dry_run=args.dry_run,
    )
    
    if args.list:
        print("\nFontes disponíveis:")
        for s in pipeline.sources:
            status = "✅" if s.get("enabled", True) else "❌"
            print(f"  {status} {s['id']}: {s['name']} ({s.get('schedule', 'manual')})")
        return
    
    if args.source:
        if args.source == "all" or args.all:
            result = await pipeline.run_all()
        else:
            result = await pipeline.run_all()  # run_all processa todas habilitadas
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.sources:
        source_list = [s.strip() for s in args.sources.split(",")]
        result = await pipeline.run_sources(source_list)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    import json
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    asyncio.run(main())