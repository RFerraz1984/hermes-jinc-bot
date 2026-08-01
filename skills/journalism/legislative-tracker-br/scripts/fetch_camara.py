#!/usr/bin/env python3
"""
Busca proposições na Câmara dos Deputados via API Dados Abertos v2.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


CAMARA_API_BASE = "https://dadosabertos.camara.leg.br/api/v2"


async def fetch_camara_proposicoes(
    data_inicio: Optional[str] = None,
    itens: int = 100,
    temas: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Busca proposições recentes na Câmara.
    
    Args:
        data_inicio: Data inicial no formato YYYY-MM-DD (default: 30 dias atrás)
        itens: Número de itens por página (max 100)
        temas: Lista de códigos de tema para filtrar
    
    Returns:
        Lista de proposições (cada uma é um dict)
    """
    from datetime import date, timedelta
    
    if data_inicio is None:
        data_inicio = (date.today() - timedelta(days=30)).isoformat()
    
    url = f"{CAMARA_API_BASE}/proposicoes"
    params = {
        "dataInicio": data_inicio,
        "itens": min(itens, 100),
        "ordenarPor": "id",
        "ordem": "DESC",
    }
    
    if temas:
        params["codTema"] = ",".join(temas)
    
    all_props = []
    page = 1
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params["pagina"] = page
            logger.debug(f"Buscando página {page} da Câmara...")
            
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                logger.error(f"Erro HTTP na Câmara: {e}")
                raise
            
            dados = data.get("dados", [])
            if not dados:
                break
            
            all_props.extend(dados)
            logger.debug(f"Página {page}: {len(dados)} proposições")
            
            # Verifica se há próxima página
            links = data.get("links", [])
            next_link = next((l for l in links if l.get("rel") == "next"), None)
            if not next_link:
                break
            
            page += 1
            
            # Limite de segurança
            if page > 50:
                logger.warning("Limite de 50 páginas atingido")
                break
    
    logger.info(f"Total de proposições da Câmara: {len(all_props)}")
    return all_props


async def fetch_proposicao_detalhes(id_proposicao: int) -> Optional[Dict[str, Any]]:
    """Busca detalhes completos de uma proposição específica."""
    url = f"{CAMARA_API_BASE}/proposicoes/{id_proposicao}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json().get("dados")
        except httpx.HTTPError as e:
            logger.error(f"Erro buscando detalhes da proposição {id_proposicao}: {e}")
            return None


async def fetch_proposicao_tramitacoes(id_proposicao: int) -> List[Dict[str, Any]]:
    """Busca tramitações de uma proposição."""
    url = f"{CAMARA_API_BASE}/proposicoes/{id_proposicao}/tramitacoes"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json().get("dados", [])
        except httpx.HTTPError as e:
            logger.error(f"Erro buscando tramitações {id_proposicao}: {e}")
            return []


async def fetch_proposicao_autores(id_proposicao: int) -> List[Dict[str, Any]]:
    """Busca autores de uma proposição."""
    url = f"{CAMARA_API_BASE}/proposicoes/{id_proposicao}/autores"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json().get("dados", [])
        except httpx.HTTPError as e:
            logger.error(f"Erro buscando autores {id_proposicao}: {e}")
            return []


async def fetch_camara_proposicoes_full(
    data_inicio: Optional[str] = None,
    include_details: bool = True,
    temas: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Busca proposições com detalhes completos (tramitações, autores).
    """
    proposicoes = await fetch_camara_proposicoes(data_inicio, temas=temas)
    
    if not include_details:
        return proposicoes
    
    # Enriquece com detalhes (tramitações + autores)
    for prop in proposicoes:
        prop_id = prop.get("id")
        if not prop_id:
            continue
        
        # Busca tramitações
        tramitacoes = await fetch_proposicao_tramitacoes(prop_id)
        prop["tramitacoes"] = tramitacoes
        
        # Última tramitação
        if tramitacoes:
            ultima = tramitacoes[-1]
            prop["ultima_tramitacao"] = ultima.get("descricaoSituacao", "")
            prop["data_ultima_tramitacao"] = ultima.get("dataHora", "")
        
        # Busca autores
        autores = await fetch_proposicao_autores(prop_id)
        if autores:
            autor_principal = autores[0]
            prop["autor_nome"] = autor_principal.get("nome", "")
            prop["autor_partido"] = autor_principal.get("siglaPartido", "")
            prop["autor_uf"] = autor_principal.get("siglaUf", "")
    
    return proposicoes


if __name__ == "__main__":
    import asyncio
    import json
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        # Teste rápido - últimas 10 proposições
        props = await fetch_camara_proposicoes(itens=10)
        print(f"Total: {len(props)}")
        for p in props[:3]:
            print(f"  {p.get('siglaTipo')}-{p.get('numero')}/{p.get('ano')}: {p.get('ementa', '')[:80]}")
    
    asyncio.run(test())