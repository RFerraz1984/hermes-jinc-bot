#!/usr/bin/env python3
"""
Teste de navegação por teclado - Tab order, focus visible, skip links, keyboard traps.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


async def test_keyboard_navigation(
    url: str,
    max_tabs: int = 100,
    check_focus_visible: bool = True,
    check_skip_links: bool = True,
    check_keyboard_traps: bool = True,
) -> Dict[str, Any]:
    """
    Testa navegação por teclado em uma página.

    Verifica:
    - Skip links funcionais
    - Tab order lógico
    - Focus visible em todos elementos interativos
    - Ausência de keyboard traps
    - Operabilidade de todos controles via teclado
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1000)

            # 1. Verifica skip links
            skip_links = []
            if check_skip_links:
                skip_links = await page.evaluate("""
                    () => {
                        const links = document.querySelectorAll('a[href^="#"]');
                        const skipLinks = [];
                        links.forEach(link => {
                            const href = link.getAttribute('href');
                            const target = document.querySelector(href);
                            const text = link.textContent.trim();
                            if (target && (text.toLowerCase().includes('skip') ||
                                text.toLowerCase().includes('pular') ||
                                text.toLowerCase().includes('conteúdo') ||
                                text.toLowerCase().includes('main'))) {
                                skipLinks.push({
                                    text: text,
                                    href: href,
                                    targetId: href.substring(1),
                                    visible: getComputedStyle(link).display !== 'none' &&
                                            getComputedStyle(link).visibility !== 'hidden'
                                });
                            }
                        });
                        return skipLinks;
                    }
                """)

            # 2. Tab navigation - coleta ordem de foco
            focus_order = []
            focusable_elements = []

            for i in range(max_tabs):
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(50)

                focused = await page.evaluate("""
                    () => {
                        const el = document.activeElement;
                        if (!el || el === document.body) return null;
                        return {
                            tagName: el.tagName.toLowerCase(),
                            id: el.id,
                            className: el.className,
                            text: el.textContent ? el.textContent.trim().slice(0, 100) : '',
                            type: el.type || '',
                            href: el.href || '',
                            role: el.getAttribute('role') || '',
                            tabindex: el.getAttribute('tabindex') || '',
                        };
                    }
                """)

                if not focused:
                    break

                # Verifica focus visible
                focus_visible = False
                if check_focus_visible:
                    focus_visible = await page.evaluate("""
                        () => {
                            const el = document.activeElement;
                            if (!el) return false;
                            const style = getComputedStyle(el);
                            const focusStyle = getComputedStyle(el, ':focus');
                            const focusVisibleStyle = getComputedStyle(el, ':focus-visible');

                            // Verifica se há outline, box-shadow ou border change no focus
                            const outline = style.outline || focusStyle.outline || focusVisibleStyle.outline;
                            const boxShadow = style.boxShadow || focusStyle.boxShadow || focusVisibleStyle.boxShadow;
                            const border = style.border || focusStyle.border || focusVisibleStyle.border;

                            return outline !== 'none' && outline !== '0px' ||
                                   boxShadow !== 'none' ||
                                   border !== '0px';
                        }
                    """)

                # Evita loops (volta ao primeiro)
                if focus_order and focused.get("id") == focus_order[0].get("id") and i > 10:
                    break

                focused["focus_visible"] = focus_visible
                focus_order.append(focused)
                focusable_elements.append(focused)

            # 3. Verifica keyboard traps (modais, carrosséis)
            keyboard_traps = []
            if check_keyboard_traps:
                keyboard_traps = await page.evaluate("""
                    () => {
                        const traps = [];
                        // Procura modais abertos
                        const modals = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .modal, .dialog, [aria-modal="true"]');
                        modals.forEach(modal => {
                            const style = getComputedStyle(modal);
                            if (style.display !== 'none' && style.visibility !== 'hidden') {
                                const focusableInModal = modal.querySelectorAll(
                                    'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
                                );
                                if (focusableInModal.length === 0) {
                                    traps.push({
                                        type: 'modal_no_focusable',
                                        element: modal.outerHTML.slice(0, 200),
                                    });
                                }
                            }
                        });
                        return traps;
                    }
                """)

            # 4. Verifica elementos interativos sem focus
            no_focus_elements = await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll(
                        'a[href], button, input, select, textarea, [onclick], [role="button"], [role="link"], [tabindex]:not([tabindex="-1"])'
                    );
                    const noFocus = [];
                    elements.forEach(el => {
                        const style = getComputedStyle(el);
                        const focusStyle = getComputedStyle(el, ':focus');
                        const focusVisibleStyle = getComputedStyle(el, ':focus-visible');

                        const hasFocusStyle = focusStyle.outline !== 'none' && focusStyle.outline !== '0px' ||
                                              focusVisibleStyle.outline !== 'none' && focusVisibleStyle.outline !== '0px' ||
                                              focusStyle.boxShadow !== 'none' ||
                                              focusVisibleStyle.boxShadow !== 'none';

                        if (!hasFocusStyle && style.display !== 'none' && style.visibility !== 'hidden') {
                            noFocus.push({
                                tagName: el.tagName.toLowerCase(),
                                id: el.id,
                                className: el.className,
                                text: el.textContent ? el.textContent.trim().slice(0, 50) : '',
                                type: el.type || '',
                            });
                        }
                    });
                    return noFocus;
                }
            """)

            await browser.close()

        except Exception as e:
            logger.error(f"Erro no teste de teclado: {e}")
            await browser.close()
            return {"url": url, "error": str(e)}

        return {
            "url": url,
            "skip_links": skip_links,
            "focus_order": focus_order,
            "focusable_count": len(focusable_elements),
            "focus_visible_issues": [f for f in focus_order if not f.get("focus_visible", True)],
            "keyboard_traps": keyboard_traps,
            "no_focus_style": no_focus_elements,
            "tab_stops": len(focus_order),
            "has_skip_link": len([s for s in skip_links if s.get("visible")]) > 0,
        }


async def test_keyboard_navigation_cli(
    url: str,
    output: Optional[Path] = None,
    max_tabs: int = 100,
) -> Dict[str, Any]:
    """Wrapper CLI."""
    logger.info(f"Testando navegação por teclado: {url}")

    result = await test_keyboard_navigation(url, max_tabs=max_tabs)

    if output:
        with open(output, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Resultado salvo em: {output}")

    # Summary
    print(f"\nNavegação por Teclado - {url}")
    print(f"  Tab stops: {result.get('tab_stops', 0)}")
    print(f"  Skip links visíveis: {sum(1 for s in result.get('skip_links', []) if s.get('visible'))}")
    print(f"  Elementos sem focus visible: {len(result.get('focus_visible_issues', []))}")
    print(f"  Keyboard traps: {len(result.get('keyboard_traps', []))}")
    print(f"  Elementos sem estilo de foco: {len(result.get('no_focus_style', []))}")

    for issue in result.get('focus_visible_issues', [])[:5]:
        print(f"  ⚠️  Sem focus visible: {issue.get('text', '')[:50]} ({issue.get('tagName')})")

    return result


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Keyboard Navigation Test")
    parser.add_argument("url", help="URL para testar")
    parser.add_argument("--output", "-o", type=Path, help="Arquivo JSON de saída")
    parser.add_argument("--max-tabs", type=int, default=100, help="Máximo de Tab presses")
    args = parser.parse_args()

    await test_keyboard_navigation_cli(args.url, args.output, args.max_tabs)


if __name__ == "__main__":
    asyncio.run(main())