#!/usr/bin/env python3
"""
Wrapper axe-core via Playwright (já integrado no audit.py).
Este módulo fornece run_axe() standalone para uso direto.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Script axe-core injection
AXE_SCRIPT = """
// Inject axe-core
const script = document.createElement('script');
script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js';
script.onload = function() {
    axe.run(document, {
        runOnly: {
            type: 'tag',
            values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']
        },
        resultTypes: ['violations', 'passes', 'incomplete', 'inapplicable']
    }).then(results => {
        window.__AXE_RESULTS__ = results;
    }).catch(err => {
        window.__AXE_ERROR__ = err.message;
    });
};
document.head.appendChild(script);
"""


async def run_axe(
    url: str,
    wait_for: Optional[str] = None,
    timeout: int = 30000,
    include_iframes: bool = True,
    output: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executa axe-core na URL via Playwright.
    
    Returns:
        Dict com violations, passes, incomplete, inapplicable
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 AxeBot/1.0"
            )
            page = await context.new_page()
            
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)
            
            await page.wait_for_timeout(2000)
            
            # Injeta axe
            await page.evaluate(AXE_SCRIPT)
            
            # Aguarda resultado
            await page.wait_for_function(
                "() => window.__AXE_RESULTS__ !== undefined || window.__AXE_ERROR__ !== undefined",
                timeout=15000
            )
            
            error = await page.evaluate("() => window.__AXE_ERROR__")
            if error:
                raise Exception(f"axe-core error: {error}")
            
            results = await page.evaluate("() => window.__AXE_RESULTS__")
            
            # Testa iframes
            if include_iframes:
                frames = page.frames
                for frame in frames[1:]:
                    try:
                        await frame.evaluate(AXE_SCRIPT)
                        await frame.wait_for_function(
                            "() => window.__AXE_RESULTS__ !== undefined", timeout=10000
                        )
                        frame_results = await frame.evaluate("() => window.__AXE_RESULTS__")
                        if frame_results and frame_results.get("violations"):
                            for v in frame_results["violations"]:
                                for node in v.get("nodes", []):
                                    node["frame"] = frame.url
                            results["violations"].extend(frame_results["violations"])
                    except Exception as e:
                        logger.debug(f"Iframe {frame.url} skipped: {e}")
            
            if output:
                with open(output, "w") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"Resultados axe salvos em: {output}")
            
            return results
            
        finally:
            await browser.close()


async def run_axe_cli(
    url: str,
    output: Optional[Path] = None,
    wait_for: Optional[str] = None,
) -> Dict[str, Any]:
    """Wrapper CLI."""
    logger.info(f"Executando axe-core: {url}")
    
    result = await run_axe(url, wait_for=wait_for, output=output)
    
    violations = result.get("violations", [])
    passes = result.get("passes", [])
    incomplete = result.get("incomplete", [])
    
    print(f"\naxe-core - {url}")
    print(f"  Violações: {len(violations)} | Passes: {len(passes)} | Incompletos: {len(incomplete)}")
    
    # Agrupa por impacto
    by_impact = {}
    for v in violations:
        impact = v.get("impact", "unknown")
        by_impact[impact] = by_impact.get(impact, 0) + 1
    
    for impact, count in sorted(by_impact.items()):
        print(f"  {impact.capitalize()}: {count}")
    
    for v in violations[:5]:
        print(f"  [{v.get('impact','')}] {v.get('id')}: {v.get('description','')[:80]}")
        print(f"    Nós: {len(v.get('nodes', []))}")
        if v.get('nodes'):
            print(f"    Seletor: {v['nodes'][0].get('target', [''])[0]}")
    
    return result


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="axe-core CLI via Playwright")
    parser.add_argument("url", help="URL para auditar")
    parser.add_argument("--output", "-o", type=Path, help="Arquivo JSON de saída")
    parser.add_argument("--wait-for", help="Seletor CSS para aguardar")
    args = parser.parse_args()
    
    await run_axe_cli(args.url, args.output, args.wait_for)


if __name__ == "__main__":
    asyncio.run(main())