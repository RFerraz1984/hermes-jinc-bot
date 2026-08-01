#!/usr/bin/env python3
"""
Wrapper pa11y - teste de acessibilidade multi-página.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def run_pa11y(
    urls: List[str],
    standard: str = "WCAG2AA",
    threshold: int = 0,
    include_warnings: bool = True,
    include_notices: bool = True,
    output: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Executa pa11y em múltiplas URLs.
    
    Args:
        urls: Lista de URLs para testar
        standard: WCAG2A, WCAG2AA, WCAG2AAA, Section508
        threshold: Número máximo de erros permitidos (0 = sem limite)
        include_warnings: Incluir warnings
        include_notices: Incluir notices
        output: Arquivo JSON de saída
        config: Config adicional (wait, timeout, etc)
    
    Returns:
        Dict com resultados consolidados
    """
    config = config or {}
    wait = config.get("wait", 1000)
    timeout = config.get("timeout", 60000)
    headers = config.get("headers", {})
    cookies = config.get("cookies", [])
    
    all_results = {}
    summary = {"total_errors": 0, "total_warnings": 0, "total_notices": 0, "pages_tested": 0}
    
    for url in urls:
        logger.info(f"Executando pa11y: {url}")
        
        cmd = [
            "pa11y",
            url,
            "--standard", standard,
            "--reporter", "json",
            "--wait", str(wait),
            "--timeout", str(timeout),
        ]
        
        if threshold > 0:
            cmd.extend(["--threshold", str(threshold)])
        
        if not include_warnings:
            cmd.append("--ignore-warnings")
        if not include_notices:
            cmd.append("--ignore-notices")
        
        # Headers customizados
        for k, v in headers.items():
            cmd.extend(["--header", f"{k}: {v}"])
        
        # Cookies
        for cookie in cookies:
            cmd.extend(["--cookie", f"{cookie['name']}={cookie['value']}"])
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            
            if proc.returncode not in (0, 1, 2):
                raise Exception(f"pa11y falhou (code {proc.returncode}): {stderr.decode()}")
            
            if stdout:
                result = json.loads(stdout.decode())
                all_results[url] = result
                
                # Sumariza
                issues = result.get("issues", [])
                errors = [i for i in issues if i.get("type") == "error"]
                warnings = [i for i in issues if i.get("type") == "warning"]
                notices = [i for i in issues if i.get("type") == "notice"]
                
                summary["total_errors"] += len(errors)
                summary["total_warnings"] += len(warnings)
                summary["total_notices"] += len(notices)
                summary["pages_tested"] += 1
                
                # Top issues por tipo
                by_type = {}
                for issue in issues:
                    t = issue.get("type", "unknown")
                    by_type[t] = by_type.get(t, 0) + 1
                
                all_results[url]["summary"] = {
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "notices": len(notices),
                    "by_type": by_type,
                }
                
        except asyncio.TimeoutError:
            logger.error(f"pa11y timeout: {url}")
            all_results[url] = {"error": "timeout"}
        except json.JSONDecodeError:
            logger.error(f"pa11y JSON inválido: {url}")
            all_results[url] = {"error": "invalid_json"}
        except Exception as e:
            logger.error(f"pa11y erro: {url} - {e}")
            all_results[url] = {"error": str(e)}
    
    result = {
        "standard": standard,
        "summary": summary,
        "results": all_results,
    }
    
    if output:
        with open(output, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Resultados salvos em: {output}")
    
    return result


async def run_pa11y_cli(
    urls: List[str],
    output: Optional[Path] = None,
    standard: str = "WCAG2AA",
) -> Dict[str, Any]:
    """Wrapper CLI."""
    logger.info(f"Executando pa11y em {len(urls)} URLs (standard={standard})")
    
    result = await run_pa11y(urls, standard=standard, output=output)
    
    print(f"\npa11y ({standard}) - {len(urls)} páginas")
    print(f"  Erros: {result['summary']['total_errors']}")
    print(f"  Warnings: {result['summary']['total_warnings']}")
    print(f"  Notices: {result['summary']['total_notices']}")
    
    for url, res in result["results"].items():
        if "error" in res:
            print(f"  ❌ {url}: {res['error']}")
        else:
            s = res.get("summary", {})
            print(f"  {url}: {s.get('errors',0)} erros, {s.get('warnings',0)} warnings")
    
    return result


async def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="pa11y Multi-Page Wrapper")
    parser.add_argument("urls", nargs="+", help="URLs para testar")
    parser.add_argument("--output", "-o", type=Path, help="Arquivo JSON de saída")
    parser.add_argument("--standard", default="WCAG2AA", choices=["WCAG2A", "WCAG2AA", "WCAG2AAA", "Section508"])
    args = parser.parse_args()
    
    await run_pa11y_cli(args.urls, args.output, args.standard)


if __name__ == "__main__":
    asyncio.run(main())