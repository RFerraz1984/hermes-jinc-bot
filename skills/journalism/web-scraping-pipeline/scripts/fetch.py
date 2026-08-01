#!/usr/bin/env python3
"""
Módulo de fetch - busca conteúdo das fontes configuradas.
Suporta HTML (Playwright/httpx), JSON API, XML API, file download.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

import httpx
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Erro durante fetch."""
    pass


async def fetch_source(source_config: Dict[str, Any]) -> Any:
    """
    Busca conteúdo de uma fonte.
    
    Args:
        source_config: Dict com configuração da fonte
            - id: identificador único
            - name: nome legível
            - url: URL base
            - type: "html" | "html_js" | "json_api" | "xml_api" | "file_download"
            - selectors: para HTML (opcional)
            - json_path: para JSON (opcional)
            - xpath: para XML (opcional)
            - headers: headers HTTP customizados
            - auth: autenticação (bearer, basic, api_key)
            - params: query params
            - wait_for: seletor para aguardar (html_js)
            - timeout: timeout em segundos
            - pagination: config de paginação
    
    Returns:
        Conteúdo bruto (str para HTML/XML, dict/list para JSON, bytes para file)
    """
    source_type = source_config.get("type", "html")
    url = source_config.get("url")
    timeout = source_config.get("timeout", 30)
    
    if not url:
        raise FetchError("URL não configurada")
    
    # Prepara headers
    headers = {
        "User-Agent": "JornalistaInclusivoBot/1.0 (+https://jornalistainclusivo.com)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }
    headers.update(source_config.get("headers", {}))
    
    # Prepara auth
    auth = source_config.get("auth")
    if auth:
        if auth.get("type") == "bearer":
            headers["Authorization"] = f"Bearer {auth['token']}"
        elif auth.get("type") == "basic":
            import base64
            creds = base64.b64encode(f"{auth['username']}:{auth['password']}".encode()).decode()
            headers["Authorization"] = f"Basic {creds}"
        elif auth.get("type") == "api_key":
            headers[auth.get("header", "X-API-Key")] = auth["key"]
    
    params = source_config.get("params", {})
    
    try:
        if source_type == "html":
            return await _fetch_html(url, headers, params, timeout)
        elif source_type == "html_js":
            return await _fetch_html_js(url, headers, params, timeout, source_config.get("wait_for"))
        elif source_type == "json_api":
            return await _fetch_json_api(url, headers, params, timeout, source_config.get("json_path"))
        elif source_type == "xml_api":
            return await _fetch_xml_api(url, headers, params, timeout, source_config.get("xpath"))
        elif source_type == "file_download":
            return await _fetch_file_download(url, headers, params, timeout)
        else:
            raise FetchError(f"Tipo de fonte desconhecido: {source_type}")
            
    except httpx.TimeoutException:
        raise FetchError(f"Timeout ({timeout}s) ao acessar {url}")
    except httpx.HTTPStatusError as e:
        raise FetchError(f"HTTP {e.response.status_code}: {url}")
    except Exception as e:
        raise FetchError(f"Erro ao buscar {url}: {e}")


async def _fetch_html(url: str, headers: Dict, params: Dict, timeout: int) -> str:
    """Busca HTML estático via httpx."""
    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.text


async def _fetch_html_js(
    url: str,
    headers: Dict,
    params: Dict,
    timeout: int,
    wait_for: Optional[str] = None,
) -> str:
    """Busca HTML com JavaScript via Playwright."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent=headers.get("User-Agent"),
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()
            
            # Adiciona headers customizados
            await page.set_extra_http_headers({k: v for k, v in headers.items() if k != "User-Agent"})
            
            await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)
            else:
                await page.wait_for_timeout(2000)
            
            content = await page.content()
            return content
        finally:
            await browser.close()


async def _fetch_json_api(
    url: str,
    headers: Dict,
    params: Dict,
    timeout: int,
    json_path: Optional[str] = None,
) -> Any:
    """Busca JSON API."""
    headers["Accept"] = "application/json"
    
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        if json_path:
            import jsonpath_ng
            expr = jsonpath_ng.parse(json_path)
            matches = [match.value for match in expr.find(data)]
            return matches
        
        return data


async def _fetch_xml_api(
    url: str,
    headers: Dict,
    params: Dict,
    timeout: int,
    xpath: Optional[str] = None,
) -> str:
    """Busca XML."""
    headers["Accept"] = "application/xml, text/xml"
    
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        xml_text = resp.text
        
        if xpath:
            import lxml.etree as ET
            root = ET.fromstring(xml_text.encode())
            elements = root.xpath(xpath)
            return ET.tostring(elements[0], encoding="unicode") if elements else ""
        
        return xml_text


async def _fetch_file_download(
    url: str,
    headers: Dict,
    params: Dict,
    timeout: int,
) -> bytes:
    """Baixa arquivo binário (PDF, ZIP, etc)."""
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.content


async def fetch_with_pagination(
    source_config: Dict[str, Any],
    max_pages: int = 10,
) -> List[Any]:
    """
    Busca múltiplas páginas paginadas.
    
    Configuração de paginação em source_config:
    - pagination.type: "page_param" | "offset_limit" | "cursor" | "link_header"
    - pagination.page_param: nome do parâmetro de página (default: "page")
    - pagination.per_page_param: nome do parâmetro por página (default: "per_page")
    - pagination.offset_param: nome do parâmetro offset
    - pagination.limit_param: nome do parâmetro limit
    - pagination.cursor_param: nome do parâmetro cursor
    - pagination.start_page: página inicial (default: 1)
    """
    pagination = source_config.get("pagination", {})
    if not pagination:
        return [await fetch_source(source_config)]
    
    p_type = pagination.get("type", "page_param")
    max_p = pagination.get("max_pages", max_pages)
    
    all_results = []
    base_params = source_config.get("params", {}).copy()
    
    if p_type == "page_param":
        page_param = pagination.get("page_param", "page")
        per_page_param = pagination.get("per_page_param", "per_page")
        start_page = pagination.get("start_page", 1)
        per_page = pagination.get("per_page", 100)
        
        base_params[per_page_param] = str(per_page)
        
        for page in range(start_page, start_page + max_p):
            base_params[page_param] = str(page)
            source_config["params"] = base_params
            
            try:
                result = await fetch_source(source_config)
                if not result:
                    break
                all_results.append(result)
                
                # Se resultado vazio ou menor que per_page, para
                if isinstance(result, list) and len(result) < per_page:
                    break
                    
            except Exception as e:
                logger.warning(f"Erro na página {page}: {e}")
                break
    
    elif p_type == "offset_limit":
        offset_param = pagination.get("offset_param", "offset")
        limit_param = pagination.get("limit_param", "limit")
        limit = pagination.get("limit", 100)
        
        base_params[limit_param] = str(limit)
        offset = 0
        
        for _ in range(max_p):
            base_params[offset_param] = str(offset)
            source_config["params"] = base_params
            
            try:
                result = await fetch_source(source_config)
                if not result:
                    break
                all_results.append(result)
                
                if isinstance(result, list) and len(result) < limit:
                    break
                offset += limit
                    
            except Exception as e:
                logger.warning(f"Erro no offset {offset}: {e}")
                break
    
    return all_results


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Fetch Source")
    parser.add_argument("--url", required=True, help="URL para buscar")
    parser.add_argument("--type", default="html", choices=["html", "html_js", "json_api", "xml_api", "file_download"])
    parser.add_argument("--output", "-o", type=str, help="Arquivo de saída")
    parser.add_argument("--wait-for", help="Seletor para aguardar (html_js)")
    parser.add_argument("--json-path", help="JSONPath para extrair (json_api)")
    parser.add_argument("--xpath", help="XPath para extrair (xml_api)")
    args = parser.parse_args()
    
    source = {
        "url": args.url,
        "type": args.type,
        "wait_for": args.wait_for,
        "json_path": args.json_path,
        "xpath": args.xpath,
    }
    
    try:
        result = await fetch_source(source)
        
        if args.output:
            import json
            with open(args.output, "w", encoding="utf-8") as f:
                if isinstance(result, (dict, list)):
                    json.dump(result, f, ensure_ascii=False, indent=2)
                elif isinstance(result, bytes):
                    with open(args.output, "wb") as f:
                        f.write(result)
                else:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(str(result))
            print(f"Salvo em: {args.output}")
        else:
            if isinstance(result, (dict, list)):
                print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])
            elif isinstance(result, bytes):
                print(f"Bytes: {len(result)}")
            else:
                print(str(result)[:2000])
                
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())