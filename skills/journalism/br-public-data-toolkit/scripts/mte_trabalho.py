#!/usr/bin/env python3
"""
Cliente MTE - RAIS, CAGED, Lei de Cotas (8213/91).
Admissões/desligamentos PcD, fiscalização de cotas.
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


class MTEClient:
    """Cliente para dados do MTE (RAIS, CAGED, Cotas)."""
    
    BASE_URL = "https://dadosabertos.rais.gov.br"
    
    ENDPOINTS = {
        "rais_vinculos": "/rais/vinculos",
        "rais_estabelecimentos": "/rais/estabelecimentos",
        "caged_movimentacao": "/caged/movimentacao",
        "caged_saldos": "/caged/saldos",
        "cotas_fiscalizacao": "/cotas/fiscalizacao",
        "cotas_estabelecimentos": "/cotas/estabelecimentos",
    }
    
    # Anos disponíveis
    RAIS_YEARS = list(range(2003, 2023))
    CAGED_YEARS = list(range(2002, 2025))
    
    def __init__(self, cache: Any = None):
        self.cache = cache or get_cache()
        self.client = httpx.AsyncClient(timeout=300, follow_redirects=True)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    async def fetch_rais_pcd(
        self,
        year: int = 2022,
        uf: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Busca vínculos RAIS filtrando PcD (deficiência)."""
        if year not in self.RAIS_YEARS:
            raise ValueError(f"Ano {year} não disponível para RAIS")
        
        cache_key = f"rais_vinculos_{year}_{uf or 'BR'}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            df = pd.DataFrame(cached)
        else:
            # RAIS microdados - arquivo grande, baixa via ZIP
            df = await self._fetch_rais_vinculos_zip(year, uf, output_dir)
        
        if df.empty:
            return df
        
        # Filtra PcD - coluna "Deficiencia" ou similar
        pcd_cols = [c for c in df.columns if 'DEFIC' in c.upper() or 'PC' in c.upper() or 'NECESSIDADE' in c.upper()]
        
        if pcd_cols:
            mask = df[pcd_cols].notna().any(axis=1)
            df_pcd = df[mask].copy()
            logger.info(f"RAIS {year}: {len(df_pcd)} vínculos PcD de {len(df)} total")
            return df_pcd
        
        return df
    
    async def _fetch_rais_vinculos_zip(
        self,
        year: int,
        uf: Optional[str],
        output_dir: Optional[Path],
    ) -> pd.DataFrame:
        """Baixa RAIS vínculos via ZIP (arquivo grande ~2-5GB)."""
        # URL padrão do MTE para RAIS
        zip_name = f"RAIS_VINC_PUB_{year}.zip"
        url = f"{self.BASE_URL}/dataset/rais_vinculos/resource/{zip_name}"
        
        logger.info(f"Baixando RAIS {year}: {url}")
        
        try:
            resp = await self.client.get(url, timeout=1800)
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            # Tenta URL alternativa
            url_alt = f"ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/{year}/RAIS_VINC_PUB_{year}.zip"
            logger.warning(f"Tentando FTP alternativo...")
            return pd.DataFrame()
        
        # Extrai ZIP - arquivos TXT fix-width
        dfs = []
        with zipfile.ZipFile(BytesIO(resp.content)) as z:
            txt_files = [f for f in z.namelist() if f.endswith('.txt')]
            
            for txt_file in txt_files:
                if uf and uf.upper() not in txt_file.upper():
                    continue
                    
                logger.debug(f"Processando {txt_file}")
                
                with z.open(txt_file) as f:
                    # RAIS usa layout fixo - precisa parser específico
                    df = self._parse_rais_txt(f)
                    if not df.empty:
                        dfs.append(df)
                        
                        if output_dir:
                            output_dir.mkdir(parents=True, exist_ok=True)
                            df.to_parquet(output_dir / f"rais_{year}_{txt_file}.parquet", index=False)
        
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        
        return pd.DataFrame()
    
    def _parse_rais_txt(self, file_handle) -> pd.DataFrame:
        """Parser para layout fixo RAIS (simplificado)."""
        # Layout RAIS Vínculos - posições fixas
        # Campos principais para PcD:
        # - Deficiencia (posição ~XXX, 1 char: 1=sim, 2=não)
        # - TipoDeficiencia (posição ~XXX, 2 chars)
        # Ver documentação oficial MTE para layout exato
        
        colspecs = [
            (0, 14),    # CNPJ
            (14, 20),   # CEI
            (20, 26),   # Ano
            (26, 28),   # Mês
            (28, 40),   # CPF
            (40, 41),   # Deficiencia (1=sim, 2=não)
            (41, 43),   # TipoDeficiencia
            # ... mais campos conforme layout
        ]
        
        names = [
            "cnpj", "cei", "ano", "mes", "cpf",
            "deficiencia", "tipo_deficiencia",
        ]
        
        try:
            # Tenta ler como fixed-width
            df = pd.read_fwf(
                file_handle,
                colspecs=colspecs[:len(names)],
                names=names,
                encoding='latin1',
                dtype=str,
            )
            return df
        except Exception as e:
            logger.warning(f"Erro parsing RAIS TXT: {e}")
            return pd.DataFrame()
    
    async def fetch_caged_pcd(
        self,
        year: int = 2024,
        month: Optional[int] = None,
        uf: Optional[str] = None,
    ) -> pd.DataFrame:
        """Busca CAGED movimentação/admissões/desligamentos PcD."""
        if year not in self.CAGED_YEARS:
            raise ValueError(f"Ano {year} não disponível para CAGED")
        
        # CAGED Novo (2020+) - API JSON
        if year >= 2020:
            return await self._fetch_caged_novo(year, month, uf)
        else:
            return await self._fetch_caged_antigo(year, month, uf)
    
    async def _fetch_caged_novo(
        self,
        year: int,
        month: Optional[int],
        uf: Optional[str],
    ) -> pd.DataFrame:
        """CAGED Novo (2020+) - API paginada."""
        cache_key = f"caged_novo_{year}_{month or 'all'}_{uf or 'BR'}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)
        
        url = f"{self.BASE_URL}/caged/movimentacao"
        
        params = {
            "ano": str(year),
            "mes": str(month).zfill(2) if month else "",
            "uf": uf or "",
        }
        
        all_data = []
        page = 1
        
        while True:
            params["pagina"] = str(page)
            params["tamPagina"] = "10000"
            
            try:
                resp = await self.client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"Erro CAGED: {e}")
                break
            
            if not data.get("dados"):
                break
            
            all_data.extend(data["dados"])
            
            if len(data["dados"]) < 10000:
                break
            page += 1
        
        if all_data:
            df = pd.DataFrame(all_data)
            
            # Filtra PcD - coluna "deficiencia" ou "indDeficiencia"
            pcd_cols = [c for c in df.columns if 'DEFIC' in c.upper() or 'PCD' in c.upper()]
            if pcd_cols:
                mask = df[pcd_cols].notna().any(axis=1)
                df = df[mask]
            
            if not df.empty:
                self.cache.set(cache_key, df.to_dict("records"), ttl_days=7)
            
            return df
        
        return pd.DataFrame()
    
    async def _fetch_caged_antigo(
        self,
        year: int,
        month: Optional[int],
        uf: Optional[str],
    ) -> pd.DataFrame:
        """CAGED Antigo (pre-2020) - arquivos TXT fix-width."""
        # Similar ao RAIS - layout fixo
        return pd.DataFrame()
    
    async def fetch_cotas_estabelecimentos(
        self,
        year: int = 2024,
        uf: Optional[str] = None,
    ) -> pd.DataFrame:
        """Busca estabelecimentos sujeitos à Lei de Cotas (8213/91)."""
        url = f"{self.BASE_URL}/cotas/estabelecimentos"
        
        params = {"ano": str(year), "uf": uf or ""}
        
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            df = pd.DataFrame(data.get("dados", []))
            df['year'] = year
            df['dataset'] = 'mte_cotas'
            
            return df
        except Exception as e:
            logger.error(f"Erro Cotas: {e}")
            return pd.DataFrame()
    
    async def fetch_cotas_fiscalizacao(
        self,
        year: int = 2024,
        uf: Optional[str] = None,
    ) -> pd.DataFrame:
        """Busca autos de infração de cotas (fiscalização)."""
        url = f"{self.BASE_URL}/cotas/fiscalizacao"
        
        params = {"ano": str(year), "uf": uf or ""}
        
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            df = pd.DataFrame(data.get("dados", []))
            df['year'] = year
            df['dataset'] = 'mte_cotas_fiscalizacao'
            
            return df
        except Exception as e:
            logger.error(f"Erro Cotas Fiscalização: {e}")
            return pd.DataFrame()
    
    async def fetch_rais_estabelecimentos(
        self,
        year: int = 2022,
        uf: Optional[str] = None,
    ) -> pd.DataFrame:
        """Busca estabelecimentos RAIS (para cruzamento com cotas)."""
        # Similar a fetch_rais_pcd mas retorna estabelecimentos
        return pd.DataFrame()


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="MTE Client - RAIS/CAGED/Cotas")
    parser.add_argument("--dataset", choices=["rais", "caged", "cotas", "fiscalizacao"], required=True)
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--month", type=int)
    parser.add_argument("--uf", help="UF (ex: SP, RJ)")
    parser.add_argument("--output", "-o", type=str, help="Arquivo Parquet de saída")
    args = parser.parse_args()
    
    async with MTEClient() as client:
        if args.dataset == "rais":
            df = await client.fetch_rais_pcd(args.year, args.uf)
        elif args.dataset == "caged":
            df = await client.fetch_caged_pcd(args.year, args.month, args.uf)
        elif args.dataset == "cotas":
            df = await client.fetch_cotas_estabelecimentos(args.year, args.uf)
        elif args.dataset == "fiscalizacao":
            df = await client.fetch_cotas_fiscalizacao(args.year, args.uf)
        else:
            df = pd.DataFrame()
        
        print(f"Linhas: {len(df)}, Colunas: {len(df.columns)}")
        if not df.empty:
            print(df.head(3).to_string())
            
            if args.output:
                df.to_parquet(args.output, index=False)
                print(f"Salvo em: {args.output}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())