#!/usr/bin/env python3
"""
Wrapper Lighthouse CI - performance + acessibilidade.
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def run_lighthouse(
    url: str,
    preset: str = "desktop",
    categories: List[str] = None,
    output: Optional[Path] = None,
    budget: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executa Lighthouse CI via CLI.
    
    Args:
        url: URL para auditar
        preset: "desktop" ou "mobile"
        categories: Lista de categorias (accessibility, performance, best-practices, seo, pwa)
        output: Arquivo JSON de saída
        budget: Arquivo budget.json para performance budgets
    
    Returns:
        Dict com resultados do Lighthouse
    """
    categories = categories or ["accessibility", "performance", "best-practices", "seo"]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        output_file = f.name
    
    try:
        cmd = [
            "lighthouse",
            url,
            "--preset", preset,
            "--output", "json",
            "--output-path", output_file,
            "--quiet",
            "--chrome-flags=--headless --no-sandbox --disable-gpu",
        ]
        
        for cat in categories:
            cmd.extend(["--only-categories", cat])
        
        if budget:
            cmd.extend(["--budget-path", str(budget)])
        
        logger.debug(f"Executando: {' '.join(cmd)}")
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise Exception("Lighthouse timeout (5 min)")
        
        if proc.returncode not in (0, 1):
            stderr_text = stderr.decode() if stderr else "unknown error"
            raise Exception(f"Lighthouse falhou (code {proc.returncode}): {stderr_text}")
        
        # Lê resultado
        with open(output_file, "r") as f:
            result = json.load(f)
        
        return result
        
    finally:
        Path(output_file).unlink(missing_ok=True)


def extract_a11y_score(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai score de acessibilidade e detalhes."""
    categories = result.get("categories", {})
    a11y = categories.get("accessibility", {})
    
    score = a11y.get("score", 0) * 100 if a11y.get("score") is not None else 0
    
    # Audits com falha
    failed_audits = []
    for audit_id, audit in a11y.get("auditRefs", []):
        pass
    
    # Better: parse audit results directly
    audits = result.get("audits", {})
    a11y_audits = {k: v for k, v in audits.items() if v.get("scoreDisplayMode") != "notApplicable"}
    
    failed = []
    for audit_id, audit in a11y_audits.items():
        if audit.get("score") is not None and audit["score"] < 1:
            failed.append({
                "id": audit_id,
                "title": audit.get("title"),
                "description": audit.get("description"),
                "score": audit.get("score"),
                "scoreDisplayMode": audit.get("scoreDisplayMode"),
                "details": audit.get("details", {}),
            })
    
    return {
        "score": round(score, 1),
        "passed": len([a for a in failed if a["score"] == 1]),
        "failed": len(failed),
        "failed_audits": failed[:20],  # top 20
    }


async def run_lighthouse_cli(
    url: str,
    output: Optional[Path] = None,
    preset: str = "desktop",
    categories: List[str] = None,
) -> Dict[str, Any]:
    """Wrapper CLI."""
    logger.info(f"Executando Lighthouse: {url} (preset={preset})")
    
    result = await run_lighthouse(url, preset=preset, categories=categories, output=output)
    
    a11y_summary = extract_a11y_score(result)
    
    print(f"\nLighthouse {preset} - {url}")
    print(f"  Acessibilidade: {a11y_summary['score']}/100")
    print(f"  Audits falhando: {a11y_summary['failed']}")
    
    for audit in a11y_summary["failed_audits"][:5]:
        print(f"  ❌ {audit['id']}: {audit['title']} (score: {audit['score']})")
    
    return result


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Lighthouse CI Wrapper")
    parser.add_argument("url", help="URL para auditar")
    parser.add_argument("--output", "-o", type=Path, help="Arquivo JSON de saída")
    parser.add_argument("--preset", default="desktop", choices=["desktop", "mobile"])
    parser.add_argument("--categories", nargs="+", default=["accessibility", "performance", "best-practices", "seo"])
    args = parser.parse_args()
    
    await run_lighthouse_cli(args.url, args.output, args.preset, args.categories)


if __name__ == "__main__":
    asyncio.run(main())