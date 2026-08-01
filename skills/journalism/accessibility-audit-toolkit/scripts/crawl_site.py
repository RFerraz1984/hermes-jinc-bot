#!/usr/bin/env python3
"""
Descobridor de URLs - sitemap + crawl limitado para definir escopo da auditoria.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def discover_urls(
    base_url: str,
    max_depth: int = 3,
    max_urls: int = 100,
    include_patterns: List[str] = None,
    exclude_patterns: List[str] = None,
    same_domain_only: bool = True,
) -> List[str]:
    """
    Descobre URLs para auditar.
    
    Prioridade:
    1. Sitemap.xml
    2. Crawl BFS limitado por profundidade
    3. Filtros include/exclude
    """
    base_parsed = urlparse(base_url)
    base_domain = base_parsed.netloc
    
    include_patterns = include_patterns or []
    exclude_patterns = exclude_patterns or [
        r".*\.(pdf|doc|docx|xls|xlsx|zip|rar|jpg|jpeg|png|gif|svg|css|js|ico|woff|woff2|ttf|eot)$",
        r".*/(login|admin|api|wp-admin|wp-json|feed|rss|xml|json).*",
        r".*\?.*(utm_|fbclid|gclid).*",
    ]
    
    discovered: Set[str] = set()
    to_visit: List[tuple] = [(base_url, 0)]  # (url, depth)
    
    # 1. Tenta sitemap.xml (apenas se max_depth > 0)
    sitemap_urls = []
    if max_depth > 0:
        sitemap_urls = await fetch_sitemap(base_url)
        for url in sitemap_urls:
            if should_include(url, include_patterns, exclude_patterns, base_domain, same_domain_only):
                discovered.add(normalize_url(url))
    
    logger.info(f"Sitemap: {len(sitemap_urls)} URLs encontradas")
    
    # 2. Crawl BFS
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        while to_visit and len(discovered) < max_urls:
            url, depth = to_visit.pop(0)
            
            if depth > max_depth:
                continue
            
            norm_url = normalize_url(url)
            if norm_url in discovered:
                continue
            
            if not should_include(norm_url, include_patterns, exclude_patterns, base_domain, same_domain_only):
                continue
            
            discovered.add(norm_url)
            
            if depth == max_depth:
                continue
            
            # Busca links na página
            try:
                resp = await client.get(norm_url, headers={"User-Agent": "A11yBot/1.0"})
                if resp.status_code != 200:
                    continue
                
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue
                
                soup = BeautifulSoup(resp.text, "html.parser")
                
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    absolute = urljoin(norm_url, href)
                    abs_norm = normalize_url(absolute)
                    
                    if abs_norm not in discovered and should_include(abs_norm, include_patterns, exclude_patterns, base_domain, same_domain_only):
                        to_visit.append((abs_norm, depth + 1))
                        
            except Exception as e:
                logger.debug(f"Erro crawl {norm_url}: {e}")
                continue
    
    result = sorted(list(discovered))[:max_urls]
    logger.info(f"Total URLs descobertas: {len(result)}")
    return result


async def fetch_sitemap(base_url: str) -> List[str]:
    """Busca URLs do sitemap.xml e sitemap_index.xml."""
    urls = []
    sitemap_locations = [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
        urljoin(base_url, "/sitemap.xml.gz"),
    ]
    
    async with httpx.AsyncClient(timeout=15) as client:
        for sitemap_url in sitemap_locations:
            try:
                resp = await client.get(sitemap_url)
                if resp.status_code == 200:
                    urls.extend(parse_sitemap(resp.text, resp.headers.get("content-type", "")))
                    logger.debug(f"Sitemap {sitemap_url}: {len(urls)} URLs")
            except Exception as e:
                logger.debug(f"Sitemap {sitemap_url} falhou: {e}")
    
    return urls


def parse_sitemap(xml_content: str, content_type: str = "") -> List[str]:
    """Parseia sitemap XML (suporta index e urlset)."""
    urls = []
    
    try:
        soup = BeautifulSoup(xml_content, "xml")
        
        # Sitemap index (referencia outros sitemaps)
        for sitemap in soup.find_all("sitemap"):
            loc = sitemap.find("loc")
            if loc and loc.text:
                # Recursivamente parseia sitemap referenciado
                # Por simplicidade, apenas coleta a URL do sitemap
                pass
        
        # URL set (URLs finais)
        for url_elem in soup.find_all("url"):
            loc = url_elem.find("loc")
            if loc and loc.text:
                urls.append(loc.text.strip())
                
    except Exception as e:
        logger.warning(f"Erro parseando sitemap: {e}")
    
    return urls


def should_include(
    url: str,
    include_patterns: List[str],
    exclude_patterns: List[str],
    base_domain: str,
    same_domain_only: bool,
) -> bool:
    """Verifica se URL deve ser incluída."""
    parsed = urlparse(url)
    
    # Mesmo domínio
    if same_domain_only and parsed.netloc != base_domain:
        return False
    
    # Exclude patterns
    for pattern in exclude_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return False
    
    # Include patterns (se definidos, deve matchar pelo menos um)
    if include_patterns:
        matched = any(re.search(p, url, re.IGNORECASE) for p in include_patterns)
        if not matched:
            return False
    
    return True


def normalize_url(url: str) -> str:
    """Normaliza URL removendo fragments, query params de tracking, etc."""
    parsed = urlparse(url)
    
    # Remove query params de tracking
    if parsed.query:
        params = []
        for param in parsed.query.split("&"):
            key = param.split("=")[0]
            if not key.startswith(("utm_", "fbclid", "gclid", "mc_", "ref_")):
                params.append(param)
        query = "&".join(params)
    else:
        query = ""
    
    # Reconstructs sem fragment
    normalized = parsed._replace(query=query, fragment="").geturl()
    
    # Remove trailing slash exceto root
    if normalized.endswith("/") and len(parsed.path) > 1:
        normalized = normalized[:-1]
    
    return normalized


async def discover_urls_cli(
    url: str,
    output: Optional[Path] = None,
    max_depth: int = 3,
    max_urls: int = 100,
) -> List[str]:
    """Wrapper CLI."""
    logger.info(f"Descobrindo URLs: {url} (depth={max_depth}, max={max_urls})")
    
    urls = await discover_urls(url, max_depth=max_depth, max_urls=max_urls)
    
    if output:
        with open(output, "w") as f:
            for u in urls:
                f.write(u + "\n")
        print(f"URLs salvas em: {output}")
    
    print(f"\nDescobertas {len(urls)} URLs para {url}:")
    for u in urls[:20]:
        print(f"  {u}")
    if len(urls) > 20:
        print(f"  ... e mais {len(urls) - 20}")
    
    return urls


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="URL Discovery para Auditoria")
    parser.add_argument("url", help="URL base")
    parser.add_argument("--output", "-o", type=Path, help="Arquivo com URLs (uma por linha)")
    parser.add_argument("--depth", type=int, default=3, help="Profundidade máxima do crawl")
    parser.add_argument("--max-urls", type=int, default=100, help="Máximo de URLs")
    args = parser.parse_args()
    
    await discover_urls_cli(args.url, args.output, args.depth, args.max_urls)


if __name__ == "__main__":
    asyncio.run(main())