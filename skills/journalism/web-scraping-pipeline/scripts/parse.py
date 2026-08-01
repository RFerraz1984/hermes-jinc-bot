#!/usr/bin/env python3
"""
Módulo de parse - extrai itens estruturados do conteúdo bruto.
Suporta HTML (BeautifulSoup + CSS selectors), JSON, XML.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import lxml.etree as ET

logger = logging.getLogger(__name__)


def parse_items(content: Any, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Função principal de parse - despacha para parser apropriado.
    
    Args:
        content: Conteúdo bruto (str para HTML/XML, dict/list para JSON)
        source_config: Config da fonte (selectors, json_path, xpath, etc)
    
    Returns:
        Lista de itens extraídos (cada item é dict com campos padronizados)
    """
    source_type = source_config.get("type", "html")
    
    if source_type in ("html", "html_js"):
        return parse_html(content, source_config.get("selectors", {}), source_config.get("base_url", ""))
    elif source_type == "json_api":
        return parse_json(content, source_config.get("json_path", "$"), source_config.get("fields", {}))
    elif source_type == "xml_api":
        return parse_xml(content, source_config.get("xpath_list", "//item"), source_config.get("xpath", {}))
    else:
        logger.warning(f"Tipo de fonte não suportado para parse: {source_config.get('type')}")
        return []


def parse_html(content: str, selectors: Dict[str, str], base_url: str = "") -> List[Dict[str, Any]]:
    """
    Parse HTML com BeautifulSoup + CSS selectors.
    
    Args:
        content: HTML string
        selectors: Dict {campo: seletor_css}
            Suporta sufixos:
            - @attr para atributo (ex: "h3 a@href")
            - ::text para texto apenas
            - ::html para HTML interno
        base_url: URL base para resolver URLs relativas
    
    Returns:
        Lista de itens extraídos
    """
    soup = BeautifulSoup(content, "lxml")
    items = []
    
    list_selector = selectors.get("list")
    if not list_selector:
        logger.warning("Seletor 'list' não definido")
        return items
    
    elements = soup.select(list_selector)
    logger.debug(f"Encontrados {len(elements)} elementos com seletor '{list_selector}'")
    
    for idx, el in enumerate(elements):
        item = {"_raw_index": idx}
        
        for field, selector in selectors.items():
            if field == "list":
                continue
            
            value = extract_with_selector(el, selector, base_url)
            item[field] = value
        
        # Garante campos mínimos
        if not item.get("title"):
            item["title"] = item.get("text", "")[:100]
        
        items.append(item)
    
    return items


def extract_with_selector(element, selector: str, base_url: str = "") -> Any:
    """Extrai valor usando seletor CSS com sufixos especiais."""
    # Parse sufixos
    attr = None
    text_only = False
    html_only = False
    
    if "@" in selector and not selector.startswith("@"):
        selector, attr = selector.rsplit("@", 1)
    elif selector.endswith("::text"):
        selector = selector[:-6]
        text_only = True
    elif selector.endswith("::html"):
        selector = selector[:-6]
        html_only = True
    
    try:
        if selector.startswith("//"):
            # XPath
            from lxml import etree
            from lxml import html as lxml_html
            lxml_el = lxml_html.fromstring(str(element))
            result = lxml_el.xpath(selector)
            if result:
                if attr:
                    return result[0].get(attr) if hasattr(result[0], 'get') else str(result[0])
                return result[0] if len(result) == 1 else result
            return None
        else:
            # CSS selector
            matched = element.select(selector)
            if not matched:
                return None
            
            if len(matched) == 1:
                el = matched[0]
                if attr:
                    return el.get(attr)
                elif text_only:
                    return el.get_text(strip=True)
                elif html_only:
                    return str(el)
                else:
                    # Extrai o mais útil
                    if el.name == "a":
                        href = el.get("href")
                        text = el.get_text(strip=True)
                        return {"text": text, "href": href} if href else text
                    elif el.name == "img":
                        return {"alt": el.get("alt", ""), "src": el.get("src", "")}
                    else:
                        return el.get_text(strip=True)
            else:
                # Múltiplos elementos
                results = []
                for el in matched:
                    if attr:
                        results.append(el.get(attr))
                    elif text_only:
                        results.append(el.get_text(strip=True))
                    elif html_only:
                        results.append(str(el))
                    else:
                        results.append(el.get_text(strip=True))
                return results
    except Exception as e:
        logger.debug(f"Erro extraindo seletor '{selector}': {e}")
        return None


