#!/usr/bin/env python3
"""
Cliente PNS (Pesquisa Nacional de Saúde) - deficiência funcional, limitação, uso de serviços.
Usa IBGE SIDRA tabelas 6579+.
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ibge_sidra import SIDRAClient
from cache import get_cache

logger = logging.getLogger(__name__)


class PNSClient:
    """Cliente para PNS via SIDRA."""
    
    TABLES = {
        "limitacao_funcional": 6579,  # Limitação funcional por grau
        "deficiencia": 6580,          # Deficiência por tipo
        "uso_servicos": 6581,         # Uso de serviços de saúde
        "reabilitacao": 6582,         # Reabilitação
        "medicamentos": 6583,         # Uso de medicamentos
        "acesso": 6584,               # Acesso a serviços
    }
    
    VARS = {
        "total": 93,
        "grau_leve": 6578,
        "grau_moderado": 6579,
        "grau_grave": 6580,
        "grau_muito_grave": 6581,
    }
    
    CLASSIFICATIONS = {
        "tipo_deficiencia": "11046",
        "grau_limitacao": "11047",
        "idade": "227",
        "sexo": "86",
        "uf": "1",
    }
    
    def __init__(self, cache: Any = None):
        self.cache = cache or get_cache()
        self.sidra = SIDRAClient(self.cache)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.sidra.__aexit__(*args)
    
    async def fetch_limitacao_funcional(
        self,
        period: str = "2019",
        geo: str = "1",
        grau: str = "all",
    ) -> Any:
        """Limitação funcional por grau (leve, moderado, grave, muito grave)."""
        return await self.sidra.query(
            table=self.TABLES["limitacao_funcional"],
            variables=[self.VARS["total"], self.VARS["grau_leve"], self.VARS["grau_moderado"], self.VARS["grau_grave"], self.VARS["grau_muito_grave"]],
            period=period,
            classifications={"11047": grau},  # grau de limitação
            geo=geo,
        )
    
    async def fetch_deficiencia_tipo(
        self,
        period: str = "2019",
        geo: str = "1",
    ) -> Any:
        """Deficiência por tipo (visual, auditiva, física, intelectual)."""
        return await self.sidra.query(
            table=self.TABLES["deficiencia"],
            variables=[self.VARS["total"]],
            period=period,
            classifications={"11046": "all"},  # tipo de deficiência
            geo=geo,
        )
    
    async def fetch_uso_servicos(
        self,
        period: str = "2019",
        geo: str = "1",
    ) -> Any:
        """Uso de serviços de saúde por PcD."""
        return await self.sidra.query(
            table=self.TABLES["uso_servicos"],
            variables=[93],  # total
            period=period,
            classifications={"11046": "all"},
            geo=geo,
        )
    
    async def fetch_reabilitacao(
        self,
        period: str = "2019",
        geo: str = "1",
    ) -> Any:
        """Necessidade e acesso a reabilitação."""
        return await self.sidra.query(
            table=self.TABLES["reabilitacao"],
            variables=[93],
            period=period,
            classifications={"11046": "all"},
            geo=geo,
        )
    
    async def fetch_acesso_servicos(
        self,
        period: str = "2019",
        geo: str = "1",
    ) -> Any:
        """Acesso a serviços de saúde."""
        return await self.sidra.query(
            table=self.TABLES["acesso"],
            variables=[93],
            period=period,
            classifications={"11046": "all"},
            geo=geo,
        )


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="PNS Client")
    parser.add_argument("--output", "-o", type=str, help="Arquivo Parquet de saída")
    parser.add_argument("--geo", default="1", choices=["1", "6"])
    parser.add_argument("--period", default="2019")
    parser.add_argument("--table", choices=["limitacao", "deficiencia", "servicos", "reabilitacao", "acesso"], default="limitacao")
    args = parser.parse_args()
    
    async with PNSClient() as client:
        if args.table == "limitacao":
            df = await client.fetch_limitacao_funcional(period=args.period, geo=args.geo)
        elif args.table == "deficiencia":
            df = await client.fetch_deficiencia_tipo(period=args.period, geo=args.geo)
        elif args.table == "servicos":
            df = await client.fetch_uso_servicos(period=args.period, geo=args.geo)
        elif args.table == "reabilitacao":
            df = await client.fetch_reabilitacao(period=args.period, geo=args.geo)
        elif args.table == "acesso":
            df = await client.fetch_acesso_servicos(period=args.period, geo=args.geo)
        
        print(f"Linhas: {len(df)}, Colunas: {list(df.columns)}")
        print(df.head(10).to_string())
        
        if args.output:
            df.to_parquet(args.output, index=False)
            print(f"Salvo em: {args.output}")


if __name__ == "__main__":
    import asyncio
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())