#!/usr/bin/env python3
"""
Cliente IBGE SIDRA - acesso às tabelas do SIDRA (Sistema IBGE de Recuperação Automática).
Documentação: https://api.sidra.ibge.gov.br/home/ajuda
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
import pandas as pd

from cache import CacheManager

logger = logging.getLogger(__name__)

BASE_URL = "https://api.sidra.ibge.gov.br/values"
RATE_LIMIT_DELAY = 0.5  # segundos entre requests


class SIDRAClient:
    """Cliente para API SIDRA do IBGE."""
    
    def __init__(self, cache: Any = None):
        self.cache = cache
        self.client = httpx.AsyncClient(
            timeout=60,
            headers={"User-Agent": "JornalistaInclusivoBot/1.0 (+https://jornalistainclusivo.com)"}
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    def _build_url(
        self,
        table: int,
        variables: List[int],
        period: str,
        classifications: Dict[str, str],
        geo: str = "1",
    ) -> str:
        """Constrói URL da API SIDRA."""
        var_str = ",".join(str(v) for v in variables)
        classif_str = ",".join(f"{k}:{v}" for k, v in classifications.items())
        
        parts = [
            f"t/{table}",
            f"v/{var_str}",
            f"p/{period}",
            f"c/{classif_str}",
            f"n/{geo}",
            "f/json",
        ]
        return f"{BASE_URL}/{'/'.join(parts)}"
    
    async def query(
        self,
        table: int,
        variables: List[int],
        period: str = "last",
        classifications: Dict[str, str] = None,
        geo: str = "1",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Executa query SIDRA e retorna DataFrame.
        
        Args:
            table: Código da tabela SIDRA (ex: 9606, 6389, 6579)
            variables: Lista de códigos de variáveis (ex: [93, 202] para total e %)
            period: Período ("last", "2022", "2020-2022", "all")
            classifications: Dict {id_classificacao: "valores"} (ex: {"2": "all", "86": "all"})
            geo: Nível geográfico ("1"=Brasil, "6"=UF, "2"=Município, "3"=Região)
        """
        classifications = classifications or {}
        
        # Cache key
        cache_key = f"sidra_t{table}_v{','.join(map(str, variables))}_p{period}_c{','.join(f'{k}{v}' for k,v in (classifications or {}).items())}_n{geo}"
        
        if self.cache and use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.info(f"Cache hit: {cache_key}")
                return pd.DataFrame(cached)
        
        url = self._build_url(table, variables, period, classifications or {}, geo)
        logger.info(f"SIDRA query: {url}")
        
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            if not data or len(data) < 2:
                logger.warning(f"SIDRA retornou dados vazios para tabela {table}")
                return pd.DataFrame()
            
            # Primeira linha é header
            headers = data[0]
            rows = data[1:]
            
            df = pd.DataFrame(rows, columns=headers)
            
            # Renomeia colunas padrão
            rename_map = {
                "D1C": "localidade_cod",
                "D1N": "localidade_nome",
                "D2C": "periodo_cod",
                "D2N": "periodo_nome",
                "V": "variavel_cod",
                "VN": "variavel_nome",
                "Valor": "valor",
                "M": "metadado",
            }
            df = df.rename(columns=rename_map)
            
            # Processa classificações (C1, C2, etc.)
            for col in df.columns:
                if col.startswith("C") and col[1:].isdigit():
                    classif_id = col[1:]
                    # Tenta separar código e nome se estiverem juntos
                    pass
            
            # Converte valor para numérico
            if "valor" in df.columns:
                df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
            
            logger.info(f"SIDRA: {len(df)} linhas obtidas da tabela {table}")
            
            # Cache
            if self.cache and use_cache:
                self.cache.set(cache_key, df.to_dict("records"), ttl_days=7)
            
            return df
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP SIDRA: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erro SIDRA: {e}")
            raise
    
    async def query_sync(
        self,
        table: int,
        variables: List[int],
        period: str = "last",
        classifications: Dict[str, str] = None,
        geo: str = "1",
    ) -> pd.DataFrame:
        """Wrapper síncrono para uso em scripts não-async."""
        import asyncio
        return asyncio.run(self.query(table, variables, period, classifications, geo))


# Cliente síncrono simples para scripts rápidos
class SIDRASyncClient:
    """Cliente SIDRA síncrono usando requests."""
    
    def __init__(self, cache: Any = None):
        self.cache = cache
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "JornalistaInclusivoBot/1.0"
        })
    
    def query(
        self,
        table: int,
        variables: List[int],
        period: str = "last",
        classifications: Dict[str, str] = None,
        geo: str = "1",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        classifications = classifications or {}
        
        cache_key = f"sidra_t{table}_v{','.join(map(str, variables))}_p{period}_c{','.join(f'{k}{v}' for k,v in (classifications or {}).items())}_n{geo}"
        
        if self.cache and use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return pd.DataFrame(cached)
        
        var_str = ",".join(str(v) for v in variables)
        classif_str = ",".join(f"{k}:{v}" for k, v in (classifications or {}).items())
        
        url = f"{BASE_URL}/t/{table}/v/{var_str}/p/{period}/c/{classif_str}/n/{geo}/f/json"
        
        logger.info(f"SIDRA sync query: {url}")
        
        try:
            resp = self.session.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            if not data or len(data) < 2:
                return pd.DataFrame()
            
            headers = data[0]
            rows = data[1:]
            
            df = pd.DataFrame(rows, columns=headers)
            
            rename_map = {
                "D1C": "localidade_cod",
                "D1N": "localidade_nome",
                "D2C": "periodo_cod",
                "D2N": "periodo_nome",
                "V": "variavel_cod",
                "VN": "variavel_nome",
                "Valor": "valor",
                "M": "metadado",
            }
            df = df.rename(columns=rename_map)
            
            if "valor" in df.columns:
                df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
            
            logger.info(f"SIDRA sync: {len(df)} linhas da tabela {table}")
            
            if self.cache:
                self.cache.set(cache_key, df.to_dict("records"), ttl_days=7)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro SIDRA sync: {e}")
            raise


if __name__ == "__main__":
    import asyncio
    import logging
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        async with SIDRAClient() as client:
            # Teste: Censo 2022 deficiência por UF (tabela 9606)
            df = await client.query(
                table=9606,
                variables=[93, 202],  # Total, Percentual
                period="2022",
                classifications={"2": "all", "86": "all", "227": "all", "292": "all"},  # tipo, sexo, idade, cor
                geo="6",  # UF
            )
            print(f"Linhas: {len(df)}")
            print(df.head())
            print(df.columns.tolist())
    
    asyncio.run(test())