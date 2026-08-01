#!/usr/bin/env python3
"""
Cliente TSE - Eleitores PcD, candidatos PcD, seções acessíveis, voto em trânsito.
Dados abertos TSE + microdados.
"""

import asyncio
import logging
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

from cache import get_cache

logger = logging.getLogger(__name__)


class TSEClient:
    """Cliente para dados abertos TSE."""
    
    BASE_URL = "https://dados.tse.jus.br"
    API_BASE = "https://dadosabertos.tse.jus.br/api/v1"
    
    ENDPOINTS = {
        "eleitores": "/eleitores",
        "candidatos": "/candidatos",
        "secoes": "/secoes",
        "votacao": "/votacao",
        "voto_trânsito": "/voto-transito",
        "acessibilidade": "/acessibilidade",
    }
    
    def __init__(self, cache: Any = None):
        self.cache = cache or get_cache()
        self.client = httpx.AsyncClient(timeout=300, follow_redirects=True)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    async def fetch_eleitores_pcd(
        self,
        year: int = 2024,
        uf: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Busca eleitores com deficiência por UF/município."""
        cache_key = f"tse_eleitores_pcd_{year}_{uf or 'BR'}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)
        
        # TSE disponibiliza CSVs por UF
        url = f"{self.BASE_URL}/dataset/eleitores-2024/resource/eleitores_deficiencia_{year}.csv"
        
        try:
            resp = await self.client.get(url, timeout=120)
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            # Tenta API
            return await self._fetch_eleitores_api(year, uf)
        
        df = pd.read_csv(BytesIO(resp.content), sep=';', encoding='latin1')
        
        if uf:
            df = df[df['SG_UF'] == uf.upper()]
        
        df['year'] = year
        df['dataset'] = 'tse_eleitores_pcd'
        
        self.cache.set(cache_key, df.to_dict('records'), ttl_days=30)
        
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            df.to_parquet(output_dir / f"tse_eleitores_pcd_{year}_{uf or 'BR'}.parquet", index=False)
        
        return df
    
    async def _fetch_eleitores_api(
        self,
        year: int,
        uf: Optional[str],
    ) -> pd.DataFrame:
        """Busca via API paginada."""
        url = f"{self.API_BASE}/eleitores"
        params = {"ano": str(year), "uf": uf or "", "pagina": 1, "tamanho": 10000}
        
        all_data = []
        while True:
            resp = await self.client.get(url, params=params)
            data = resp.json()
            if not data.get('dados'):
                break
            all_data.extend(data['dados'])
            if len(data['dados']) < 10000:
                break
            params['pagina'] += 1
        
        return pd.DataFrame(all_data)
    
    async def fetch_candidatos_pcd(
        self,
        year: int = 2024,
        uf: Optional[str] = None,
        cargo: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Busca candidatos com deficiência."""
        cache_key = f"tse_candidatos_pcd_{year}_{uf or 'BR'}_{cargo or 'ALL'}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)
        
        # TSE microdados candidatos
        url = f"{self.BASE_URL}/dataset/candidatos-{year}/resource/candidatos_deficiencia_{year}.zip"
        
        try:
            resp = await self.client.get(url, timeout=300)
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            return await self._fetch_candidatos_api(year, uf, cargo)
        
        # Extrai ZIP
        dfs = []
        with zipfile.ZipFile(BytesIO(resp.content)) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            for csv_file in csv_files:
                if uf and uf.upper() not in csv_file.upper():
                    continue
                with z.open(csv_file) as f:
                    df = pd.read_csv(f, sep=';', encoding='latin1', low_memory=False)
                    dfs.append(df)
        
        if not dfs:
            return pd.DataFrame()
        
        df = pd.concat(dfs, ignore_index=True)
        
        # Filtra PcD
        pcd_cols = [c for c in df.columns if 'DEFICIENCIA' in c.upper() or 'NECESSIDADE' in c.upper()]
        if pcd_cols:
            mask = df[pcd_cols].notna().any(axis=1)
            df = df[mask]
        
        df['year'] = year
        df['dataset'] = 'tse_candidatos_pcd'
        
        self.cache.set(cache_key, df.to_dict('records'), ttl_days=30)
        
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            df.to_parquet(output_dir / f"tse_candidatos_pcd_{year}_{uf or 'BR'}.parquet", index=False)
        
        return df
    
    async def _fetch_candidatos_api(
        self,
        year: int,
        uf: Optional[str],
        cargo: Optional[str],
    ) -> pd.DataFrame:
        url = f"{self.API_BASE}/candidatos"
        params = {"ano": str(year), "uf": uf or "", "cargo": cargo or ""}
        
        all_data = []
        page = 1
        while True:
            params['pagina'] = page
            resp = await self.client.get(url, params=params)
            data = resp.json()
            if not data.get('dados'):
                break
            all_data.extend(data['dados'])
            if len(data['dados']) < 10000:
                break
        
        return pd.DataFrame(all_data)
    
    async def fetch_secoes_acessiveis(
        self,
        year: int = 2024,
        uf: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Busca seções eleitorais com acessibilidade."""
        cache_key = f"tse_secoes_acessiveis_{year}_{uf or 'BR'}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)
        
        url = f"{self.BASE_URL}/dataset/secoes-eleitorais-{year}/resource/secoes_acessibilidade_{year}.csv"
        
        try:
            resp = await self.client.get(url, timeout=120)
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            # Tenta API
            url = f"{self.API_BASE}/secoes"
            params = {"ano": str(year), "uf": uf or ""}
            resp = await self.client.get(url, params=params)
            data = resp.json()
            df = pd.DataFrame(data.get('dados', []))
        else:
            df = pd.read_csv(BytesIO(resp.content), sep=';', encoding='latin1')
        
        # Filtra acessíveis
        acess_cols = [c for c in df.columns if 'ACESS' in c.upper() or 'ADAPT' in c.upper()]
        if acess_cols:
            mask = df[acess_cols].apply(lambda x: x.astype(str).str.upper().str.contains('SIM|S|1|SIM').any(), axis=1)
            df = df[mask]
        
        df['year'] = year
        df['dataset'] = 'tse_secoes_acessiveis'
        
        self.cache.set(cache_key, df.to_dict('records'), ttl_days=30)
        
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            df.to_parquet(output_dir / f"tse_secoes_acessiveis_{year}_{uf or 'BR'}.parquet", index=False)
        
        return df
    
    async def fetch_voto_transito(
        self,
        year: int = 2024,
        uf: Optional[str] = None,
    ) -> pd.DataFrame:
        """Busca voto em trânsito para PcD."""
        cache_key = f"tse_voto_transito_{year}_{uf or 'BR'}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)
        
        url = f"{self.API_BASE}/voto-transito"
        params = {"ano": str(year), "uf": uf or ""}
        
        resp = await self.client.get(url, params=params)
        data = resp.json()
        
        df = pd.DataFrame(data.get('dados', []))
        df['year'] = year
        df['dataset'] = 'tse_voto_transito'
        
        self.cache.set(cache_key, df.to_dict('records'), ttl_days=30)
        return df
    
    async def fetch_dados_gerais_eleicao(
        self,
        year: int = 2024,
    ) -> Dict[str, Any]:
        """Busca estatísticas gerais da eleição."""
        url = f"{self.API_BASE}/estatisticas"
        params = {"ano": str(year)}
        
        resp = await self.client.get(url, params=params)
        return resp.json()


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="TSE Client")
    parser.add_argument("--dataset", choices=["eleitores", "candidatos", "secoes", "voto_transito", "estatisticas"], required=True)
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--uf", help="UF (ex: SP, RJ)")
    parser.add_argument("--cargo", help="Cargo (ex: DEPUTADO FEDERAL)")
    parser.add_argument("--output", "-o", type=str, help="Arquivo Parquet de saída")
    args = parser.parse_args()
    
    async with TSEClient() as client:
        if args.dataset == "eleitores":
            df = await client.fetch_eleitores_pcd(args.year, args.uf)
        elif args.dataset == "candidatos":
            df = await client.fetch_candidatos_pcd(args.year, args.uf, args.cargo)
        elif args.dataset == "secoes":
            df = await client.fetch_secoes_acessiveis(args.year, args.uf)
        elif args.dataset == "voto_transito":
            df = await client.fetch_voto_transito(args.year, args.uf)
        elif args.dataset == "estatisticas":
            result = await client.fetch_dados_gerais_eleicao(args.year)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        else:
            df = pd.DataFrame()
        
        print(f"Linhas: {len(df)}, Colunas: {len(df.columns)}")
        if not df.empty:
            print(df.head(3).to_string())
            
            if args.output:
                df.to_parquet(args.output, index=False)
                print(f"Salvo em: {args.output}")


if __name__ == "__main__":
    import json
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())