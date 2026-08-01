#!/usr/bin/env python3
"""
Verificador de contraste WCAG 2.1/2.2 (AA/AAA).
Analisa elementos visuais na página via Playwright.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


# Thresholds WCAG
CONTRAST_THRESHOLDS = {
    "AA": {"normal": 4.5, "large": 3.0, "ui": 3.0},
    "AAA": {"normal": 7.0, "large": 4.5, "ui": 3.0},
}


def parse_color(color_str: str) -> Optional[Tuple[int, int, int, float]]:
    """Parseia string de cor CSS para RGBA (0-255, 0-255, 0-255, 0-1)."""
    if not color_str or color_str in ("transparent", "rgba(0, 0, 0, 0)"):
        return None

    # rgb(r, g, b) / rgba(r, g, b, a)
    rgb_match = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", color_str)
    if rgb_match:
        r, g, b = map(int, rgb_match.groups()[:3])
        a = float(rgb_match.group(4)) if rgb_match.group(4) else 1.0
        return (r, g, b, a)

    # hex #rgb / #rrggbb / #rrggbbaa
    hex_match = re.match(r'#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})', color_str)
    if hex_match:
        hex_str = hex_match.group(1)
        if len(hex_str) == 3:
            r = int(hex_str[0]*2, 16)
            g = int(hex_str[1]*2, 16)
            b = int(hex_str[2]*2, 16)
            a = 1.0
        elif len(hex_str) == 4:
            r = int(hex_str[0]*2, 16)
            g = int(hex_str[1]*2, 16)
            b = int(hex_str[2]*2, 16)
            a = int(hex_str[3]*2, 16) / 255.0
        elif len(hex_str) == 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            a = 1.0
        elif len(hex_str) == 8:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            a = int(hex_str[6:8], 16) / 255.0
        else:
            return None
        return (r, g, b, a)

    return None


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calcula luminância relativa WCAG."""
    def channel(c: int) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(color1: Tuple[int, int, int, float], color2: Tuple[int, int, int, float]) -> float:
    """Calcula razão de contraste entre duas cores (com alpha blending)."""
    # Se tem transparência, assume fundo branco
    def blend(color: Tuple[int, int, int, float]) -> Tuple[int, int, int]:
        r, g, b, a = color
        if a >= 1.0:
            return (r, g, b)
        # Alpha blend sobre branco
        return (
            int(r * a + 255 * (1 - a)),
            int(g * a + 255 * (1 - a)),
            int(b * a + 255 * (1 - a)),
        )

    c1 = blend(color1)
    c2 = blend(color2)

    l1 = relative_luminance(*c1)
    l2 = relative_luminance(*c2)

    if l1 > l2:
        return (l1 + 0.05) / (l2 + 0.05)
    return (l2 + 0.05) / (l1 + 0.05)


def is_large_text(font_size: float, font_weight: str) -> bool:
    """Determina se texto é 'large' per WCAG (≥18pt ou ≥14pt bold)."""
    # 1pt = 1.333px
    size_pt = font_size / 1.333
    is_bold = font_weight in ("bold", "700", "800", "900")
    return size_pt >= 18 or (size_pt >= 14 and is_bold)


