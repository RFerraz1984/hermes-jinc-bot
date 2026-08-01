#!/usr/bin/env python3
"""
Busca matérias no Senado Federal via Dados Abertos (XML).
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx
import lxml.etree as ET

logger = logging.getLogger(__name__)


SENADO_API_BASE = "https://legis.senado.leg.br/dadosabertos"


async def fetch_senado_materias(
    data_inicial: Optional[str] = None,
    itens: int = 100
) -> List[Dict[str, Any]]:
    """
    Busca matérias recentes no Senado Federal.
    
    Args:
        data_inicial: Data inicial YYYY-MM-DD (default: 30 dias atrás)
        itens: Itens por página
    
    Returns:
        Lista de matérias normalizadas
    """
    if data_inicial is None:
        data_inicial = (date.today() - timedelta(days=30)).isoformat()
    
    url = f"{SENADO_API_BASE}/materia/pesquisa/lista"
    params = {
        "dataInicial": data_inicial,
        "itens": itens,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            xml_content = resp.text
        except httpx.HTTPError as e:
            logger.error(f"Erro HTTP no Senado: {e}")
            raise
    
    # Parse XML
    try:
        root = ET.fromstring(xml_content.encode())
    except ET.XMLSyntaxError as e:
        logger.error(f"Erro parseando XML do Senado: {e}")
        return []
    
    materias = []
    for materia_elem in root.xpath("//Materia"):
        materia = {}
        
        # Extrai campos usando XPath
        xpath_map = {
            "id": "IdentificacaoMateria/CodigoMateria",
            "sigla_tipo": "IdentificacaoMateria/SiglaSubtipoMateria",
            "numero": "IdentificacaoMateria/NumeroMateria",
            "ano": "IdentificacaoMateria/AnoMateria",
            "ementa": "IdentificacaoMateria/EmentaMateria",
            "link_inteiro_teor": "IdentificacaoMateria/LinkInteiroTeor",
            "data_apresentacao": "IdentificacaoMateria/DataApresentacao",
            "autor_nome": "IdentificacaoMateria/Autores/Autor/NomeAutor",
            "autor_partido": "IdentificacaoMateria/Autores/Autor/SiglaPartidoAutor",
            "autor_uf": "IdentificacaoMateria/Autores/Autor/UFAutor",
        }
        
        for field, xpath in xpath_map.items():
            elems = materia_elem.xpath(xpath)
            if elems:
                materia[field] = elems[0].text if hasattr(elems[0], 'text') else str(elems[0])
        
        # Tema (pode ter múltiplos)
        temas = materia_elem.xpath("Assuntos/Assunto/DescricaoAssunto/text()")
        if temas:
            materia["temas"] = temas
        
        # Situação atual
        situacao = materia_elem.xpath("SituacaoAtual/DescricaoSituacao/text()")
        if situacao:
            materia["situacao_atual"] = situacao[0]
        
        # Última tramitação
        ultima = materia_elem.xpath("UltimaTramitacao/DescricaoSituacao/text()")
        if ultima:
            materia["ultima_tramitacao"] = ultima[0]
        data_ultima = materia_elem.xpath("UltimaTramitacao/DataTramitacao/text()")
        if data_ultima:
            materia["data_ultima_tramitacao"] = data_ultima[0]
        
        # Normaliza ID
        sigla = materia.get("sigla_tipo", "").upper()
        numero = materia.get("numero", "")
        ano = materia.get("ano", "")
        if sigla and numero and ano:
            materia["id_externo"] = f"{sigla}-{numero}/{ano}"
        
        materia["casa"] = "senado"
        materias.append(materia)
    
    logger.info(f"Total de matérias do Senado: {len(materias)}")
    return materias


async def fetch_materia_detalhes(codigo_materia: str) -> Optional[Dict[str, Any]]:
    """Busca detalhes completos de uma matéria específica."""
    url = f"{SENADO_API_BASE}/materia/{codigo_materia}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            root = ET.fromstring(resp.text.encode())
            
            # Extrai detalhes similares ao fetch principal
            materia_elem = root.xpath("//Materia")
            if not materia_elem:
                return None
            return parse_materia_element(materia_elem[0])
        except Exception as e:
            logger.error(f"Erro buscando detalhes da matéria {codigo_materia}: {e}")
            return None


def parse_materia_element(elem: ET._Element) -> Dict[str, Any]:
    """Parseia elemento Materia XML para dict."""
    materia = {}
    
    xpath_map = {
        "id": "IdentificacaoMateria/CodigoMateria",
        "sigla_tipo": "IdentificacaoMateria/SiglaSubtipoMateria",
        "numero": "IdentificacaoMateria/NumeroMateria",
        "ano": "IdentificacaoMateria/AnoMateria",
        "ementa": "IdentificacaoMateria/EmentaMateria",
        "link_inteiro_teor": "IdentificacaoMateria/LinkInteiroTeor",
        "data_apresentacao": "IdentificacaoMateria/DataApresentacao",
        "autor_nome": "IdentificacaoMateria/Autores/Autor/NomeAutor",
        "autor_partido": "IdentificacaoMateria/Autores/Autor/SiglaPartidoAutor",
        "autor_uf": "IdentificacaoMateria/Autores/Autor/UFAutor",
    }
    
    for field, xpath in xpath_map.items():
        elems = elem.xpath(xpath)
        if elems:
            materia[field] = elems[0].text if hasattr(elems[0], 'text') else str(elems[0])
    
    # Temas
    temas = elem.xpath("Assuntos/Assunto/DescricaoAssunto/text()")
    if temas:
        materia["temas"] = temas
    
    # Situação
    situacao = elem.xpath("SituacaoAtual/DescricaoSituacao/text()")
    if situacao:
        materia["situacao_atual"] = situacao[0]
    
    # Última tramitação
    ultima = elem.xpath("UltimaTramitacao/DescricaoSituacao/text()")
    if ultima:
        materia["ultima_tramitacao"] = ultima[0]
    data_ultima = elem.xpath("UltimaTramitacao/DataTramitacao/text()")
    if data_ultima:
        materia["data_ultima_tramitacao"] = data_ultima[0]
    
    sigla = materia.get("sigla_tipo", "").upper()
    numero = materia.get("numero", "")
    ano = materia.get("ano", "")
    if sigla and numero and ano:
        materia["id_externo"] = f"{sigla}-{numero}/{ano}"
    
    materia["casa"] = "senado"
    return materia


if __name__ == "__main__":
    import asyncio
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        materias = await fetch_senado_materias(itens=10)
        print(f"Total: {len(materias)}")
        for m in materias[:3]:
            print(f"  {m.get('sigla_tipo')}-{m.get('numero')}/{m.get('ano')}: {m.get('ementa', '')[:80]}")
    
    asyncio.run(test())