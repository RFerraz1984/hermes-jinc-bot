#!/usr/bin/env python3
"""
Screen Reader Testing - NVDA/JAWS/Orca via speech-dispatcher.
For automated CI, uses speech-dispatcher + espeak-ng.
For local testing, can connect to running NVDA/JAWS via COM/AT-SPI.
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def run_screen_reader_test(
    url: str,
    output: Optional[Path] = None,
    wait_for: Optional[str] = None,
    voice: str = "pt-br",
    method: str = "speech-dispatcher",
) -> Dict[str, Any]:
    """
    Testa leitura de página via screen reader.

    Métodos suportados:
    - speech-dispatcher (Linux CI): usa espeak-ng via speechd
    - nvda-com (Windows local): conecta ao NVDA via COM
    - orca-atspi (Linux local): conecta ao Orca via AT-SPI
    """
    results = {
        "url": url,
        "method": method,
        "announcements": [],
        "issues": [],
        "skipped": False,
    }

    if method == "speech-dispatcher":
        try:
            import speechd
        except ImportError:
            logger.warning("python3-speechd não instalado — pulando teste screen reader")
            results["skipped"] = True
            results["error"] = "speechd_not_available"
            return results

        client = speechd.SSIPClient("a11y-audit")
        client.set_output_module("espeak-ng")
        client.set_voice(voice)
        client.set_punctuation(speechd.Punctuation.SOME)

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("playwright não instalado")
            results["skipped"] = True
            results["error"] = "playwright_not_available"
            return results

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                if wait_for:
                    await page.wait_for_selector(wait_for, timeout=10000)
                await page.wait_for_timeout(2000)

                # Coleta texto que seria lido
                readable_elements = await page.evaluate("""
                    () => {
                        const walker = document.createTreeWalker(
                            document.body, NodeFilter.SHOW_TEXT, null, false
                        );
                        const results = [];
                        let node;
                        while (node = walker.nextNode()) {
                            const parent = node.parentElement;
                            if (!parent) continue;
                            const style = getComputedStyle(parent);
                            if (style.display !== 'none' && style.visibility !== 'hidden') {
                                const text = node.textContent.trim();
                                if (text && text.length > 2) {
                                    results.push({
                                        text: text.slice(0, 200),
                                        tag: parent.tagName.toLowerCase(),
                                        role: parent.getAttribute('role') || '',
                                        ariaLabel: parent.getAttribute('aria-label') || '',
                                        ariaDescribedBy: parent.getAttribute('aria-describedby') || '',
                                    });
                                }
                            }
                        }
                        return results;
                    }
                """)

                # Envia para speech-dispatcher
                for item in readable_elements[:50]:  # Limita
                    announcement = {
                        "text": item["text"],
                        "context": item["tag"],
                        "role": item["role"],
                        "aria_label": item["ariaLabel"],
                    }
                    results["announcements"].append(announcement)
                    client.speak(item["text"])
                    await asyncio.sleep(0.1)  # Pausa entre anúncios

                # Verifica problemas comuns de screen reader
                sr_issues = await page.evaluate("""
                    () => {
                        const issues = [];
                        // Imagens sem alt
                        document.querySelectorAll('img:not([alt])').forEach(img => {
                            issues.push({type: 'missing_alt', element: img.outerHTML.slice(0, 100)});
                        });
                        // Botões sem nome acessível
                        document.querySelectorAll('button:not([aria-label]):not([aria-labelledby])').forEach(btn => {
                            if (!btn.textContent.trim()) {
                                issues.push({type: 'unnamed_button', element: btn.outerHTML.slice(0, 100)});
                            }
                        });
                        // Inputs sem label
                        document.querySelectorAll('input:not([type="hidden"]):not([aria-label]):not([aria-labelledby])').forEach(input => {
                            const id = input.id;
                            const label = id ? document.querySelector(`label[for="${id}"]`) : null;
                            if (!label && !input.closest('label')) {
                                issues.push({type: 'unlabeled_input', element: input.outerHTML.slice(0, 100)});
                            }
                        });
                        // Live regions sem aria-live
                        document.querySelectorAll('[role="alert"], [role="status"], [aria-live]').forEach(el => {
                            if (!el.getAttribute('aria-live') && !el.getAttribute('role')) {
                                issues.push({type: 'missing_aria_live', element: el.outerHTML.slice(0, 100)});
                            }
                        });
                        return issues;
                    }
                """)

                results["issues"] = sr_issues

                await browser.close()

            except Exception as e:
                logger.error(f"Erro no teste screen reader: {e}")
                await browser.close()
                results["error"] = str(e)
                return results

    elif method == "nvda-com":
        # Windows only - conecta ao NVDA via COM
        if sys.platform != "win32":
            results["skipped"] = True
            results["error"] = "nvda_com_windows_only"
            return results
        try:
            import comtypes.client
            nvda = comtypes.client.CreateObject("NVDA.Controller")
            # NVDA API: speakText, getFocusObject, etc.
            results["issues"].append({"type": "info", "message": "NVDA COM conectado - implementação pendente"})
        except Exception as e:
            results["error"] = f"nvda_com_failed: {e}"

    elif method == "orca-atspi":
        # Linux - conecta ao Orca via AT-SPI (D-Bus)
        try:
            import gi
            gi.require_version("Atspi", "2.0")
            from gi.repository import Atspi
            # AT-SPI tree traversal
            results["issues"].append({"type": "info", "message": "Orca AT-SPI conectado - implementação pendente"})
        except Exception as e:
            results["error"] = f"orca_atspi_failed: {e}"

    if output:
        with open(output, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Resultados salvos em: {output}")

    return results


async def run_screen_reader_cli(
    url: str,
    output: Optional[Path] = None,
    method: str = "speech-dispatcher",
    voice: str = "pt-br",
) -> Dict[str, Any]:
    """Wrapper CLI."""
    logger.info(f"Testando screen reader ({method}): {url}")

    result = await run_screen_reader_test(url, output=output, voice=voice, method=method)

    print(f"\nScreen Reader Test ({method}) - {url}")
    print(f"  Anúncios capturados: {len(result.get('announcements', []))}")
    print(f"  Issues detectados: {len(result.get('issues', []))}")

    for issue in result.get("issues", [])[:5]:
        print(f"  ⚠️  {issue.get('type')}: {issue.get('element', issue.get('message', ''))[:80]}")

    return result


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Screen Reader Accessibility Test")
    parser.add_argument("url", help="URL para testar")
    parser.add_argument("--output", "-o", type=Path, help="Arquivo JSON de saída")
    parser.add_argument("--method", default="speech-dispatcher", choices=["speech-dispatcher", "nvda-com", "orca-atspi"])
    parser.add_argument("--voice", default="pt-br", help="Voz para speech-dispatcher")
    parser.add_argument("--wait-for", help="Seletor para aguardar")
    args = parser.parse_args()

    await run_screen_reader_cli(args.url, args.output, args.method, args.voice)


if __name__ == "__main__":
    asyncio.run(main())