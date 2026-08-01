#!/usr/bin/env python3
"""
Cliente INEP - Censo Escolar, ENEM, Censo Superior.
Microdados + agregados para indicadores PcD/AEE.
"""

import asyncio
import logging
import os
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

from cache import get_cache

logger = logging.getLogger(__name__)


class INEPClient:
    """Cliente para microdados INEP."""
    
    BASE_URL = "https://download.inep.gov.br"
    
    # Datasets disponíveis
    DATASETS = {
        "censo_escolar": {
            "name": "Censo Escolar",
            "years": list(range(2007, 2025)),
            "url_pattern": "/dados_abertos/microdados/microdados_censo_escolar_{year}.zip",
            "pcd_indicators": ["IN_AEE", "IN_ESPECIAL", "IN_REGULAR", "IN_EJA", "IN_PROFISSIONAL"],
        },
        "enem": {
            "name": "ENEM",
            "years": list(range(1998, 2025)),
            "url_pattern": "/dados_abertos/microdados/microdados_enem_{year}.zip",
            "pcd_indicators": ["IN_DEFICIENCIA", "TP_PRESENCA", "TP_STATUS_REDACAO"],
        },
        "censo_superior": {
            "name": "Censo da Educação Superior",
            "years": list(range(2009, 2024)),
            "url_pattern": "/dados_abertos/microdados/microdados_censo_da_educacao_superior_{year}.zip",
            "pcd_indicators": ["IN_DEFICIENCIA", "IN_NECESSIDADE_ESPECIAL"],
        },
        "ideb": {
            "name": "IDEB",
            "years": [2005, 2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021, 2023],
            "url_pattern": "/dados_abertos/indicadores/ideb_{year}.zip",
        },
        "prova_brasil": {
            "name": "Prova Brasil / SAEB",
            "years": [2005, 2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021, 2023],
            "url_pattern": "/dados_abertos/saeb/microdados_saeb_{year}.zip",
        },
    }
    
    def __init__(self, cache: Any = None):
        self.cache = cache or get_cache()
        self.client = httpx.AsyncClient(timeout=600, follow_redirects=True)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    def _get_url(self, dataset: str, year: int) -> str:
        """Constrói URL do dataset."""
        pattern = self.DATASETS[dataset]["url_pattern"]
        return f"{self.BASE_URL}{pattern.format(year=year)}"
    
    async def fetch_dataset(
        self,
        dataset: str,
        year: int,
        output_dir: Optional[Path] = None,
        filter_pcd: bool = True,
    ) -> pd.DataFrame:
        """
        Baixa e processa dataset INEP.
        
        Args:
            dataset: Nome do dataset (censo_escolar, enem, censo_superior, ideb, prova_brasil)
            year: Ano
            output_dir: Diretório para salvar CSVs extraídos
            filter_pcd: Se True, filtra apenas indicadores PcD/AEE
        """
        if dataset not in self.DATASETS:
            raise ValueError(f"Dataset desconhecido: {dataset}")
        
        if year not in self.DATASETS[dataset]["years"]:
            raise ValueError(f"Ano {year} não disponível para {dataset}")
        
        url = self._get_url(dataset, year)
        logger.info(f"Baixando {dataset} {year}: {url}")
        
        # Cache key
        cache_key = f"inep_{dataset}_{year}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit")
            return pd.DataFrame(cached)
        
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Arquivo não encontrado: {url}")
                return pd.DataFrame()
            raise
        
        # Extrai ZIP
        df = await self._extract_zip(resp.content, dataset, year, output_dir, filter_pcd)
        
        if not df.empty:
            self.cache.set(cache_key, df.to_dict("records"), ttl_days=30)
        
        return df
    
    async def _extract_zip(
        self,
        content: bytes,
        dataset: str,
        year: int,
        output_dir: Optional[Path],
        filter_pcd: bool,
    ) -> pd.DataFrame:
        """Extrai ZIP e processa CSVs."""
        dfs = []
        
        with zipfile.ZipFile(BytesIO(content)) as z:
            # Lista arquivos CSV/DAT
            data_files = [f for f in z.namelist() if f.endswith(('.csv', '.CSV', '.dat', '.DAT', '.txt', '.TXT'))]
            
            for file_name in data_files:
                logger.debug(f"Processando {file_name}")
                
                with z.open(file_name) as f:
                    content_bytes = f.read()
                    
                    # Tenta detectar encoding
                    for encoding in ['latin1', 'utf-8', 'cp1252']:
                        try:
                            text = content_bytes.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        text = content_bytes.decode('latin1', errors='replace')
                    
                    # Detecta separador
                    sample = text[:1000]
                    if ';' in sample and sample.count(';') > sample.count(','):
                        sep = ';'
                    elif '\t' in sample:
                        sep = '\t'
                    else:
                        sep = ','
                    
                    try:
                        df = pd.read_csv(
                            BytesIO(content_bytes),
                            encoding=encoding,
                            sep=sep,
                            low_memory=False,
                        )
                        
                        # Filtra PcD se solicitado
                        if filter_pcd and dataset in self.DATASETS:
                            pcd_cols = self.DATASETS[dataset].get("pcd_indicators", [])
                            mask = False
                            for col in pcd_cols:
                                if col in df.columns:
                                    mask = mask | df[col].notna()
                            
                            if mask.any():
                                df = df[mask]
                        
                        df["source_file"] = file_name
                        df["dataset"] = dataset
                        df["year"] = year
                        dfs.append(df)
                        
                        # Salva CSV se output_dir
                        if output_dir:
                            output_dir.mkdir(parents=True, exist_ok=True)
                            safe_name = re.sub(r'[^\w\-_]', '_', file_name)
                            df.to_csv(output_dir / f"{dataset}_{year}_{safe_name}", index=False, sep=';')
                            
                    except Exception as e:
                        logger.warning(f"Erro processando {file_name}: {e}")
                        continue
        
        if dfs:
            result = pd.concat(dfs, ignore_index=True)
            logger.info(f"Total linhas: {len(result)} de {len(dfs)} arquivos")
            return result
        
        return pd.DataFrame()
    
    async def fetch_censo_escolar_aee(
        self,
        year: int = 2023,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Busca escolas com AEE (Atendimento Educacional Especializado)."""
        df = await self.fetch_dataset("censo_escolar", year, output_dir)
        
        if df.empty:
            return df
        
        # Filtra escolas com AEE
        aee_cols = [c for c in df.columns if 'AEE' in c.upper() or 'ESPECIAL' in c.upper()]
        
        if aee_cols:
            mask = df[aee_cols].notna().any(axis=1)
            df_aee = df[mask].copy()
            logger.info(f"Escolas com AEE: {len(df_aee)} de {len(df)}")
            return df_aee
        
        return df
    
    async def fetch_enem_pcd(
        self,
        year: int = 2023,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Busca microdados ENEM filtrando PcD."""
        df = await self.fetch_dataset("enem", year, output_dir)
        
        if df.empty:
            return df
        
        # Filtra candidatos com deficiência
        pcd_cols = [c for c in df.columns if 'DEFICIENCIA' in c.upper() or 'NECESSIDADE' in c.upper()]
        
        if pcd_cols:
            mask = df[pcd_cols].notna().any(axis=1)
            df_pcd = df[mask].copy()
            logger.info(f"Candidatos ENEM PcD: {len(df_pcd)} de {len(df)}")
            return df_pcd
        
        return df
    
    async def fetch_censo_superior_pcd(
        self,
        year: int = 2022,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Busca Censo Superior filtrando PcD."""
        df = await self.fetch_dataset("censo_superior", year, output_dir)
        
        if df.empty:
            return df
        
        pcd_cols = [c for c in df.columns if 'DEFICIENCIA' in c.upper() or 'NECESSIDADE' in c.upper()]
        
        if pcd_cols:
            mask = df[pcd_cols].notna().any(axis=1)
            df_pcd = df[mask].copy()
            logger.info(f"Matrículas Censo Superior PcD: {len(df_pcd)} de {len(df)}")
            return df_pcd
        
        return df


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="INEP Client")
    parser.add_argument("--dataset", choices=["censo_escolar", "enem", "censo_superior", "ideb", "prova_brasil"], required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output", "-o", type=str, help="Diretório de saída")
    parser.add_argument("--no-filter", action="store_true", help="Não filtrar PcD")
    args = parser.parse_args()
    
    async with INEPClient() as client:
        df = await client.fetch_dataset(
            args.dataset, 
            args.year, 
            Path(args.output) if args.output else None,
            filter_pcd=not args.no_filter
        )
        
        print(f"Linhas: {len(df)}, Colunas: {len(df.columns)}")
        if not df.empty:
            print(df.head(3).to_string())
            
            if args.output:
                out_path = Path(args.output) / f"inep_{args.dataset}_{args.year}.parquet"
                df.to_parquet(out_path, index=False)
                print(f"Salvo em: {out_path}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())