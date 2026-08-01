#!/usr/bin/env python3
"""
Script standalone para execução via cron (no_agent=True) - AUDITORIA LEGISLATIVA.
Roda auditoria dos portais legislativos e entrega relatório via stdout para o Hermes entregar ao Telegram.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Garante que Node.js binaries estejam no PATH (instalados via npm global)
os.environ["PATH"] = "/opt/data/.npm-global/bin:" + os.environ.get("PATH", "")

# Garante que o toolkit esteja no path
TOOLKIT_PATH = Path("/opt/data/skills/journalism/accessibility-audit-toolkit")
sys.path.insert(0, str(TOOLKIT_PATH))

from scripts.audit import AccessibilityAudit

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    """Executa auditoria para os portais legislativos alvo."""
    
    # Carrega URLs dos portais legislativos
    urls_file = Path("/opt/data/urls_legislative.txt")
    if urls_file.exists():
        target_urls = [line.strip() for line in urls_file.read_text().splitlines() if line.strip() and not line.startswith("#")]
    else:
        # Fallback para URLs hardcoded dos portais legislativos
        target_urls = [
            "https://www.camara.leg.br",
            "https://www.senado.leg.br",
            "https://www.gov.br",
            "https://www.gov.br/acessibilidade",
        ]
    
    # Diretório de saída com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"/opt/data/audits/cron_legislative_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary_lines = [f"🤖 **Auditoria Legislativa Automática JINC** — {timestamp}\n"]
    
    for url in target_urls:
        try:
            logger.info(f"Iniciando auditoria legislativa: {url}")
            
            # Cria diretório específico para este site
            site_dir = output_dir / url.replace("https://", "").replace("/", "_")
            site_dir.mkdir(parents=True, exist_ok=True)
            
            # Executa auditoria completa (APENAS home page para cron)
            audit = AccessibilityAudit(
                url=url,
                output_dir=site_dir,
                depth=0,  # não faz crawl - testa só a URL passada
                auto_only=True,
                manual_only=False,
                url_list=None,
                compare_with=None,
            )
            
            result = await audit.run()
            
            # Lê o relatório executivo gerado
            report_dir = site_dir / "reports"
            executive_files = list(report_dir.glob("*_executive.md"))
            if executive_files:
                with open(executive_files[0], "r") as f:
                    content = f.read()
                    # Pega as primeiras linhas do resumo
                    lines = content.split("\n")[:18]
                    summary_lines.append(f"\n## 📍 {url}")
                    summary_lines.extend(lines)
            else:
                summary_lines.append(f"\n## 📍 {url} — Relatório não gerado")
            
        except Exception as e:
            logger.error(f"Erro auditando {url}: {e}")
            summary_lines.append(f"\n## ❌ {url} — **ERRO**: {e}")
    
    # Output final para Telegram (stdout é entregue pelo Hermes)
    print("\n".join(summary_lines))
    print(f"\n📁 Relatórios completos em: `{output_dir}`")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)