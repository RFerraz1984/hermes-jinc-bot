#!/usr/bin/env python3
"""
Cliente PNAD Contínua - mercado de trabalho PcD trimestral.
Usa IBGE SIDRA tabelas 6389+.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ibge_sidra import SIDRAClient
from cache import get_cache

logger = logging.getLogger(__name__)


class PNADContinuaClient:
    """Cliente para PNAD Contínua via SIDRA."""
    
    # Tabelas SIDRA relevantes para PcD
    TABLES = {
        "trabalho_pcd": 6389,      # Pessoas com deficiência no mercado de trabalho
        "trabalho_geral": 6388,    # Mercado de trabalho geral (comparação)
        "rendimento_pcd": 6390,    # Rendimento PcD
        "informalidade_pcd": 6391, # Informalidade PcD
    }
    
    # Variáveis comuns
    VARS = {
        "total": 93,           # Total
        "ocupado": 6941,       # Ocupado
        "desocupado": 6942,    # Desocupado
        "fora_forca": 6943,    # Fora da força de trabalho
        "rendimento": 6944,    # Rendimento médio
        "informal": 6945,      # Informalidade
    }
    
    # Classificações
    CLASSIFICATIONS = {
        "deficiencia": "11046",  # Tipo de deficiência
        "idade": "227",          # Grupos de idade
        "sexo": "86",            # Sexo
        "cor": "292",            # Cor/raça
        "uf": "1",               # UF (geo=6)
        "brasil": "1",           # Brasil (geo=1)
    }
    
    def __init__(self, cache: Any = None):
        self.cache = cache or get_cache()
        self.sidra = SIDRAClient(self.cache)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.sidra.__aexit__(*args)
    
    async def fetch_latest(
        self,
        variables: List[int] = None,
        classifications: Dict[str, str] = None,
        geo: str = "1",  # 1=Brasil, 6=UF
        period: str = "last",
    ) -> pd.DataFrame:
        """Busca último trimestre disponível."""
        variables = variables or [self.VARS["total"], self.VARS["ocupado"], self.VARS["desocupado"], self.VARS["fora_forca"]]
        classifications = classifications or {"11046": "all"}  # tipo deficiência
        
        # Tabela principal: trabalho PcD
        df = await self.sidra.query(
            table=self.TABLES["trabalho_pcd"],
            variables=variables,
            period=period,
            classifications=classifications,
            geo=geo,
        )
        
        # Adiciona metadados
        df["dataset"] = "pnad_continua"
        df["table"] = "trabalho_pcd"
        df["periodo"] = period
        
        return df
    
    async def fetch_historical(
        self,
        years: List[int] = None,
        variables: List[int] = None,
        geo: str = "1",
    ) -> pd.DataFrame:
        """Busca série histórica anual."""
        years = years or list(range(2016, 2025))
        variables = variables or [self.VARS["total"], self.VARS["ocupado"], self.VARS["desocupado"]]
        
        period = ",".join(str(y) for y in years)
        
        df = await self.sidra.query(
            table=self.TABLES["trabalho_pcd"],
            variables=variables,
            period=period,
            classifications={"11046": "all"},
            geo=geo,
        )
        
        df["dataset"] = "pnad_continua"
        df["table"] = "trabalho_pcd_historico"
        
        return df
    
    async def fetch_by_uf(
        self,
        variables: List[int] = None,
        period: str = "last",
    ) -> pd.DataFrame:
        """Busca dados por UF (geo=6)."""
        return await self.fetch_latest(variables=variables, geo="6", period=period)
    
    async def fetch_rendimento(
        self,
        period: str = "last",
        geo: str = "1",
    ) -> pd.DataFrame:
        """Busca rendimento médio PcD."""
        return await self.sidra.query(
            table=self.TABLES["rendimento_pcd"],
            variables=[self.VARS["rendimento"]],
            period=period,
            classifications={"11046": "all"},
            geo=geo,
        )
    
    async def fetch_informalidade(
        self,
        period: str = "last",
        geo: str = "1",
    ) -> pd.DataFrame:
        """Busca informalidade PcD."""
        return await self.sidra.query(
            table=self.TABLES["informalidade_pcd"],
            variables=[self.VARS["informal"]],
            period=period,
            classifications={"11046": "all"},
            geo=geo,
        )
    
    async def fetch_comparison_geral(
        self,
        period: str = "last",
        geo: str = "1",
    ) -> pd.DataFrame:
        """Busca mercado de trabalho geral (sem filtro deficiência) para comparação."""
        return await self.sidra.query(
            table=self.TABLES["trabalho_geral"],
            variables=[self.VARS["total"], self.VARS["ocupado"], self.VARS["desocupado"]],
            period=period,
            geo=geo,
        )


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="PNAD Contínua Client")
    parser.add_argument("--output", "-o", type=str, help="Arquivo Parquet de saída")
    parser.add_argument("--geo", default="1", choices=["1", "6"], help="1=Brasil, 6=UF")
    parser.add_argument("--historical", action="store_true", help="Série histórica")
    parser.add_argument("--rendimento", action="store_true", help="Rendimento médio")
    parser.add_argument("--informalidade", action="store_true", help="Taxa de informalidade")
    parser.add_argument("--comparison", action="store_true", help="Comparação mercado geral")
    parser.add_argument("--by-uf", action="store_true", help="Dados por UF")
    args = parser.parse_args()
    
    async with PNADContinuaClient() as client:
        if args.historical:
            df = await client.fetch_historical(geo=args.geo)
        elif args.rendimento:
            df = await client.fetch_rendimento(geo=args.geo)
        elif args.informalidade:
            df = await client.fetch_informalidade(geo=args.geo)
        elif args.comparison:
            df = await client.fetch_comparison_geral(geo=args.geo)
        elif args.by_uf:
            df = await client.fetch_by_uf(geo=args.geo)
        else:
            df = await client.fetch_latest(geo=args.geo)
        
        print(f"Linhas: {len(df)}, Colunas: {list(df.columns)}")
        print(df.head(10).to_string())
        
        if args.output:
            df.to_parquet(args.output, index=False)
            print(f"Salvo em: {args.output}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())