async def check_contrast(
    url: str,
    threshold: str = "AA",
    include_ui: bool = True,
    output: Optional[Path] = None,
    wait_for: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verifica contraste de todos os elementos de texto na página.

    Args:
        url: URL para auditar
        threshold: "AA" ou "AAA"
        include_ui: Incluir componentes UI (botões, inputs, etc)
        output: Arquivo JSON de saída
        wait_for: Seletor para aguardar

    Returns:
        Dict com resultados de contraste
    """
    thresholds = CONTRAST_THRESHOLDS[threshold]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            page = await context.new_page()

            await page.goto(url, wait_until="networkidle", timeout=30000)
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)
            await page.wait_for_timeout(2000)

            # Coleta elementos de texto
            elements = await page.evaluate("""
                () => {
                    const results = [];
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );

                    let node;
                    while (node = walker.nextNode()) {
                        const parent = node.parentElement;
                        if (!parent) continue;

                        const style = getComputedStyle(parent);
                        const text = node.textContent.trim();
                        if (!text) continue;

                        // Pega cor do texto
                        const color = style.color;
                        const bgColor = style.backgroundColor;

                        // Font
                        const fontSize = parseFloat(style.fontSize);
                        const fontWeight = style.fontWeight;
                        const fontFamily = style.fontFamily;

                        // Element info
                        const tagName = parent.tagName.toLowerCase();
                        const id = parent.id;
                        const className = parent.className;
                        const selector = id ? `#${id}` :
                                        (className ? `.${className.split(' ')[0]}` : tagName);

                        results.push({
                            text: text.slice(0, 100),
                            color: color,
                            backgroundColor: bgColor,
                            fontSize: fontSize,
                            fontWeight: fontWeight,
                            tagName: tagName,
                            selector: selector,
                            isUI: ['button', 'a', 'input', 'select', 'textarea', '[role="button"]').some(s => parent.matches(s))
                        });
                    }
                    return results;
                }
            """)

            violations = []
            passes = 0

            for el in elements:
                fg = parse_color(el["color"])
                bg = parse_color(el["backgroundColor"])

                if not fg or not bg:
                    continue

                ratio = contrast_ratio(fg, bg)

                is_large = is_large_text(el["fontSize"], el["fontWeight"])
                is_ui = el["isUI"]

                # Determina threshold aplicável
                if is_ui and include_ui:
                    required = thresholds["ui"]
                elif is_large:
                    required = thresholds["large"]
                else:
                    required = thresholds["normal"]

                passed = ratio >= required

                if passed:
                    passes += 1
                else:
                    violations.append({
                        "selector": el["selector"],
                        "tag": el["tagName"],
                        "text": el["text"][:50],
                        "font_size_px": el["fontSize"],
                        "font_weight": el["fontWeight"],
                        "is_large_text": is_large,
                        "is_ui_component": is_ui,
                        "contrast_ratio": round(ratio, 2),
                        "required_ratio": required,
                        "threshold": threshold,
                        "fg_color": f"rgba({fg[0]},{fg[1]},{fg[2]},{fg[3]})",
                        "bg_color": f"rgba({bg[0]},{bg[1]},{bg[2]},{bg[3]})",
                    })

            result = {
                "url": url,
                "threshold": threshold,
                "total_elements": len(elements),
                "passed": passes,
                "failed": len(violations),
                "violations": violations,
            }

            if output:
                with open(output, "w") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"Resultados salvos em: {output}")

            return result

        finally:
            await browser.close()


async def check_contrast_cli(
    url: str,
    threshold: str = "AA",
    output: Optional[Path] = None,
    wait_for: Optional[str] = None,
) -> Dict[str, Any]:
    """Wrapper CLI."""
    logger.info(f"Verificando contraste {threshold}: {url}")

    result = await check_contrast(url, threshold, output=output, wait_for=wait_for)

    print(f"\nContraste {threshold} - {url}")
    print(f"  Elementos analisados: {result['total_elements']}")
    print(f"  Passaram: {result['passed']}")
    print(f"  Falharam: {result['failed']}")

    for v in result["violations"][:10]:
        print(f"  ⚠️  {v['selector']}: {v['contrast_ratio']:.2f}:1 (mín {v['required_ratio']:.1f}:1)")
        print(f"      Texto: '{v['text']}' ({v['font_size_px']}px, {v['font_weight']})")

    return result


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="WCAG Contrast Checker")
    parser.add_argument("url", help="URL para auditar")
    parser.add_argument("--threshold", default="AA", choices=["AA", "AAA"])
    parser.add_argument("--output", "-o", type=Path, help="Arquivo JSON de saída")
    parser.add_argument("--wait-for", help="Seletor para aguardar")
    args = parser.parse_args()

    await check_contrast_cli(args.url, args.threshold, args.output, args.wait_for)


if __name__ == "__main__":
    asyncio.run(main())