#!/usr/bin/env python3
"""
Cliente Portal da Transparência - convênios, termos, emendas parlamentares, repasses PcD.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

from cache import get_cache

logger = logging.getLogger(__name__)


class TransparenciaClient:
    """Cliente para API do Portal da Transparência."""
    
    BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"
    
    # Endpoints
    ENDPOINTS = {
        "convenios": "/convenios",
        "termos": "/termos",
        "emendas": "/emendas",
        "repasses": "/repasses",
        "licitacoes": "/licitacoes",
        "contratos": "/contratos",
    }
    
    def __init__(self, api_token: Optional[str] = None, cache: Any = None):
        self.api_token = api_token or os.getenv("TRANSPARENCIA_TOKEN")
        self.cache = cache or get_cache()
        
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=60,
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    def _params(
        self,
        pagina: int = 1,
        tam_pagina: int = 500,
        **filters,
    ) -> Dict[str, Any]:
        """Constrói parâmetros de query."""
        params = {"pagina": pagina, "tamPagina": tam_pagina}
        params.update({k: v for k, v in filters.items() if v is not None})
        return params
    
    async def fetch_paginated(
        self,
        endpoint: str,
        max_pages: int = 50,
        **filters,
    ) -> pd.DataFrame:
        """Busca paginada genérica."""
        all_data = []
        
        for page in range(1, max_pages + 1):
            params = self._params(pagina=page, **filters)
            
            cache_key = f"transparencia_{endpoint}_p{page}_{hash(str(filters))}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                data = cached
            else:
                try:
                    resp = await self.client.get(endpoint, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    self.cache.set(cache_key, data, ttl_days=7)
                except httpx.HTTPStatusError as e:
                    logger.error(f"Erro HTTP {e.response.status_code}: {e.response.text}")
                    break
                except Exception as e:
                    logger.error(f"Erro na requisição: {e}")
                    break
            
            if not data:
                break
            
            all_data.extend(data)
            
            if len(data) < params["tamPagina"]:
                break
        
        if all_data:
            df = pd.DataFrame(all_data)
            df['dataset'] = f'transparencia_{endpoint.lstrip("/")}'
            return df
        
        return pd.DataFrame()
    
    async def fetch_convenios_pcd(
        self,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        palavra_chave: str = "pessoa com deficiência",
        uf: Optional[str] = None,
        orgao: Optional[str] = None,
    ) -> pd.DataFrame:
        """Busca convênios relacionados a PcD."""
        filters = {
            "dataInicio": data_inicio,
            "dataFim": data_fim,
            "palavraChave": palavra_chave,
            "uf": uf,
            "orgao": orgao,
        }
        return await self.fetch_paginated(self.ENDPOINTS["convenios"], **filters)
    
    async def fetch_emendas_pcd(
        self,
        ano: int = 2024,
        uf: Optional[str] = None,
        parlamentar: Optional[str] = None,
        palavra_chave: str = "deficiência",
    ) -> pd.DataFrame:
        """Busca emendas parlamentares PcD."""
        filters = {
            "ano": str(ano),
            "uf": uf,
            "parlamentar": parlamentar,
            "palavraChave": palavra_chave,
        }
        return await self.fetch_paginated(self.ENDPOINTS["emendas"], **filters)
    
    async def fetch_repasses_pcd(
        self,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        uf: Optional[str] = None,
        municipio: Optional[str] = None,
    ) -> pd.DataFrame:
        """Busca repasses (Fundo a Fundo, etc.) PcD."""
        filters = {
            "dataInicio": data_inicio,
            "dataFim": data_fim,
            "uf": uf,
            "municipio": municipio,
            "palavraChave": "pessoa com deficiência",
        }
        return await self.fetch_paginated(self.ENDPOINTS["repasses"], **filters)
    
    async def fetch_licitacoes_pcd(
        self,
        ano: int = 2024,
        uf: Optional[str] = None,
        palavra_chave: str = "acessibilidade",
    ) -> pd.DataFrame:
        """Busca licitações com termos de acessibilidade."""
        filters = {
            "ano": str(ano),
            "uf": uf,
            "palavraChave": palavra_chave,
        }
        return await self.fetch_paginated(self.ENDPOINTS["licitacoes"], **filters)
    
    async def fetch_contratos_pcd(
        self,
        ano: int = 2024,
        uf: Optional[str] = None,
        palavra_chave: str = "tecnologia assistiva",
    ) -> pd.DataFrame:
        """Busca contratos com termos de acessibilidade/assistiva."""
        filters = {
            "ano": str(ano),
            "uf": uf,
            "palavraChave": palavra_chave,
        }
        return await self.fetch_paginated(self.ENDPOINTS["contratos"], **filters)
    
    async def search_all_pcd(
        self,
        year: int = 2024,
        uf: Optional[str] = None,
        keywords: List[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Busca completa PcD em todos endpoints."""
        keywords = keywords or [
            "pessoa com deficiência", "PcD", "acessibilidade",
            "tecnologia assistiva", "inclusão", "cota", "LBI"
        ]
        
        results = {}
        
        for keyword in keywords:
            logger.info(f"Buscando: {keyword}")
            
            results[f"convenios_{keyword}"] = await self.fetch_convenios_pcd(
                data_inicio=f"{year}-01-01",
                data_fim=f"{year}-12-31",
                palavra_chave=keyword,
                uf=uf,
            )
            
            results[f"emendas_{keyword}"] = await self.fetch_emendas_pcd(
                ano=year,
                palavra_chave=keyword,
                uf=uf,
            )
            
            results[f"licitacoes_{keyword}"] = await self.fetch_licitacoes_pcd(
                ano=year,
                palavra_chave=keyword,
                uf=uf,
            )
        
        return results


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Portal da Transparência Client")
    parser.add_argument("--output", "-o", type=str, help="Diretório de saída")
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--uf", help="UF (ex: SP, RJ)")
    parser.add_argument("--keyword", help="Palavra-chave", default="pessoa com deficiência")
    parser.add_argument("--dataset", choices=["convenios", "emendas", "repasses", "licitacoes", "contratos", "all"], default="all")
    args = parser.parse_args()
    
    async with TransparenciaClient() as client:
        if args.dataset == "all":
            results = await client.search_all_pcd(args.year, args.uf)
            
            if args.output:
                out_dir = Path(args.output)
                out_dir.mkdir(parents=True, exist_ok=True)
                
                for name, df in results.items():
                    if not df.empty:
                        path = Path(args.output) / f"transparencia_{name}_{args.year}.parquet"
                        df.to_parquet(path, index=False)
                        print(f"Salvo: {path} ({len(df)} linhas)")
        else:
            if args.dataset == "convenios":
                df = await client.fetch_convenios_pcd(palavra_chave=args.keyword, uf=args.uf)
            elif args.dataset == "emendas":
                df = await client.fetch_emendas_pcd(ano=args.year, palavra_chave=args.keyword, uf=args.uf)
            elif args.dataset == "repasses":
                df = await client.fetch_repasses_pcd(uf=args.uf)
            elif args.dataset == "licitacoes":
                df = await client.fetch_licitacoes_pcd(ano=args.year, palavra_chave=args.keyword, uf=args.uf)
            elif args.dataset == "contratos":
                df = await client.fetch_contratos_pcd(ano=args.year, palavra_chave=args.keyword, uf=args.uf)
            else:
                df = pd.DataFrame()
            
            print(f"Linhas: {len(df)}, Colunas: {list(df.columns)}")
            print(df.head(5).to_string())
            
            if args.output:
                df.to_parquet(args.output, index=False)
                print(f"Salvo em: {args.output}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())