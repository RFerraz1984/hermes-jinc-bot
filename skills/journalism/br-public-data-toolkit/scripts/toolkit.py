#!/usr/bin/env python3
"""
CLI unificado do BR Public Data Toolkit.
Acesso unificado a IBGE/SIDRA, Censo, PNAD, PNS, DATASUS, TSE, Transparência, INEP, MTE.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from ibge_sidra import SIDRAClient
from pnad_continua import PNADContinuaClient
from datasus import DATASUSClient
from tse_eleicoes import TSEClient
from transparencia import TransparenciaClient
from cache import CacheManager
from export import ExportManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path("/opt/data/br-public-data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Carrega queries pré-definidas
QUERIES_FILE = BASE_DIR / "templates" / "queries.yaml"
with open(QUERIES_FILE, encoding="utf-8") as f:
    QUERIES = yaml.safe_load(f).get("queries", {})

# Schemas de validação
SCHEMAS_FILE = BASE_DIR / "templates" / "schemas.yaml"
with open(SCHEMAS_FILE, encoding="utf-8") as f:
    SCHEMAS = yaml.safe_load(f)


class BRPublicDataToolkit:
    """Orquestrador principal do toolkit."""
    
    def __init__(self, cache_dir: Path = None, output_dir: Path = None):
        self.cache = CacheManager(cache_dir or DATA_DIR / "cache")
        self.exporter = ExportManager(output_dir or DATA_DIR / "exports")
        self.sidra = SIDRAClient(self.cache)
        self.pnad = PNADContinuaClient(self.cache)
        self.datasus = DATASUSClient(self.cache)
        self.tse = TSEClient(self.cache)
        self.transparencia = TransparenciaClient(self.cache)
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """Lista todos os datasets disponíveis."""
        datasets = []
        
        # SIDRA queries
        for qid, qconfig in QUERIES.items():
            datasets.append({
                "id": qid,
                "source": "IBGE SIDRA",
                "description": qconfig.get("description", ""),
                "table": qconfig.get("table"),
                "variables": qconfig.get("variables", []),
                "period": qconfig.get("period", "latest"),
                "geography": qconfig.get("geo", "1"),
            })
        
        # Outros datasets
        other_datasets = [
            {"id": "pnad_trabalho", "source": "PNAD Contínua", "description": "Mercado de trabalho PcD", "frequency": "trimestral"},
            {"id": "tse_eleitores", "source": "TSE", "description": "Eleitores PcD por UF", "frequency": "eleitoral"},
            {"id": "tse_secoes", "source": "TSE", "description": "Seções acessíveis", "frequency": "eleitoral"},
            {"id": "datasus_sih", "source": "DATASUS", "description": "Internações PcD (SIH)", "frequency": "mensal"},
            {"id": "datasus_sia", "source": "DATASUS", "description": "Atendimentos ambulatoriais PcD", "frequency": "mensal"},
            {"id": "transparencia_convenios", "source": "Portal Transparência", "description": "Convênios PcD", "frequency": "diário"},
        ]
        datasets.extend(other_datasets)
        
        return datasets
    
    def fetch_sidra(self, query_id: str, **overrides) -> Any:
        """Busca dados via query SIDRA pré-definida."""
        if query_id not in QUERIES:
            raise ValueError(f"Query SIDRA não encontrada: {query_id}")
        
        config = QUERIES[query_id].copy()
        config.update(overrides)
        
        return self.sidra.query(
            table=config["table"],
            variables=config.get("variables", []),
            period=config.get("period", "last"),
            classifications=config.get("classifications", {}),
            geo=config.get("geo", "1"),
        )
    
    def fetch_pnad(self, **kwargs) -> Any:
        """Busca PNAD Contínua - mercado de trabalho PcD."""
        return self.pnad.fetch_latest(**kwargs)
    
    def fetch_tse(self, dataset: str, **kwargs) -> Any:
        """Busca dados TSE."""
        if dataset == "eleitores":
            return self.tse.eleitores_pcd(**kwargs)
        elif dataset == "secoes":
            return self.tse.secoes_acessiveis(**kwargs)
        elif dataset == "candidatos":
            return self.tse.candidatos_pcd(**kwargs)
        else:
            raise ValueError(f"Dataset TSE desconhecido: {dataset}")
    
    def fetch_datasus(self, dataset: str, **kwargs) -> Any:
        """Busca dados DATASUS."""
        if dataset == "sih":
            return self.datasus.sih_pcd(**kwargs)
        elif dataset == "sia":
            return self.datasus.sia_pcd(**kwargs)
        else:
            raise ValueError(f"Dataset DATASUS desconhecido: {dataset}")
    
    def fetch_transparencia(self, **kwargs) -> Any:
        """Busca convênios PcD no Portal da Transparência."""
        return self.transparencia.convenios_pcd(**kwargs)
    
    def export(self, data: Any, output: str, fmt: str = "parquet", **kwargs) -> Path:
        """Exporta dados para arquivo."""
        return self.exporter.export(data, output, fmt, **kwargs)
    
    def validate(self, file_path: str, schema: str) -> Dict[str, Any]:
        """Valida arquivo contra schema."""
        return self.exporter.validate(file_path, schema)


def main():
    parser = argparse.ArgumentParser(description="BR Public Data Toolkit - Dados Públicos Brasileiros")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")
    
    # list
    list_parser = subparsers.add_parser("list", help="Lista datasets disponíveis")
    
    # fetch sidra
    fetch_sidra = subparsers.add_parser("fetch-sidra", help="Busca query SIDRA pré-definida")
    fetch_sidra.add_argument("query_id", help="ID da query (ex: censo2022_deficiencia_uf)")
    fetch_sidra.add_argument("--output", "-o", help="Arquivo de saída")
    fetch_sidra.add_argument("--format", "-f", default="parquet", choices=["parquet", "csv", "json", "xlsx"])
    fetch_sidra.add_argument("--period", help="Período (ex: 2022, last)")
    fetch_sidra.add_argument("--geo", help="Geografia (1=UF, 2=municipio, 6=Brasil)")
    fetch_sidra.add_argument("--vars", help="Variáveis separadas por vírgula")
    
    # fetch pnad
    fetch_pnad = subparsers.add_parser("fetch-pnad", help="Busca PNAD Contínua PcD")
    fetch_pnad.add_argument("--output", "-o", help="Arquivo de saída")
    fetch_pnad.add_argument("--format", "-f", default="parquet", choices=["parquet", "csv", "json", "xlsx"])
    fetch_pnad.add_argument("--vars", help="Variáveis (ex: VD4001,VD4002)")
    fetch_pnad.add_argument("--classif", help="Classificações (ex: deficiencia:all)")
    
    # fetch tse
    fetch_tse = subparsers.add_parser("fetch-tse", help="Busca dados TSE")
    fetch_tse.add_argument("dataset", choices=["eleitores", "secoes", "candidatos"])
    fetch_tse.add_argument("--output", "-o", help="Arquivo de saída")
    fetch_tse.add_argument("--format", "-f", default="parquet", choices=["parquet", "csv", "json", "xlsx"])
    fetch_tse.add_argument("--year", type=int, help="Ano da eleição")
    fetch_tse.add_argument("--uf", help="UF (sigla)")
    
    # fetch datasus
    fetch_datasus = subparsers.add_parser("fetch-datasus", help="Busca dados DATASUS")
    fetch_datasus.add_argument("dataset", choices=["sih", "sia"])
    fetch_datasus.add_argument("--output", "-o", help="Arquivo de saída")
    fetch_datasus.add_argument("--format", "-f", default="parquet", choices=["parquet", "csv", "json", "xlsx"])
    fetch_datasus.add_argument("--cid10", help="Filtro CID-10 (ex: Q%, G80%)")
    fetch_datasus.add_argument("--month", help="Mês (YYYY-MM)")
    
    # fetch transparencia
    fetch_transp = subparsers.add_parser("fetch-transparencia", help="Busca Portal Transparência")
    fetch_transp.add_argument("--output", "-o", help="Arquivo de saída")
    fetch_transp.add_argument("--format", "-f", default="parquet", choices=["parquet", "csv", "json", "xlsx"])
    fetch_transp.add_argument("--query", help="Palavra-chave")
    fetch_transp.add_argument("--days", type=int, default=30, help="Últimos N dias")
    
    # export
    export_parser = subparsers.add_parser("export", help="Exporta todos os datasets processados")
    export_parser.add_argument("--format", "-f", default="parquet", choices=["parquet", "csv", "json", "xlsx"])
    export_parser.add_argument("--output-dir", "-o", help="Diretório de saída")
    
    # validate
    validate_parser = subparsers.add_parser("validate", help="Valida arquivo contra schema")
    validate_parser.add_argument("file", help="Arquivo a validar")
    validate_parser.add_argument("--schema", "-s", required=True, help="Nome do schema")
    
    # stats
    stats_parser = subparsers.add_parser("stats", help="Estatísticas rápidas de um arquivo")
    stats_parser.add_argument("file", help="Arquivo Parquet/CSV")
    stats_parser.add_argument("--groupby", help="Coluna para agrupar")
    stats_parser.add_argument("--measure", help="Coluna para medir")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    toolkit = BRPublicDataToolkit()
    
    if args.command == "list":
        datasets = toolkit.list_datasets()
        print(f"\n{'ID':<30} {'Fonte':<20} {'Descrição'}")
        print("-" * 80)
        for d in datasets:
            print(f"{d['id']:<30} {d['source']:<20} {d['description']}")
        return
    
    elif args.command == "fetch-sidra":
        overrides = {}
        if args.period: overrides["period"] = args.period
        if args.geo: overrides["geo"] = args.geo
        if args.vars: overrides["variables"] = args.vars.split(",")
        
        df = toolkit.fetch_sidra(args.query_id, **overrides)
        print(f"Linhas: {len(df)}, Colunas: {list(df.columns)}")
        
        if args.output:
            toolkit.export(df, args.output, args.format)
            print(f"Exportado para: {args.output}")
    
    elif args.command == "fetch-pnad":
        kwargs = {}
        if args.vars: kwargs["variables"] = args.vars.split(",")
        if args.classif: 
            # parse "deficiencia:all" -> {"deficiencia": "all"}
            pairs = args.classif.split(",")
            kwargs["classifications"] = {p.split(":")[0]: p.split(":")[1] for p in pairs}
        
        df = toolkit.fetch_pnad(**kwargs)
        print(f"Linhas: {len(df)}, Colunas: {list(df.columns)}")
        
        if args.output:
            toolkit.export(df, args.output, args.format)
            print(f"Exportado para: {args.output}")
    
    elif args.command == "fetch-tse":
        df = toolkit.fetch_tse(args.dataset, year=args.year, uf=args.uf)
        print(f"Linhas: {len(df)}, Colunas: {list(df.columns)}")
        
        if args.output:
            toolkit.export(df, args.output, args.format)
            print(f"Exportado para: {args.output}")
    
    elif args.command == "fetch-datasus":
        df = toolkit.fetch_datasus(args.dataset, cid10=args.cid10, month=args.month)
        print(f"Linhas: {len(df)}, Colunas: {list(df.columns)}")
        
        if args.output:
            toolkit.export(df, args.output, args.format)
            print(f"Exportado para: {args.output}")
    
    elif args.command == "fetch-transparencia":
        df = toolkit.fetch_transparencia(query=args.query, days=args.days)
        print(f"Linhas: {len(df)}, Colunas: {list(df.columns)}")
        
        if args.output:
            toolkit.export(df, args.output, args.format)
            print(f"Exportado para: {args.output}")
    
    elif args.command == "export":
        # Exporta todos os datasets processados
        output_dir = Path(args.output_dir) if args.output_dir else DATA_DIR / "exports" / f"pcd_{datetime.now().strftime('%Y-%m')}"
        toolkit.exporter.export_all(output_dir, args.format)
        print(f"Exportados para: {output_dir}")
    
    elif args.command == "validate":
        result = toolkit.validate(args.file, args.schema)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "stats":
        import pandas as pd
        df = pd.read_parquet(args.file) if args.file.endswith(".parquet") else pd.read_csv(args.file)
        
        if args.groupby and args.measure:
            result = df.groupby(args.groupby)[args.measure].agg(["count", "mean", "sum", "min", "max"])
            print(result.to_string())
        else:
            print(df.describe(include="all").to_string())


if __name__ == "__main__":
    import asyncio
    from datetime import datetime
    import json
    
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Erro: {e}")
        sys.exit(1)