def parse_json(content: Any, json_path: str, field_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    """Parse JSON API com jsonpath-ng."""
    import jsonpath_ng
    
    if isinstance(content, str):
        data = json.loads(content)
    else:
        data = content
    
    expr = jsonpath_ng.parse(json_path)
    matches = expr.find(data)
    
    items = []
    for match in matches:
        raw = match.value
        if not isinstance(raw, dict):
            continue
        
        item = {}
        for out_field, in_path in field_mapping.items():
            try:
                expr2 = jsonpath_ng.parse(in_path)
                vals = expr2.find(raw)
                item[out_field] = vals[0].value if vals else None
            except Exception:
                item[out_field] = None
        items.append(item)
    
    return items


def parse_xml(content: str, list_xpath: str, xpath_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    """Parse XML usando lxml."""
    try:
        root = ET.fromstring(content.encode() if isinstance(content, str) else content)
    except ET.XMLSyntaxError as e:
        logger.error(f"Erro parseando XML: {e}")
        return []
    
    items = []
    elements = root.xpath(list_xpath)
    
    for el in elements:
        item = {}
        for field, xpath in xpath_mapping.items():
            try:
                result = el.xpath(xpath)
                if result:
                    if hasattr(result[0], 'text'):
                        item[field] = result[0].text
                    else:
                        item[field] = str(result[0])
                else:
                    item[field] = None
            except Exception:
                item[field] = None
        items.append(item)
    
    return items


def parse_content(content: Any, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Alias para parse_items (compatibilidade)."""
    return parse_items(content, source_config)


# Normalização de dados comuns
def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """Normaliza data para ISO 8601 (YYYY-MM-DD)."""
    if not date_str:
        return None
    
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%d de %B de %Y",
        "%d de %b de %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    
    # Tenta extrair com regex
    patterns = [
        r"(\d{4})-(\d{2})-(\d{2})",
        r"(\d{2})/(\d{2})/(\d{4})",
        r"(\d{2})/(\d{2})/(\d{2})",
    ]
    for pattern in patterns:
        m = re.search(pattern, date_str)
        if m:
            try:
                if len(m.group(1)) == 4:
                    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                else:
                    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            except Exception:
                pass
    
    logger.warning(f"Não foi possível parsear data: {date_str}")
    return None


def normalize_url(url: Optional[str], base_url: str = "") -> Optional[str]:
    """Normaliza URL para absoluta."""
    if not url:
        return None
    url = url.strip()
    if url.startswith(("http://", "https://")):
        return url
    if base_url:
        return urljoin(base_url, url)
    return url


def clean_text(text: Optional[str]) -> Optional[str]:
    """Limpa texto: remove whitespace excessivo, chars de controle."""
    if not text:
        return None
    # Remove chars de controle exceto newline/tab
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Colapsa whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    
    # Teste rápido
    html = """
    <html><body>
    <article class="article-item">
        <h3><a href="/noticia/123">Título da Notícia</a></h3>
        <time datetime="2026-07-24">24/07/2026</time>
        <div class="article-content">Conteúdo da notícia aqui.</div>
    </article>
    </body></html>
    """
    
    selectors = {
        "list": "article.article-item",
        "title": "h3 a::text",
        "link": "h3 a@href",
        "date": "time@datetime",
        "content": "div.article-content::text",
    }
    
    items = parse_html(html, selectors, "https://exemplo.com")
    print(json.dumps(items, indent=2, ensure_ascii=False))