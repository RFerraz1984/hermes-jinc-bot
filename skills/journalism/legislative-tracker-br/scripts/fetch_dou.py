#!/usr/bin/env python3
"""
Busca leis e decretos sancionados no Diário Oficial da União (DOU).
"""

import logging
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


DOU_BASE = "https://www.in.gov.br"


async def fetch_dou_leis(
    data_inicio: Optional[str] = None,
    secoes: Optional[List[int]] = None,
    max_pages: int = 5
) -> List[Dict[str, Any]]:
    """
    Busca leis, decretos e MPs publicadas no DOU Seção 1.
    
    Args:
        data_inicio: Data inicial YYYY-MM-DD (default: 30 dias atrás)
        secoes: Seções do DOU a buscar (default: [1] - Seção 1)
        max_pages: Máximo de páginas por seção
    
    Returns:
        Lista de atos normativos
    """
    from datetime import date
    
    if data_inicio is None:
        data_inicio = (date.today() - timedelta(days=30)).isoformat()
    
    if secoes is None:
        secoes = [1]  # Seção 1 = leis, decretos, MPs
    
    # Formata data para URL do DOU
    dia, mes, ano = data_inicio.split("-")
    data_str = f"{dia}-{mes}-{ano}"
    
    all_leis = []
    
    for secao in secoes:
        logger.info(f"Buscando DOU Seção {secao} a partir de {data_inicio}")
        
        for page in range(1, max_pages + 1):
            url = f"{DOU_BASE}/leiturajornal"
            params = {
                "data": data_str,
                "secao": f"secao{secao}",
                "pagina": page,
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                try:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.error(f"Erro HTTP DOU: {e}")
                    break
                
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Verifica se chegou ao fim
                artigos = soup.select("article.article-item")
                if not artigos:
                    logger.debug(f"Seção {secao}, página {page}: sem artigos")
                    break
                
                for art in artigos:
                    lei = parse_dou_artigo(art, secao, data_inicio)
                    if lei:
                        all_leis.append(lei)
                
                logger.debug(f"DOU Seção {secao} página {page}: {len(artigos)} artigos")
                
                # Verifica paginação
                next_link = soup.select_one("a.next-page, a[rel='next']")
                if not next_link:
                    break
    
    logger.info(f"Total de atos DOU encontrados: {len(all_leis)}")
    return all_leis


def parse_dou_artigo(article, secao: int, data_ref: str) -> Optional[Dict[str, Any]]:
    """Parseia um artigo do DOU."""
    try:
        # Título/link
        titulo_elem = article.select_one("h3 a, h2 a, .titulo a")
        if not titulo_elem:
            return None
        
        titulo = titulo_elem.get_text(strip=True)
        link = titulo_elem.get("href", "")
        if link and not link.startswith("http"):
            link = f"{DOU_BASE}{link}"
        
        # Tipo do ato (Portaria, Decreto, Lei, MP, etc.)
        tipo_elem = article.select_one(".tipo-ato, .tipo, .categoria")
        tipo = tipo_elem.get_text(strip=True) if tipo_elem else ""
        
        # Órgão
        orgao_elem = article.select_one(".orgao, .ministerio, .orgao-publicador")
        orgao = orgao_elem.get_text(strip=True) if orgao_elem else ""
        
        # Data publicação
        data_elem = article.select_one("time, .data, .data-publicacao")
        data_pub = data_ref
        if data_elem:
            data_text = data_elem.get("datetime") or data_elem.get_text(strip=True)
            # Tenta parsear
            parsed = parse_dou_date(data_text)
            if parsed:
                data_pub = parsed
        
        # Conteúdo/resumo
        conteudo_elem = article.select_one(".resumo, .conteudo, .texto, p")
        conteudo = conteudo_elem.get_text(strip=True) if conteudo_elem else ""
        
        # Identifica se é relevante para PcD
        texto_completo = f"{titulo} {conteudo} {tipo} {orgao}".lower()
        
        # Número do ato (se houver)
        numero_match = re.search(r"n[º°\s]*[\d\.]+", titulo, re.IGNORECASE)
        numero = numero_match.group(0) if numero_match else ""
        
        return {
            "titulo": titulo,
            "link": link,
            "tipo": tipo,
            "orgao": orgao,
            "data": data_pub,
            "secao": secao,
            "conteudo": conteudo[:2000],  # Limita
            "texto_completo": texto_completo,
            "numero": numero,
            "id_externo": f"dou-{secao}-{data_ref}-{hash(titulo + link) % 100000}",
            "casa": "dou",
            "relevante_pcd": any(kw in texto_completo for kw in [
                "pessoa com deficiência", "pcD", "deficiência", "acessibilidade",
                "inclusão", "cota", "LBI", "Lei 13.146", "Decreto 10.098", "CONADE"
            ]),
        }
    except Exception as e:
        logger.warning(f"Erro parseando artigo DOU: {e}")
        return None


def parse_dou_date(date_text: str) -> Optional[str]:
    """Parseia data do DOU para ISO."""
    if not date_text:
        return None
    
    # Formatos comuns DOU
    patterns = [
        r"(\d{2})/(\d{2})/(\d{4})",
        r"(\d{4})-(\d{2})-(\d{2})",
        r"(\d{2})\s+de\s+(\w+)\s+de\s+(\d{4})",
    ]
    
    meses = {
        "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
        "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
        "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12",
    }
    
    for pattern in patterns:
        m = re.search(pattern, date_text, re.IGNORECASE)
        if m:
            try:
                if len(m.groups()) == 3:
                    if m.group(2).isalpha():
                        # DD de Mês de AAAA
                        dia, mes_nome, ano = m.groups()
                        return f"{ano}-{meses[mes_nome.lower()]}-{dia.zfill(2)}"
                    else:
                        # DD/MM/AAAA ou AAAA-MM-DD
                        if len(m.group(1)) == 4:
                            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                        else:
                            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            except Exception:
                pass
    
    return None


async def fetch_dou_artigo_completo(url: str) -> Optional[str]:
    """Busca texto completo de um ato no DOU."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Busca conteúdo principal
            conteudo = soup.select_one(".conteudo-ato, .texto-integral, .article-body, #texto")
            if conteudo:
                return conteudo.get_text(strip=True)[:5000]
        except Exception as e:
            logger.warning(f"Erro buscando artigo completo DOU: {e}")
    return None


if __name__ == "__main__":
    import asyncio
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        leis = await fetch_dou_leis(max_pages=2)
        print(f"Total: {len(leis)}")
        for l in leis[:3]:
            print(f"  [{l.get('tipo','')}] {l.get('titulo','')[:80]}")
            print(f"    Órgão: {l.get('orgao','')} | Data: {l.get('data','')}")
            print(f"    Link: {l.get('link','')}")
            print()
    
    asyncio.run(test())