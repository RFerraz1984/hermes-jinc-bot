#!/usr/bin/env python3
"""
Orquestrador principal - Accessibility Audit Toolkit.
Executa auditoria completa: crawl → axe/pa11y/lighthouse → contraste → teclado → checklist e-MAG → relatórios.
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from axe_cli import run_axe
from pa11y_cli import run_pa11y
from lighthouse_cli import run_lighthouse
from contrast_check import check_contrast
from keyboard_nav import test_keyboard_navigation
from emag_checklist import run_emag_checklist
from wcag_report import generate_reports
from diff_report import compare_audits
from crawl_site import discover_urls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
CRITERIA_FILE = BASE_DIR / "templates" / "wcag_criteria.yaml"
CHECKLIST_FILE = BASE_DIR / "templates" / "checklist_emag.md"


class AccessibilityAudit:
    """Orquestra auditoria completa de acessibilidade."""

    def __init__(
        self,
        url: str,
        output_dir: Path,
        depth: int = 3,
        auto_only: bool = False,
        manual_only: bool = False,
        url_list: Optional[Path] = None,
        compare_with: Optional[Path] = None,
    ):
        self.url = url
        self.output_dir = output_dir
        self.depth = depth
        self.auto_only = auto_only
        self.manual_only = manual_only
        self.url_list = url_list
        self.compare_with = compare_with
        self.audit_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.raw_dir = output_dir / "raw" / self.audit_id
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    async def run(self) -> Dict[str, Any]:
        """Executa pipeline completo."""
        logger.info(f"Iniciando auditoria: {self.audit_id}")
        logger.info(f"URL base: {self.url}")
        logger.info(f"Diretório de saída: {self.output_dir}")

        # 1. Descoberta de URLs
        urls = await self._discover_urls()
        logger.info(f"URLs descobertas: {len(urls)}")

        if self.manual_only:
            return await self._run_manual_only(urls, self.audit_id)

        # 2. Testes automatizados (paralelo por URL)
        auto_results = await self._run_automated_tests(urls)

        if self.auto_only:
            return self._finalize(self.audit_id, urls, auto_results, None, None, None)

        # 3. Testes manuais (uma vez por auditoria)
        manual_results = await self._run_manual_tests(urls)

        # 4. Consolida
        return self._finalize(self.audit_id, urls, auto_results, manual_results, None, None)

    async def _discover_urls(self) -> List[str]:
        if self.url_list:
            with open(self.url_list) as f:
                return [line.strip() for line in f if line.strip() and not line.startswith("#")]

        return await discover_urls(self.url, max_depth=self.depth)

    async def _run_automated_tests(self, urls: List[str]) -> Dict[str, Any]:
        """Executa axe + pa11y + lighthouse em paralelo."""
        results = {}

        for url in urls:
            logger.info(f"Testando: {url}")
            url_results = {}

            # axe-core
            try:
                axe_result = await run_axe(url)
                url_results["axe"] = axe_result
                self._save_raw("axe", url, axe_result)
            except Exception as e:
                logger.warning(f"axe falhou para {url}: {e}")
                url_results["axe"] = {"error": str(e)}

            # pa11y
            try:
                pa11y_result = await run_pa11y([url])
                url_results["pa11y"] = pa11y_result
                self._save_raw("pa11y", url, pa11y_result)
            except Exception as e:
                logger.warning(f"pa11y falhou para {url}: {e}")
                url_results["pa11y"] = {"error": str(e)}

            # Lighthouse
            try:
                lh_result = await run_lighthouse(url)
                url_results["lighthouse"] = lh_result
                self._save_raw("lighthouse", url, lh_result)
            except Exception as e:
                logger.warning(f"Lighthouse falhou para {url}: {e}")
                url_results["lighthouse"] = {"error": str(e)}

            results[url] = url_results

        return results

    async def _run_manual_tests(self, urls: List[str]) -> Dict[str, Any]:
        """Executa testes manuais: contraste, teclado, e-MAG."""
        manual = {}

        # Contraste (página principal + amostra)
        sample_urls = urls[:5] if len(urls) > 5 else urls
        contrast_results = {}
        for url in sample_urls:
            try:
                contrast_results[url] = await check_contrast(url)
            except Exception as e:
                logger.warning(f"Contraste falhou para {url}: {e}")
                contrast_results[url] = {"error": str(e)}
        manual["contrast"] = contrast_results

        # Navegação por teclado (página principal)
        try:
            manual["keyboard"] = await test_keyboard_navigation(self.url)
        except Exception as e:
            logger.warning(f"Teste de teclado falhou: {e}")
            manual["keyboard"] = {"error": str(e)}

        # Checklist e-MAG
        try:
            manual["emag"] = await run_emag_checklist(self.url)
        except Exception as e:
            logger.warning(f"Checklist e-MAG falhou: {e}")
            manual["emag"] = {"error": str(e)}

        return manual

    async def _run_manual_only(self, urls: List[str], audit_id: str) -> Dict[str, Any]:
        """Executa apenas testes manuais (para re-auditoria rápida)."""
        manual_results = await self._run_manual_tests(urls)
        return self._finalize(audit_id, urls, {}, manual_results, None, None)

    def _finalize(
        self,
        audit_id: str,
        urls: List[str],
        auto_results: Dict,
        manual_results: Optional[Dict],
        contrast_results: Optional[Dict],
        keyboard_results: Optional[Dict],
    ) -> Dict[str, Any]:
        """Consolida tudo e gera relatórios."""
        audit_data = {
            "audit_id": audit_id,
            "url": self.url,
            "timestamp": datetime.now().isoformat(),
            "config": {
                "depth": self.depth,
                "auto_only": self.auto_only,
                "manual_only": self.manual_only,
            },
            "scope": {
                "urls": urls,
                "urls_tested": len(urls),
            },
            "auto_results": auto_results,
            "manual_results": manual_results or {},
        }

        # Gera relatórios
        logger.info("Gerando relatórios...")
        report_paths = generate_reports(audit_data, self.output_dir / "reports")

        # Compara com auditoria anterior se solicitado
        if self.compare_with:
            diff = compare_audits(self.compare_with, self.output_dir / "reports" / f"{audit_id}_raw.json")
            audit_data["diff"] = diff

        # Salva JSON consolidado
        consolidated_path = self.output_dir / "reports" / f"{audit_id}_consolidated.json"
        consolidated_path.write_text(json.dumps(audit_data, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info(f"Auditoria concluída: {audit_id}")
        logger.info(f"Relatórios em: {self.output_dir / 'reports'}")

        return audit_data

    def _save_raw(self, tool: str, url: str, data: Dict):
        """Salva resultado bruto de cada ferramenta."""
        safe_url = url.replace("://", "_").replace("/", "_").replace(":", "_")[:100]
        path = self.raw_dir / f"{tool}_{safe_url}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


async def main():
    parser = argparse.ArgumentParser(description="Accessibility Audit Toolkit")
    parser.add_argument("url", nargs="?", help="URL base para auditar")
    parser.add_argument("--output", "-o", type=Path, default=Path("audit_output"), help="Diretório de saída")
    parser.add_argument("--depth", "-d", type=int, default=3, help="Profundidade do crawl")
    parser.add_argument("--auto-only", action="store_true", help="Apenas testes automatizados")
    parser.add_argument("--manual-only", action="store_true", help="Apenas testes manuais")
    parser.add_argument("--url-list", "-u", type=Path, help="Arquivo com lista de URLs (uma por linha)")
    parser.add_argument("--compare", "-c", type=Path, help="Arquivo JSON de auditoria anterior para comparar")
    args = parser.parse_args()

    if not args.url and not args.url_list:
        parser.error("Forneça uma URL ou --url-list")

    audit = AccessibilityAudit(
        url=args.url or "",
        output_dir=args.output,
        depth=args.depth,
        auto_only=args.auto_only,
        manual_only=args.manual_only,
        url_list=args.url_list,
        compare_with=args.compare,
    )

    result = await audit.run()

    print(f"\n✅ Auditoria concluída: {result['audit_id']}")
    print(f"📁 Relatórios: {args.output / 'reports'}")


if __name__ == "__main__":
    asyncio.run(main())


# Função auxiliar para uso interno (cron scripts)
async def run_audit_internal(
    url: str,
    output_dir: Path,
    auto_only: bool = True,
    max_urls: int = 10,
) -> Dict[str, Any]:
    """Executa auditoria interna sem CLI args."""
    from crawl_site import discover_urls
    
    # Descobre URLs
    urls = await discover_urls(url, max_depth=2, max_urls=max_urls)
    
    audit = AccessibilityAudit(
        url=url,
        output_dir=output_dir,
        depth=2,
        auto_only=auto_only,
        manual_only=False,
        url_list=None,
        compare_with=None,
    )
    # Override _discover_urls to use our pre-discovered URLs
    audit._discover_urls = lambda: asyncio.coroutine(lambda: urls)()
    
    return await audit.run()