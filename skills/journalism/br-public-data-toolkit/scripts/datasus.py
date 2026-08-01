#!/usr/bin/env python3
"""
Cliente DATASUS - SIH (internações), SIA (ambulatorial), CNES (estabelecimentos).
FTP + API para dados de saúde PcD.
"""

import asyncio
import logging
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import httpx

from cache import get_cache

logger = logging.getLogger(__name__)


class DATASUSClient:
    """Cliente para DATASUS (SIH, SIA, CNES)."""
    
    # URLs base
    FTP_BASE = "https://ftp.datasus.gov.br/dissemin/publicos"
    API_BASE = "https://apidatasus.saude.gov.br"
    
    # CID-10 capítulos relevantes para PcD
    CID10_PCD = {
        "Q00-Q99": "Malformações congênitas, deformidades e anomalias cromossômicas",
        "G80-G83": "Paralisia cerebral e outras doenças paralíticas",
        "F70-F79": "Transtornos do desenvolvimento intelectual",
        "F80-F89": "Transtornos do desenvolvimento psicológico",
        "H90-H94": "Perda auditiva",
        "H54": "Cegueira e baixa visão",
        "S00-T98": "Lesões, envenenamentos e outras consequências de causas externas",
    }
    
    # UFs para download
    UFS = [
        "RO", "AC", "AM", "RR", "PA", "AP", "TO",
        "MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA",
        "MG", "ES", "RJ", "SP",
        "PR", "SC", "RS",
        "MS", "MT", "GO", "DF"
    ]
    
    def __init__(self, cache: Any = None):
        self.cache = cache or get_cache()
        self.client = httpx.AsyncClient(timeout=300, follow_redirects=True)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    async def fetch_sih(
        self,
        uf: str,
        year: int,
        month: int,
        cid10_filter: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Busca SIH (internações hospitalares) por UF/mês.
        Formato: RD{UF}{AA}{MM}.dbc
        """
        uf = uf.upper()
        year_str = str(year)[-2:]
        month_str = f"{month:02d}"
        
        filename = f"RD{uf}{year_str}{month_str}.dbc"
        url = f"{self.FTP_BASE}/SIHSUS/200801_/Dados/{filename}"
        
        logger.info(f"Baixando SIH: {url}")
        
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Arquivo não encontrado: {url}")
                return pd.DataFrame()
            raise
        
        # Lê DBC (formato DBF comprimido)
        df = self._read_dbc(resp.content)
        
        if cid10_filter:
            df = self._filter_cid10(df, cid10_filter)
        
        df["uf"] = uf
        df["year"] = year
        df["month"] = month
        df["dataset"] = "sih"
        
        return df
    
    async def fetch_sih_state_year(
        self,
        uf: str,
        year: int,
        cid10_filter: Optional[str] = None,
    ) -> pd.DataFrame:
        """Busca todos os meses de um ano para uma UF."""
        dfs = []
        for month in range(1, 13):
            df = await self.fetch_sih(uf, year, month, cid10_filter)
            if not df.empty:
                dfs.append(df)
        
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()
    
    async def fetch_sia(
        self,
        uf: str,
        year: int,
        month: int,
    ) -> pd.DataFrame:
        """
        Busca SIA (atendimentos ambulatoriais).
        Formato: PA{UF}{AA}{MM}.dbc
        """
        uf = uf.upper()
        year_str = str(year)[-2:]
        month_str = f"{month:02d}"
        
        filename = f"PA{uf}{year_str}{month_str}.dbc"
        url = f"{self.FTP_BASE}/SIASUS/200801_/Dados/{filename}"
        
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return pd.DataFrame()
            raise
        
        df = self._read_dbc(resp.content)
        df["uf"] = uf
        df["year"] = year
        df["month"] = month
        df["dataset"] = "sia"
        
        return df
    
    async def fetch_cnes(
        self,
        year: int,
        month: int,
    ) -> pd.DataFrame:
        """
        Busca CNES (cadastro de estabelecimentos).
        Formato: LT{AA}{MM}.dbc (nacional)
        """
        year_str = str(year)[-2:]
        month_str = f"{month:02d}"
        
        filename = f"LT{year_str}{month_str}.dbc"
        url = f"{self.FTP_BASE}/CNES/200801_/Dados/{filename}"
        
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return pd.DataFrame()
            raise
        
        df = self._read_dbc(resp.content)
        df["year"] = year
        df["month"] = month
        df["dataset"] = "cnes"
        
        return df
    
    def _read_dbc(self, content: bytes) -> pd.DataFrame:
        """Lê arquivo DBC (DBF comprimido com LZMA)."""
        try:
            # DBC é DBF comprimido com LZMA
            import lzma
            
            # Tenta descomprimir
            decompressed = lzma.decompress(content)
            
            # Lê DBF
            from dbfread import DBF
            from io import BytesIO
            
            dbf = DBF(BytesIO(decompressed), load=True, encoding='latin1')
            records = list(dbf)
            return pd.DataFrame(records)
            
        except Exception as e:
            logger.warning(f"Erro lendo DBC, tentando como DBF direto: {e}")
            try:
                from dbfread import DBF
                from io import BytesIO
                dbf = DBF(BytesIO(content), load=True, encoding='latin1')
                return pd.DataFrame(list(dbf))
            except Exception as e2:
                logger.error(f"Falha lendo DBC/DBF: {e2}")
                return pd.DataFrame()
    
    def _filter_cid10(self, df: pd.DataFrame, cid10_filter: str) -> pd.DataFrame:
        """Filtra por CID-10 (DIAG_PRINC ou similar)."""
        # Colunas comuns de diagnóstico no SIH/SIA
        diag_cols = [c for c in df.columns if 'DIAG' in c.upper() or 'CID' in c.upper()]
        
        if not diag_cols:
            return df
        
        # Cria máscara combinada
        mask = False
        for col in diag_cols:
            if col in df.columns:
                mask = mask | df[col].astype(str).str.upper().str.startswith(cid10_filter.upper())
        
        return df[mask]
    
    async def fetch_latest_month(
        self,
        cid10_filter: Optional[str] = None,
    ) -> pd.DataFrame:
        """Busca mês mais recente disponível para todas UFs."""
        # Tenta mês atual, se falha vai voltando
        from datetime import datetime
        now = datetime.now()
        
        for i in range(6):  # tenta últimos 6 meses
            year = now.year
            month = now.month - i
            if month <= 0:
                month += 12
                year -= 1
            
            dfs = []
            for uf in self.UFS:
                df = await self.fetch_sih(uf, year, month, cid10_filter)
                if not df.empty:
                    dfs.append(df)
            
            if dfs:
                logger.info(f"Encontrado dados SIH para {year}-{month:02d} ({len(dfs)} UFs)")
                return pd.concat(dfs, ignore_index=True)
        
        return pd.DataFrame()


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="DATASUS Client")
    parser.add_argument("--output", "-o", type=str, help="Arquivo Parquet de saída")
    parser.add_argument("--uf", help="UF específica (ex: SP, RJ)")
    parser.add_argument("--year", type=int, help="Ano")
    parser.add_argument("--month", type=int, help="Mês")
    parser.add_argument("--cid10", help="Filtro CID-10 (ex: Q, G80, F70)")
    parser.add_argument("--latest", action="store_true", help="Último mês disponível")
    args = parser.parse_args()
    
    async with DATASUSClient() as client:
        if args.latest:
            df = await client.fetch_latest_month(cid10_filter=args.cid10)
        elif args.uf and args.year and args.month:
            df = await client.fetch_sih(args.uf, args.year, args.month, cid10_filter=args.cid10)
        elif args.uf and args.year:
            df = await client.fetch_sih_state_year(args.uf, args.year, cid10_filter=args.cid10)
        else:
            parser.print_help()
            return
        
        print(f"Linhas: {len(df)}, Colunas: {list(df.columns)}")
        print(df.head(5).to_string())
        
        if args.output:
            df.to_parquet(args.output, index=False)
            print(f"Salvo em: {args.output}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())