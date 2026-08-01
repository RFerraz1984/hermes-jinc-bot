#!/usr/bin/env python3
"""
Orquestrador principal - Legislative Tracker BR.
Monitora proposições na Câmara, Senado e DOU sobre PcD/acessibilidade.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from fetch_camara import fetch_camara_proposicoes
from fetch_senado import fetch_senado_materias
from fetch_dou import fetch_dou_leis
from normalize import normalize_proposicao
from score import calculate_relevance
from dedup import DedupManager
from enrich import enrich_batch
from alert import AlertManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
KEYWORDS_FILE = BASE_DIR / "templates" / "keywords.yaml"
DATA_DIR = Path("/opt/data/legislative-tracker")
DATA_DIR.mkdir(parents=True, exist_ok=True)


class LegislativeTracker:
    """Orquestra monitoramento legislativo completo."""
    
    def __init__(self, keywords_path: Path, data_dir: Path, dry_run: bool = False):
        self.keywords_path = keywords_path
        self.data_dir = data_dir
        self.dry_run = dry_run
        self.keywords = self._load_keywords()
        
        # Diretórios
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "digest").mkdir(exist_ok=True)
        
        # Gerenciadores
        self.dedup = DedupManager(self.data_dir / "proposicoes.db")
        self.alert_mgr = AlertManager(self.data_dir)
        
        # Stats
        self.stats = {
            "started_at": datetime.now().isoformat(),
            "sources_processed": 0,
            "total_fetched": 0,
            "total_new": 0,
            "total_relevant": 0,
            "alerts_sent": 0,
            "errors": 0,
        }
    
    def _load_keywords(self) -> Dict[str, List[str]]:
        with open(self.keywords_path) as f:
            config = yaml.safe_load(f)
        return config.get("keywords", {})
    
    async def run_camara(self) -> Dict[str, Any]:
        """Busca proposições na Câmara dos Deputados."""
        logger.info("=== Iniciando Câmara dos Deputados ===")
        result = {"source": "camara", "fetched": 0, "new": 0, "relevant": 0, "errors": []}
        
        try:
            proposicoes = await fetch_camara_proposicoes()
            result["fetched"] = len(proposicoes)
            self.stats["total_fetched"] += len(proposicoes)
            
            # Normaliza
            normalized = [normalize_proposicao(p, "camara") for p in proposicoes]
            
            # Dedup
            new_items = []
            for item in normalized:
                content_hash = self.dedup.compute_hash(item)
                if not self.dedup.is_seen(content_hash):
                    new_items.append(item)
                    if not self.dry_run:
                        self.dedup.mark_seen(content_hash, item)
                else:
                    result["duplicates"] = result.get("duplicates", 0) + 1
            
            result["new"] = len(new_items)
            self.stats["total_new"] += len(new_items)
            
            if not new_items:
                return result
            
            # Score + Enrich
            scored = []
            for item in new_items:
                score = calculate_relevance(item, self.keywords)
                item["relevance_score"] = score
                scored.append(item)
            
            enriched = enrich_batch(scored)
            result["relevant"] = len([i for i in enriched if i.get("relevance_score", 0) >= 50])
            self.stats["total_relevant"] += result["relevant"]
            
            # Alertas imediatos (score >= 50)
            high_relevance = [i for i in enriched if i.get("relevance_score", 0) >= 50]
            if high_relevance and not self.dry_run:
                sent = await self.alert_mgr.send_alerts(high_relevance, "camara")
                result["alerts_sent"] = sent
                self.stats["alerts_sent"] += sent
            
            # Armazena
            if not self.dry_run:
                self._store_proposicoes(enriched)
            
        except Exception as e:
            logger.exception("Erro na Câmara")
            result["errors"].append(str(e))
            self.stats["errors"] += 1
        
        return result
    
    async def run_senado(self) -> Dict[str, Any]:
        """Busca matérias no Senado Federal."""
        logger.info("=== Iniciando Senado Federal ===")
        result = {"source": "senado", "fetched": 0, "new": 0, "relevant": 0, "errors": []}
        
        try:
            materias = await fetch_senado_materias()
            result["fetched"] = len(materias)
            self.stats["total_fetched"] += len(materias)
            
            normalized = [normalize_proposicao(m, "senado") for m in materias]
            
            new_items = []
            for item in normalized:
                content_hash = self.dedup.compute_hash(item)
                if not self.dedup.is_seen(content_hash):
                    new_items.append(item)
                    if not self.dry_run:
                        self.dedup.mark_seen(content_hash, item)
            
            result["new"] = len(new_items)
            self.stats["total_new"] += len(new_items)
            
            if not new_items:
                return result
            
            scored = []
            for item in new_items:
                score = calculate_relevance(item, self.keywords)
                item["relevance_score"] = score
                scored.append(item)
            
            enriched = enrich_batch(scored)
            result["relevant"] = len([i for i in enriched if i.get("relevance_score", 0) >= 50])
            self.stats["total_relevant"] += result["relevant"]
            
            high_relevance = [i for i in enriched if i.get("relevance_score", 0) >= 50]
            if high_relevance and not self.dry_run:
                sent = await self.alert_mgr.send_alerts(high_relevance, "senado")
                result["alerts_sent"] = sent
                self.stats["alerts_sent"] += sent
            
            if not self.dry_run:
                self._store_proposicoes(enriched)
                
        except Exception as e:
            logger.exception("Erro no Senado")
            result["errors"].append(str(e))
            self.stats["errors"] += 1
        
        return result
    
    async def run_dou(self) -> Dict[str, Any]:
        """Busca leis/decretos sancionados no DOU."""
        logger.info("=== Iniciando DOU (leis sancionadas) ===")
        result = {"source": "dou", "fetched": 0, "new": 0, "relevant": 0, "errors": []}
        
        try:
            leis = await fetch_dou_leis()
            result["fetched"] = len(leis)
            self.stats["total_fetched"] += len(leis)
            
            normalized = [normalize_proposicao(l, "dou") for l in leis]
            
            new_items = []
            for item in normalized:
                content_hash = self.dedup.compute_hash(item)
                if not self.dedup.is_seen(content_hash):
                    new_items.append(item)
                    if not self.dry_run:
                        self.dedup.mark_seen(content_hash, item)
            
            result["new"] = len(new_items)
            self.stats["total_new"] += len(new_items)
            
            if not new_items:
                return result
            
            scored = []
            for item in new_items:
                score = calculate_relevance(item, self.keywords)
                item["relevance_score"] = score
                scored.append(item)
            
            enriched = enrich_batch(scored)
            result["relevant"] = len([i for i in enriched if i.get("relevance_score", 0) >= 50])
            self.stats["total_relevant"] += result["relevant"]
            
            high_relevance = [i for i in enriched if i.get("relevance_score", 0) >= 50]
            if high_relevance and not self.dry_run:
                sent = await self.alert_mgr.send_alerts(high_relevance, "dou")
                result["alerts_sent"] = sent
                self.stats["alerts_sent"] += sent
            
            if not self.dry_run:
                self._store_proposicoes(enriched)
                
        except Exception as e:
            logger.exception("Erro no DOU")
            result["errors"].append(str(e))
            self.stats["errors"] += 1
        
        return result
    
    def _store_proposicoes(self, proposicoes: List[Dict[str, Any]]):
        """Armazena proposições em JSONL."""
        jsonl_path = self.data_dir / "proposicoes.jsonl"
        with open(jsonl_path, "a", encoding="utf-8") as f:
            for p in proposicoes:
                p["stored_at"] = datetime.now().isoformat()
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
    
    async def run_all(self) -> Dict[str, Any]:
        """Executa todos os monitores."""
        logger.info("Iniciando Legislative Tracker BR - todas as fontes")
        
        self.stats["sources_processed"] = 0
        results = []
        
        # Executa em paralelo fontes independentes
        camara_task = self.run_camara()
        senado_task = self.run_senado()
        dou_task = self.run_dou()
        
        camara_result = await camara_task
        results.append(camara_result)
        self.stats["sources_processed"] += 1
        
        senado_result = await senado_task
        results.append(senado_result)
        self.stats["sources_processed"] += 1
        
        dou_result = await dou_task
        results.append(dou_result)
        self.stats["sources_processed"] += 1
        
        # Digest diário
        if not self.dry_run:
            await self._generate_daily_digest()
        
        self.stats["finished_at"] = datetime.now().isoformat()
        
        return {
            "stats": self.stats,
            "results": results,
        }
    
    async def _generate_daily_digest(self):
        """Gera e envia digest diário."""
        # Carrega proposições de hoje
        jsonl_path = self.data_dir / "proposicoes.jsonl"
        if not jsonl_path.exists():
            return
        
        today = date.today().isoformat()
        todays = []
        
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                try:
                    p = json.loads(line)
                    if p.get("stored_at", "").startswith(today):
                        todays.append(p)
                except json.JSONDecodeError:
                    continue
        
        if not todays:
            return
        
        # Envia digest
        await self.alert_mgr.send_daily_digest(todays, self.stats)


async def main():
    parser = argparse.ArgumentParser(description="Legislative Tracker BR - Monitoramento legislativo PcD")
    parser.add_argument("--camara", action="store_true", help="Executa apenas Câmara")
    parser.add_argument("--senado", action="store_true", help="Executa apenas Senado")
    parser.add_argument("--dou", action="store_true", help="Executa apenas DOU")
    parser.add_argument("--all", action="store_true", help="Executa todas as fontes")
    parser.add_argument("--dry-run", action="store_true", help="Não salva nem alerta")
    parser.add_argument("--stats", action="store_true", help="Mostra estatísticas")
    parser.add_argument("--cleanup", type=int, help="Limpa hashes antigos (>N dias)")
    args = parser.parse_args()
    
    tracker = LegislativeTracker(KEYWORDS_FILE, DATA_DIR, dry_run=args.dry_run)
    
    if args.stats:
        print(json.dumps(tracker.dedup.get_stats(), indent=2))
        return
    
    if args.cleanup:
        removed = tracker.dedup.cleanup(args.cleanup)
        print(f"Removidos {removed} hashes antigos (> {args.cleanup} dias)")
        return
    
    if args.camara:
        result = await tracker.run_camara()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.senado:
        result = await tracker.run_senado()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.dou:
        result = await tracker.run_dou()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.all:
        result = await tracker.run_all()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    import json
    asyncio.run(main())